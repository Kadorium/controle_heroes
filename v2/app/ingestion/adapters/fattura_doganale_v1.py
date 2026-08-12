"""Adapter fattura_doganale_v1 — Fattura Doganale (customs invoice) da Heroe's Srl.

Corpus: corpus_202/FatturaDoganale_202.pdf (1 página).
Estrutura similar à Fattura comercial mas sem scadenze.
Colunas: Quantity (SET) | NCM | Description | Indiv. Price | Amount (EUR)
Totais: Total (EUR), Total Net Weight (Kg), Total Gross Weight (Kg), Pallets

Decisão P0: FatturaDoganale é a fonte customs; quando commitado, pode criar
ImportProcess DRAFT via customs public API (dossier_commands.py).
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion import staging_commands
from app.ingestion import storage as quarantine_storage
from app.ingestion.annotations import extract_origin_annotation
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.ingestion.parse_it import parse_it_date, parse_it_number

ADAPTER_ID = "fattura_doganale_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "FATTURA_DOGANALE"


def _compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _strip_currency(s: str) -> str:
    return re.sub(r"[€\s]", "", s).strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RawLineItem:
    quantity: Decimal
    unit: str  # "SET" as declared in Doganale
    ncm: str | None
    description: str
    unit_price: Decimal
    line_total: Decimal
    row_index: int


@dataclass
class AdapterRawResult:
    supplier_name: str | None
    supplier_pi_cf: str | None
    document_number: str | None
    document_date_iso: str | None
    currency: str
    incoterms: str | None
    payment_terms: str | None
    total_document: Decimal | None
    total_net_weight_kg: Decimal | None
    total_gross_weight_kg: Decimal | None
    pallet_count: int | None
    delivery_terms: str | None
    origin_raw: str | None
    origin_declared: str | None
    origin_possible_other: str | None
    lines: list[RawLineItem] = field(default_factory=list)
    raw_text_layout: str = ""


# ---------------------------------------------------------------------------
# Header + totals extraction — from layout text
# ---------------------------------------------------------------------------


def _extract_header_and_totals(layout_text: str) -> dict:
    result: dict = {}
    lines = [l.strip() for l in layout_text.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        low = line.lower().replace(" ", "")

        if "heroe" in low and "srl" in low:
            result.setdefault("supplier_name", "Heroe's Srl")

        m = re.search(r"PI\s*/?\s*CF\s*:\s*([\d]+)\s*-", line, re.IGNORECASE)
        if m:
            pi_raw = re.sub(r"\s+", "", m.group(1))
            if len(pi_raw) >= 11:
                result.setdefault("supplier_pi_cf", pi_raw[:11])

        # Number and date: "202 16/04/2026" on same line
        m = re.search(r"\b(\d{1,4})\s+(\d{1,2}/\d{2}/\d{4})\b", line)
        if m:
            result.setdefault("document_number", m.group(1))
            result.setdefault("document_date_raw", m.group(2))

        if "eur" in low and "incoterms" not in result:
            result.setdefault("currency", "EUR")

        if "ex works" in line.lower():
            result.setdefault("incoterms", "EX WORKS")

        if "bonifico" in low:
            result.setdefault("payment_terms", _compact(line))

        # Total (EUR): "Total (EUR) 30.188,00 €" or "30.188,00 €"
        m = re.search(r"[Tt]otal\s*\(EUR\)\s+([\d.,]+)", line)
        if m:
            result.setdefault("total_document", _strip_currency(m.group(1)))

        # Subtotal: "Subtotal (EUR) 30.188,00 €"
        m = re.search(r"[Ss]ubtotal\s*\(EUR\)\s+([\d.,]+)", line)
        if m:
            result.setdefault("subtotal", _strip_currency(m.group(1)))

        # Total Net Weight
        m = re.search(r"Total\s+Net\s+Weight\s*\(Kg\)\s+([\d.,]+)", line, re.IGNORECASE)
        if m:
            result.setdefault("total_net_weight", m.group(1))

        # Total Gross Weight
        m = re.search(r"Total\s+Gross\s+Weight\s*\(Kg\)\s+([\d.,]+)", line, re.IGNORECASE)
        if m:
            result.setdefault("total_gross_weight", m.group(1))

        # Pallets
        m = re.search(r"Pallets\s+(\d+)", line, re.IGNORECASE)
        if m:
            result.setdefault("pallets", m.group(1))

        if "delivery terms" in line.lower():
            result.setdefault("delivery_terms", _compact(line))

    return result


# ---------------------------------------------------------------------------
# Line items extraction — layout mode
# ---------------------------------------------------------------------------


def _parse_lines(layout_text: str) -> list[RawLineItem]:
    """Parse doganale line items from layout text.

    Format: quantity  NCM  description  unit_price  amount_eur
    Example:
      150               4202 221000                  WASH BAG REBEL   6,50   975,00 €
    """
    items: list[RawLineItem] = []
    row_idx = 0

    _RE_LINE = re.compile(
        r"^\s*(\d+)\s+"                         # quantity (group 1)
        r"((?:\d[\d\s]*\d|\d{4,}))\s+"          # NCM (group 2)
        r"(.+?)\s+"                              # description (group 3)
        r"([\d,\.]+)\s+"                         # unit_price (group 4)
        r"([\d,\.]+)\s*€?"                       # line_total (group 5)
    )

    for line in layout_text.splitlines():
        stripped = line.strip()
        m = _RE_LINE.match(stripped)
        if not m:
            continue

        # Skip header rows
        desc_lower = m.group(3).lower()
        if "description" in desc_lower or "ncm" in desc_lower:
            continue

        qty = parse_it_number(m.group(1)) or Decimal("0")
        ncm_raw = re.sub(r"\s+", "", m.group(2))
        description = _compact(m.group(3))
        unit_price = parse_it_number(m.group(4)) or Decimal("0")
        line_total = parse_it_number(m.group(5)) or Decimal("0")

        # Skip if line_total == 0 and price == 0 (packaging/blank rows)
        if qty == 0:
            continue

        items.append(
            RawLineItem(
                quantity=qty,
                unit="SET",
                ncm=ncm_raw,
                description=description,
                unit_price=unit_price,
                line_total=line_total,
                row_index=row_idx,
            )
        )
        row_idx += 1

    return items


# ---------------------------------------------------------------------------
# Math validation
# ---------------------------------------------------------------------------


def _validate_math(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []

    if not raw.lines:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_LINE_ITEMS",
                "message": "Nenhum item extraído da Fattura Doganale.",
                "target_type": "DOCUMENT",
            }
        )
        return issues

    computed = sum(line.line_total for line in raw.lines)
    for line in raw.lines:
        expected = (line.quantity * line.unit_price).quantize(Decimal("0.01"))
        if abs(expected - line.line_total) > Decimal("0.02"):
            issues.append(
                {
                    "severity": "ERROR",
                    "code": "MATH_LINE_TOTAL_MISMATCH",
                    "message": (
                        f"Linha '{line.description}': {line.quantity} × {line.unit_price} "
                        f"= {expected} mas total declarado é {line.line_total}"
                    ),
                    "target_type": "ROW",
                    "target_id": line.row_index,
                }
            )

    if raw.total_document is not None:
        if abs(computed - raw.total_document) > Decimal("0.02"):
            issues.append(
                {
                    "severity": "ERROR",
                    "code": "MATH_TOTAL_MISMATCH",
                    "message": (
                        f"Soma linhas ({computed}) ≠ Total (EUR) ({raw.total_document})"
                    ),
                    "target_type": "DOCUMENT",
                }
            )

    if raw.origin_possible_other:
        issues.append(
            {
                "severity": "WARNING",
                "code": "DUAL_ORIGIN_ANNOTATION",
                "message": (
                    f"Campo 'Country of origin' contém duas camadas: "
                    f"'{raw.origin_possible_other}' (fundo) + '{raw.origin_declared}' (declarado)."
                ),
                "target_type": "DOCUMENT",
                "locator_json": json.dumps({"field": "origin_country", "source": "layout_freetext"}),
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Main extract
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    layout_pages: list[str] = []
    for page in reader.pages:
        layout_pages.append(page.extract_text(extraction_mode="layout") or "")

    layout_text = "\n".join(layout_pages)
    header = _extract_header_and_totals(layout_text)
    lines = _parse_lines(layout_text)

    doc_date_iso: str | None = None
    if header.get("document_date_raw"):
        doc_date_iso, _ = parse_it_date(header["document_date_raw"])

    from app.ingestion.annotations import extract_origin_annotation

    ann = extract_origin_annotation(layout_text)

    # Prefer Total over Subtotal for total_document
    total_doc_str = header.get("total_document") or header.get("subtotal")
    total_document = parse_it_number(total_doc_str)
    total_net = parse_it_number(header.get("total_net_weight"))
    total_gross = parse_it_number(header.get("total_gross_weight"))
    pallet_count = int(header["pallets"]) if header.get("pallets") else None

    return AdapterRawResult(
        supplier_name=header.get("supplier_name"),
        supplier_pi_cf=header.get("supplier_pi_cf"),
        document_number=header.get("document_number"),
        document_date_iso=doc_date_iso,
        currency=header.get("currency", "EUR"),
        incoterms=header.get("incoterms"),
        payment_terms=header.get("payment_terms"),
        total_document=total_document,
        total_net_weight_kg=total_net,
        total_gross_weight_kg=total_gross,
        pallet_count=pallet_count,
        delivery_terms=header.get("delivery_terms"),
        origin_raw=ann.raw_value,
        origin_declared=ann.declared,
        origin_possible_other=ann.possible_other,
        lines=lines,
        raw_text_layout=layout_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    if raw.supplier_name and "heroe" in raw.supplier_name.lower():
        if raw.lines:
            return True
    return False


# ---------------------------------------------------------------------------
# Full adapter run
# ---------------------------------------------------------------------------


def run_adapter(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str,
    quarantine_path: Path,
) -> "IngestionDocument":  # noqa: F821
    occ = db.get(IngestionOccurrence, occurrence_id)
    if occ is None:
        from app.ingestion.errors import OccurrenceNotFound

        raise OccurrenceNotFound(occurrence_id)

    if occ.blob is None or occ.blob.physical_status != "PRESENT" or not occ.blob.storage_path:
        raise IngestionError(
            f"Blob da occurrence {occurrence_id} indisponível", code="blob_unavailable"
        )

    path = quarantine_storage.resolve_quarantine_path(quarantine_path, occ.blob.storage_path)
    if path is None or not path.is_file():
        raise IngestionError(
            f"Arquivo físico não encontrado para occurrence {occurrence_id}",
            code="blob_unavailable",
        )

    pdf_bytes = path.read_bytes()
    raw = extract(pdf_bytes)
    issues = _validate_math(raw)

    sections = [
        {"section_key": "header", "title": "Cabeçalho Fattura Doganale", "ordinal": 0},
        {"section_key": "lines", "title": "Linhas Doganale", "ordinal": 1},
        {"section_key": "annotations", "title": "Anotações FreeText", "ordinal": 2},
    ]

    def _loc(p: int = 0) -> str:
        return json.dumps({"page": p, "source": "pypdf_layout"})

    str_or_none = lambda v: str(v) if v is not None else None

    fields = [
        {"section_key": "header", "field_key": "supplier_name", "value_type": "string", "raw_value": raw.supplier_name, "normalized_value": raw.supplier_name, "locator_json": _loc()},
        {"section_key": "header", "field_key": "supplier_pi_cf", "value_type": "string", "raw_value": raw.supplier_pi_cf, "normalized_value": raw.supplier_pi_cf, "locator_json": _loc()},
        {"section_key": "header", "field_key": "document_number", "value_type": "string", "raw_value": raw.document_number, "normalized_value": raw.document_number, "locator_json": _loc()},
        {"section_key": "header", "field_key": "document_date", "value_type": "date", "raw_value": raw.document_date_iso, "normalized_value": raw.document_date_iso, "locator_json": _loc()},
        {"section_key": "header", "field_key": "currency", "value_type": "string", "raw_value": raw.currency, "normalized_value": raw.currency, "locator_json": None},
        {"section_key": "header", "field_key": "incoterms", "value_type": "string", "raw_value": raw.incoterms, "normalized_value": raw.incoterms, "locator_json": _loc()},
        {"section_key": "header", "field_key": "total_document_eur", "value_type": "decimal", "raw_value": str_or_none(raw.total_document), "normalized_value": str_or_none(raw.total_document), "locator_json": _loc()},
        {"section_key": "header", "field_key": "total_net_weight_kg", "value_type": "decimal", "raw_value": str_or_none(raw.total_net_weight_kg), "normalized_value": str_or_none(raw.total_net_weight_kg), "locator_json": _loc()},
        {"section_key": "header", "field_key": "total_gross_weight_kg", "value_type": "decimal", "raw_value": str_or_none(raw.total_gross_weight_kg), "normalized_value": str_or_none(raw.total_gross_weight_kg), "locator_json": _loc()},
        {"section_key": "header", "field_key": "pallet_count", "value_type": "integer", "raw_value": str_or_none(raw.pallet_count), "normalized_value": str_or_none(raw.pallet_count), "locator_json": _loc()},
        {"section_key": "annotations", "field_key": "origin_country_raw", "value_type": "string", "raw_value": raw.origin_raw, "normalized_value": raw.origin_raw, "locator_json": json.dumps({"field": "origin_country", "source": "layout_freetext"})},
        {"section_key": "annotations", "field_key": "origin_country_declared", "value_type": "string", "raw_value": raw.origin_declared, "normalized_value": raw.origin_declared, "locator_json": json.dumps({"field": "origin_country", "source": "layout_freetext", "layer": "declared"})},
    ]

    if raw.origin_possible_other:
        fields.append({"section_key": "annotations", "field_key": "origin_country_possible_other", "value_type": "string", "raw_value": raw.origin_possible_other, "normalized_value": raw.origin_possible_other, "locator_json": json.dumps({"field": "origin_country", "source": "layout_freetext", "layer": "background"})})

    rows = []
    for line in raw.lines:
        cells = {
            "quantity": {"raw": str(line.quantity), "normalized": str(line.quantity)},
            "unit": {"raw": line.unit, "normalized": line.unit},
            "ncm": {"raw": line.ncm, "normalized": line.ncm},
            "description": {"raw": line.description, "normalized": line.description},
            "unit_price": {"raw": str(line.unit_price), "normalized": str(line.unit_price)},
            "line_total": {"raw": str(line.line_total), "normalized": str(line.line_total)},
        }
        rows.append(
            {
                "section_key": "lines",
                "row_index": line.row_index,
                "row_key": f"dog_{line.row_index}",
                "cells_json": json.dumps(cells, ensure_ascii=False),
            }
        )

    return staging_commands.seed_document_from_occurrence(
        db,
        occurrence_id=occurrence_id,
        actor_id=actor_id,
        doc_type=DOC_TYPE,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        sections=sections,
        fields=fields,
        rows=rows,
        issues=issues,
    )
