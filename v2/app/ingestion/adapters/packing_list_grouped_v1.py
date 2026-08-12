"""Adapter packing_list_grouped_v1 — PL Grouped da Heroe's Srl.

Corpus: corpus_202/PackingListGrouped_202.pdf (1 página).
Decisão P0: PL Grouped = evidência de ambiguidade, NÃO é SoT comercial.
- Linhas comerciais emitem issue AMBIGUITY_PL_GROUPED (WARNING, não ERROR)
- Linhas de embalagem (NCM 4819) anotadas como packaging, não criadas como OrderItem
- Reconciler usa como evidência, não como fonte autoritativa
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

ADAPTER_ID = "packing_list_grouped_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "PACKING_LIST_GROUPED"

NCM_PACKAGING_PREFIX = "4819"  # Not commercial goods


def _compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RawGroupedRow:
    units: int | None
    ncm: str | None
    description: str
    amount: Decimal | None
    unit_net_weight: Decimal | None
    unit_gross_weight: Decimal | None
    total_net_weight: Decimal | None
    total_gross_weight: Decimal | None
    is_packaging: bool  # NCM 4819 = packaging material
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
    origin_raw: str | None
    origin_declared: str | None
    origin_possible_other: str | None
    grouped_rows: list[RawGroupedRow] = field(default_factory=list)
    raw_text_layout: str = ""


# ---------------------------------------------------------------------------
# Header extraction
# ---------------------------------------------------------------------------


def _extract_header(text: str) -> dict:
    result: dict = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        low = line.lower().replace(" ", "")
        if "heroe" in low and "srl" in low:
            result.setdefault("supplier_name", "Heroe's Srl")
        m = re.search(r"PI\s*/\s*CF\s*:\s*([\d]+)\s*-", line, re.IGNORECASE)
        if m:
            pi_raw = re.sub(r"\s+", "", m.group(1))
            if len(pi_raw) >= 11:
                result.setdefault("supplier_pi_cf", pi_raw[:11])
        m = re.search(r"\b(\d{1,4})\s+(\d{1,2}/\d{2}/\d{4})\b", line)
        if m:
            result.setdefault("document_number", m.group(1))
            result.setdefault("document_date_raw", m.group(2))
        if "eur" in low:
            result.setdefault("currency", "EUR")
        if "ex works" in line.lower():
            result.setdefault("incoterms", "EX WORKS")
        if "bonifico" in low:
            result.setdefault("payment_terms", _compact(line))
    return result


# ---------------------------------------------------------------------------
# Row extraction from layout mode (clean columns)
# ---------------------------------------------------------------------------


def _parse_grouped_rows(layout_text: str) -> list[RawGroupedRow]:
    """Parse grouped rows from layout-mode text.

    Layout row format (space-aligned columns):
      units  NCM  description  amount  unit_weight  unit_gross  total_net  total_gross

    Example:
      600     4202 2210 00    GRAVITY ARION  23.688,00  0,90  1,00  690,00  747,00
    """
    rows: list[RawGroupedRow] = []
    row_idx = 0

    # Pattern: starts with number (units) optionally, then NCM (digits+spaces), then text, then numbers
    _RE_ROW = re.compile(
        r"^\s*(\d+)\s+"               # units (group 1)
        r"((?:\d[\d\s]*\d|\d+))\s+"   # NCM — digit sequence possibly with spaces (group 2)
        r"(.+?)\s+"                    # description (group 3, non-greedy)
        r"([\d.,]+)\s+"               # amount (group 4)
        r"([\d,]+)\s+"                # unit_net (group 5)
        r"([\d,]+)\s+"                # unit_gross (group 6)
        r"([\d,]+)\s+"                # total_net (group 7)
        r"([\d,]+)"                   # total_gross (group 8)
    )

    for line in layout_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        m = _RE_ROW.match(stripped)
        if not m:
            continue

        units_str = m.group(1)
        ncm_raw = re.sub(r"\s+", "", m.group(2))
        description = _compact(m.group(3))
        amount_str = m.group(4)
        unit_net_str = m.group(5)
        unit_gross_str = m.group(6)
        total_net_str = m.group(7)
        total_gross_str = m.group(8)

        # Skip header-like rows
        if description.lower().strip() in ("items description", "ncm"):
            continue

        try:
            units = int(units_str)
        except ValueError:
            units = None

        amount = parse_it_number(amount_str)
        unit_net = parse_it_number(unit_net_str)
        unit_gross = parse_it_number(unit_gross_str)
        total_net = parse_it_number(total_net_str)
        total_gross = parse_it_number(total_gross_str)

        is_packaging = ncm_raw.startswith(NCM_PACKAGING_PREFIX)

        rows.append(
            RawGroupedRow(
                units=units,
                ncm=ncm_raw,
                description=description,
                amount=amount,
                unit_net_weight=unit_net,
                unit_gross_weight=unit_gross,
                total_net_weight=total_net,
                total_gross_weight=total_gross,
                is_packaging=is_packaging,
                row_index=row_idx,
            )
        )
        row_idx += 1

    return rows


# ---------------------------------------------------------------------------
# Validation — emite WARNING para ambiguidade, não ERROR
# ---------------------------------------------------------------------------


def _validate(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []

    commercial_rows = [r for r in raw.grouped_rows if not r.is_packaging]
    packaging_rows = [r for r in raw.grouped_rows if r.is_packaging]

    if not raw.grouped_rows:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_GROUPED_ROWS",
                "message": "Nenhuma linha extraída do PL Grouped.",
                "target_type": "DOCUMENT",
            }
        )
        return issues

    # Each commercial row: emit AMBIGUITY warning (P0 decision — NOT commercial SoT)
    for row in commercial_rows:
        issues.append(
            {
                "severity": "WARNING",
                "code": "AMBIGUITY_PL_GROUPED",
                "message": (
                    f"PL Grouped linha '{row.description}' (NCM {row.ncm}, units={row.units}, "
                    f"amount={row.amount}): quantidade pode divergir da Fattura/PL Detalhado. "
                    "PL Grouped NÃO é SoT comercial — usar apenas como evidência de reconciliação."
                ),
                "target_type": "ROW",
                "target_id": row.row_index,
            }
        )

    # Packaging lines annotation
    for row in packaging_rows:
        issues.append(
            {
                "severity": "INFO",
                "code": "PACKAGING_LINE_NCM4819",
                "message": (
                    f"Linha '{row.description}' (NCM {row.ncm}) é embalagem (NCM 4819). "
                    "Não criar Product/OrderItem — candidato a ShipmentPackage."
                ),
                "target_type": "ROW",
                "target_id": row.row_index,
            }
        )

    # Dual origin annotation
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
                "locator_json": json.dumps(
                    {"field": "origin_country", "source": "layout_freetext"}
                ),
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Main extract
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    """Extração pura do PL Grouped."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    layout_pages: list[str] = []
    default_pages: list[str] = []
    for page in reader.pages:
        layout_pages.append(page.extract_text(extraction_mode="layout") or "")
        default_pages.append(page.extract_text() or "")

    layout_text = "\n".join(layout_pages)
    default_text = "\n".join(default_pages)

    header = _extract_header(default_text)
    grouped_rows = _parse_grouped_rows(layout_text)

    from app.ingestion.annotations import extract_origin_annotation

    ann = extract_origin_annotation(layout_text)

    doc_date_iso: str | None = None
    if header.get("document_date_raw"):
        doc_date_iso, _ = parse_it_date(header["document_date_raw"])

    return AdapterRawResult(
        supplier_name=header.get("supplier_name"),
        supplier_pi_cf=header.get("supplier_pi_cf"),
        document_number=header.get("document_number"),
        document_date_iso=doc_date_iso,
        currency=header.get("currency", "EUR"),
        incoterms=header.get("incoterms"),
        payment_terms=header.get("payment_terms"),
        origin_raw=ann.raw_value,
        origin_declared=ann.declared,
        origin_possible_other=ann.possible_other,
        grouped_rows=grouped_rows,
        raw_text_layout=layout_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    return bool(raw.supplier_name and "heroe" in raw.supplier_name.lower())


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
    issues = _validate(raw)

    sections = [
        {"section_key": "header", "title": "Cabeçalho PL Grouped", "ordinal": 0},
        {"section_key": "grouped_lines", "title": "Linhas Agrupadas", "ordinal": 1},
        {"section_key": "annotations", "title": "Anotações FreeText", "ordinal": 2},
    ]

    def _loc() -> str:
        return json.dumps({"page": 0, "source": "pypdf_layout"})

    fields = [
        {
            "section_key": "header",
            "field_key": "supplier_name",
            "value_type": "string",
            "raw_value": raw.supplier_name,
            "normalized_value": raw.supplier_name,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "document_number",
            "value_type": "string",
            "raw_value": raw.document_number,
            "normalized_value": raw.document_number,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "document_date",
            "value_type": "date",
            "raw_value": raw.document_date_iso,
            "normalized_value": raw.document_date_iso,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "currency",
            "value_type": "string",
            "raw_value": raw.currency,
            "normalized_value": raw.currency,
            "locator_json": None,
        },
        {
            "section_key": "header",
            "field_key": "is_sot",
            "value_type": "boolean",
            "raw_value": "false",
            "normalized_value": "false",
            "locator_json": None,
            "provenance_json": json.dumps({"reason": "P0 decision: PL Grouped = ambiguity evidence only"}),
        },
        {
            "section_key": "annotations",
            "field_key": "origin_country_raw",
            "value_type": "string",
            "raw_value": raw.origin_raw,
            "normalized_value": raw.origin_raw,
            "locator_json": json.dumps({"field": "origin_country", "source": "layout_freetext"}),
        },
        {
            "section_key": "annotations",
            "field_key": "origin_country_declared",
            "value_type": "string",
            "raw_value": raw.origin_declared,
            "normalized_value": raw.origin_declared,
            "locator_json": json.dumps({"field": "origin_country", "source": "layout_freetext", "layer": "declared"}),
        },
    ]

    if raw.origin_possible_other:
        fields.append(
            {
                "section_key": "annotations",
                "field_key": "origin_country_possible_other",
                "value_type": "string",
                "raw_value": raw.origin_possible_other,
                "normalized_value": raw.origin_possible_other,
                "locator_json": json.dumps(
                    {"field": "origin_country", "source": "layout_freetext", "layer": "background"}
                ),
            }
        )

    rows = []
    for row in raw.grouped_rows:
        cells = {
            "units": {"raw": str(row.units) if row.units is not None else None, "normalized": str(row.units) if row.units is not None else None},
            "ncm": {"raw": row.ncm, "normalized": row.ncm},
            "description": {"raw": row.description, "normalized": row.description},
            "amount": {"raw": str(row.amount) if row.amount is not None else None, "normalized": str(row.amount) if row.amount is not None else None},
            "total_net_weight_kg": {"raw": str(row.total_net_weight) if row.total_net_weight is not None else None, "normalized": str(row.total_net_weight) if row.total_net_weight is not None else None},
            "total_gross_weight_kg": {"raw": str(row.total_gross_weight) if row.total_gross_weight is not None else None, "normalized": str(row.total_gross_weight) if row.total_gross_weight is not None else None},
            "is_packaging": {"raw": str(row.is_packaging).lower(), "normalized": str(row.is_packaging).lower()},
        }
        rows.append(
            {
                "section_key": "grouped_lines",
                "row_index": row.row_index,
                "row_key": f"grp_{row.row_index}",
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
