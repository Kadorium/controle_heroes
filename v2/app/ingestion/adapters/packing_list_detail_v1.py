"""Adapter packing_list_detail_v1 — Packing List detalhado da Heroe's Srl.

Corpus: corpus_202/PackingList_202.pdf (7 páginas, 100 cartons).
Estratégia:
- pypdf DEFAULT mode → header + item rows
- pypdf LAYOUT mode → origin annotation (chinaItaly glued)
- Cada carton row = triplet: linha NCM-prefix / linha dados / linha NCM-suffix
- Rows IR = per-carton (até 100); reconciler agrupa por produto para comparar

Separação de responsabilidades:
- extract(bytes) → AdapterRawResult — puro, sem DB
- run_adapter(db, ...) → seeds IngestionDocument
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

ADAPTER_ID = "packing_list_detail_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "PACKING_LIST_DETAIL"

# Regex: pallet carton items [description] dimensions unit_net unit_gross total_net total_gross
_RE_DIMS = re.compile(r"\d+[,\.]\d+x\d+[,\.]\d+x\d+[,\.]\d+")
_RE_CARTON = re.compile(
    r"^(\d+)\s+(\d+)\s+(\d+)\s*(.*?)\s*"
    r"(\d+[,\.]\d+x\d+[,\.]\d+x\d+[,\.]\d+)\s+"
    r"([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)"
)
_RE_TOTALE = re.compile(r"Totale\s+([\d,\.]+)\s+([\d,\.]+)", re.IGNORECASE)
_RE_NCM_FRAG = re.compile(r"^[\d\s]+$")


def _compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _strip_non_digit_prefix(s: str) -> str:
    """Return only leading digits/spaces from a string."""
    m = re.match(r"^[\d\s]+", s)
    return m.group(0).strip() if m else ""


def _strip_alpha_suffix(s: str) -> str:
    """Return alphabetic/space tail of a string (after leading digits)."""
    m = re.search(r"[A-Za-z].*$", s)
    return m.group(0).strip() if m else ""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RawCartonRow:
    pallet_no: int
    carton_no: int
    items_per_ctn: int
    ncm: str | None
    description: str
    dimensions: str
    unit_net_weight: Decimal
    unit_gross_weight: Decimal
    total_net_weight: Decimal
    total_gross_weight: Decimal
    row_index: int


@dataclass
class AdapterRawResult:
    supplier_name: str | None
    supplier_pi_cf: str | None
    document_number: str | None
    document_date_iso: str | None
    document_date_needs_review: bool
    currency: str
    incoterms: str | None
    payment_terms: str | None
    delivery_terms: str | None
    total_net_weight: Decimal | None
    total_gross_weight_items: Decimal | None  # items only (excludes pallets)
    total_cartons: int
    origin_raw: str | None  # e.g. "chinaItaly" from layout mode
    origin_declared: str | None  # parsed declared value
    origin_possible_other: str | None  # second layer if dual
    carton_rows: list[RawCartonRow] = field(default_factory=list)
    raw_text_layout: str = ""


# ---------------------------------------------------------------------------
# Header extraction — default mode
# ---------------------------------------------------------------------------


def _extract_header(default_text: str) -> dict:
    lines = [l.strip() for l in default_text.splitlines() if l.strip()]
    result: dict = {}

    for i, line in enumerate(lines):
        low = line.lower().replace(" ", "")

        if "heroe" in low and "srl" in low:
            result.setdefault("supplier_name", "Heroe's Srl")

        m = re.search(r"PI\s*/\s*CF\s*:\s*([\d]+)\s*-", line, re.IGNORECASE)
        if m:
            pi_raw = re.sub(r"\s+", "", m.group(1))
            if len(pi_raw) >= 11:
                result.setdefault("supplier_pi_cf", pi_raw[:11])

        # Number / Date on same text region: "202 16/04/2026" (compact)
        m = re.search(r"\b(\d{1,4})\s+(\d{1,2}/\d{2}/\d{4})\b", line)
        if m and "document_number" not in result:
            num = m.group(1)
            date_raw = m.group(2)
            if 1 <= int(num) <= 9999:
                result.setdefault("document_number", num)
                result.setdefault("document_date_raw", date_raw)

        # Spaced digit pattern in layout-mode text: "2 0 2" + date
        m2 = re.search(r"\b(\d(?:\s+\d)+)\s+(\d{1,2}/\s*\d{2}/\s*\d{4})\b", line)
        if m2 and "document_number" not in result:
            num_raw = re.sub(r"\s+", "", m2.group(1))
            date_raw = re.sub(r"\s+", "", m2.group(2))
            if num_raw.isdigit() and 1 <= int(num_raw) <= 9999:
                result.setdefault("document_number", num_raw)
                result.setdefault("document_date_raw", date_raw)

        if "eur" in low and "incoterms" not in result:
            result.setdefault("currency", "EUR")

        if "ex works" in line.lower():
            result.setdefault("incoterms", "EX WORKS")

        if "bonifico" in low:
            result.setdefault("payment_terms", _compact(line))

        if "delivery terms" in low:
            result.setdefault("delivery_terms", _compact(line))

    return result


# ---------------------------------------------------------------------------
# Carton row extraction — default mode
# ---------------------------------------------------------------------------


def _parse_carton_rows(default_text: str) -> list[RawCartonRow]:
    """Parse per-carton rows from PL Detail default-mode text.

    Format (3-line triplet):
      Line A: NCM_prefix [desc_prefix]   e.g. "4202 2210" or "4202 WASH BAG"
      Line B: pallet carton items [desc] dimensions unit_net unit_gross total_net total_gross
      Line C: NCM_suffix [desc_suffix]   e.g. "00" or "221000 STARLIGHT"
    """
    lines = [l.rstrip() for l in default_text.splitlines()]
    rows: list[RawCartonRow] = []
    row_idx = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not _RE_DIMS.search(stripped):
            continue

        m = _RE_CARTON.match(stripped)
        if not m:
            continue

        pallet_no = int(m.group(1))
        carton_no = int(m.group(2))
        items = int(m.group(3))
        desc_in_line = m.group(4).strip()
        dims = m.group(5)
        unit_net = parse_it_number(m.group(6)) or Decimal("0")
        unit_gross = parse_it_number(m.group(7)) or Decimal("0")
        total_net = parse_it_number(m.group(8)) or Decimal("0")
        total_gross = parse_it_number(m.group(9)) or Decimal("0")

        # --- Look at surrounding lines for NCM and extra description ---
        ncm_digits = ""
        desc_prefix = ""
        desc_suffix = ""

        if i > 0:
            prev = lines[i - 1].strip()
            # NCM prefix: digits and spaces (whole line)
            ncm_digits += re.sub(r"\s+", "", _strip_non_digit_prefix(prev))
            desc_prefix = _strip_alpha_suffix(prev)

        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            ncm_digits += re.sub(r"\s+", "", _strip_non_digit_prefix(nxt))
            desc_suffix = _strip_alpha_suffix(nxt)

        parts = [x for x in [desc_prefix, desc_in_line, desc_suffix] if x]
        description = _compact(" ".join(parts))
        ncm = ncm_digits if ncm_digits else None

        rows.append(
            RawCartonRow(
                pallet_no=pallet_no,
                carton_no=carton_no,
                items_per_ctn=items,
                ncm=ncm,
                description=description,
                dimensions=dims,
                unit_net_weight=unit_net,
                unit_gross_weight=unit_gross,
                total_net_weight=total_net,
                total_gross_weight=total_gross,
                row_index=row_idx,
            )
        )
        row_idx += 1

    return rows


# ---------------------------------------------------------------------------
# Totals extraction
# ---------------------------------------------------------------------------


def _extract_totals(default_text: str) -> tuple[Decimal | None, Decimal | None]:
    """Extract 'Totale net gross' summary line."""
    m = _RE_TOTALE.search(default_text)
    if m:
        net = parse_it_number(m.group(1))
        gross = parse_it_number(m.group(2))
        return net, gross
    return None, None


# ---------------------------------------------------------------------------
# Math validation
# ---------------------------------------------------------------------------


def _validate_math(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []
    if not raw.carton_rows:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_CARTON_ROWS",
                "message": "Nenhum carton extraído do PL Detail.",
                "target_type": "DOCUMENT",
            }
        )
        return issues

    computed_net = sum(r.total_net_weight for r in raw.carton_rows)
    computed_gross = sum(r.total_gross_weight for r in raw.carton_rows)

    if raw.total_net_weight is not None:
        if abs(computed_net - raw.total_net_weight) > Decimal("0.5"):
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "TOTAL_NET_WEIGHT_MISMATCH",
                    "message": (
                        f"Soma net weight cartons ({computed_net}) difere do Totale "
                        f"({raw.total_net_weight})"
                    ),
                    "target_type": "DOCUMENT",
                }
            )

    if raw.total_cartons != len(raw.carton_rows):
        issues.append(
            {
                "severity": "WARNING",
                "code": "CARTON_COUNT_MISMATCH",
                "message": (
                    f"Cartons extraídos ({len(raw.carton_rows)}) ≠ declarados "
                    f"({raw.total_cartons})"
                ),
                "target_type": "DOCUMENT",
            }
        )

    # Origin dual-layer annotation
    if raw.origin_possible_other:
        issues.append(
            {
                "severity": "WARNING",
                "code": "DUAL_ORIGIN_ANNOTATION",
                "message": (
                    f"Campo 'Country of origin' contém duas camadas de texto: "
                    f"'{raw.origin_possible_other}' (fundo) + '{raw.origin_declared}' (declarado). "
                    "Verificar origem real da mercadoria."
                ),
                "target_type": "DOCUMENT",
                "locator_json": json.dumps(
                    {"field": "origin_country", "source": "layout_freetext"}
                ),
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Main extract function
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    """Extração pura — sem DB."""
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

    document_date_iso: str | None = None
    document_date_needs_review = False
    if header.get("document_date_raw"):
        document_date_iso, document_date_needs_review = parse_it_date(
            header["document_date_raw"]
        )

    carton_rows = _parse_carton_rows(default_text)
    total_net, total_gross = _extract_totals(default_text)
    total_cartons = int(header.get("total_cartons_raw", len(carton_rows)))

    # Origin annotation from layout mode
    from app.ingestion.annotations import extract_origin_annotation

    ann = extract_origin_annotation(layout_text)
    origin_raw = ann.raw_value
    origin_declared = ann.declared
    origin_possible_other = ann.possible_other

    return AdapterRawResult(
        supplier_name=header.get("supplier_name"),
        supplier_pi_cf=header.get("supplier_pi_cf"),
        document_number=header.get("document_number"),
        document_date_iso=document_date_iso,
        document_date_needs_review=document_date_needs_review,
        currency=header.get("currency", "EUR"),
        incoterms=header.get("incoterms"),
        payment_terms=header.get("payment_terms"),
        delivery_terms=header.get("delivery_terms"),
        total_net_weight=total_net,
        total_gross_weight_items=total_gross,
        total_cartons=total_cartons,
        origin_raw=origin_raw,
        origin_declared=origin_declared,
        origin_possible_other=origin_possible_other,
        carton_rows=carton_rows,
        raw_text_layout=layout_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    """True se parece ser um PL Detail da Heroe's Srl."""
    if raw.supplier_name and "heroe" in raw.supplier_name.lower():
        return True
    return False


# ---------------------------------------------------------------------------
# Full adapter run (DB-aware)
# ---------------------------------------------------------------------------


def run_adapter(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str,
    quarantine_path: Path,
) -> "IngestionDocument":  # noqa: F821
    """Extrai PL Detail, semeia IR."""
    occ = db.get(IngestionOccurrence, occurrence_id)
    if occ is None:
        from app.ingestion.errors import OccurrenceNotFound

        raise OccurrenceNotFound(occurrence_id)

    if occ.blob is None or occ.blob.physical_status != "PRESENT" or not occ.blob.storage_path:
        raise IngestionError(
            f"Blob da occurrence {occurrence_id} indisponível",
            code="blob_unavailable",
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
        {"section_key": "header", "title": "Cabeçalho do Packing List", "ordinal": 0},
        {"section_key": "cartons", "title": "Linhas de Carton", "ordinal": 1},
        {"section_key": "annotations", "title": "Anotações FreeText", "ordinal": 2},
    ]

    def _locator(page: int = 0) -> str:
        return json.dumps({"page": page, "source": "pypdf_layout"})

    fields = [
        {
            "section_key": "header",
            "field_key": "supplier_name",
            "value_type": "string",
            "raw_value": raw.supplier_name,
            "normalized_value": raw.supplier_name,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "supplier_pi_cf",
            "value_type": "string",
            "raw_value": raw.supplier_pi_cf,
            "normalized_value": raw.supplier_pi_cf,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "document_number",
            "value_type": "string",
            "raw_value": raw.document_number,
            "normalized_value": raw.document_number,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "document_date",
            "value_type": "date",
            "raw_value": raw.document_date_iso,
            "normalized_value": raw.document_date_iso,
            "locator_json": _locator(),
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
            "field_key": "incoterms",
            "value_type": "string",
            "raw_value": raw.incoterms,
            "normalized_value": raw.incoterms,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "payment_terms",
            "value_type": "string",
            "raw_value": raw.payment_terms,
            "normalized_value": raw.payment_terms,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_net_weight_kg",
            "value_type": "decimal",
            "raw_value": str(raw.total_net_weight) if raw.total_net_weight is not None else None,
            "normalized_value": str(raw.total_net_weight) if raw.total_net_weight is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_gross_weight_kg",
            "value_type": "decimal",
            "raw_value": str(raw.total_gross_weight_items) if raw.total_gross_weight_items is not None else None,
            "normalized_value": str(raw.total_gross_weight_items) if raw.total_gross_weight_items is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_cartons",
            "value_type": "integer",
            "raw_value": str(raw.total_cartons),
            "normalized_value": str(raw.total_cartons),
            "locator_json": _locator(),
        },
        # Annotation fields
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
    for cr in raw.carton_rows:
        cells = {
            "pallet_no": {"raw": str(cr.pallet_no), "normalized": str(cr.pallet_no)},
            "carton_no": {"raw": str(cr.carton_no), "normalized": str(cr.carton_no)},
            "items_per_ctn": {"raw": str(cr.items_per_ctn), "normalized": str(cr.items_per_ctn)},
            "ncm": {"raw": cr.ncm, "normalized": cr.ncm},
            "description": {"raw": cr.description, "normalized": cr.description},
            "dimensions": {"raw": cr.dimensions, "normalized": cr.dimensions},
            "unit_net_weight_kg": {"raw": str(cr.unit_net_weight), "normalized": str(cr.unit_net_weight)},
            "unit_gross_weight_kg": {"raw": str(cr.unit_gross_weight), "normalized": str(cr.unit_gross_weight)},
            "total_net_weight_kg": {"raw": str(cr.total_net_weight), "normalized": str(cr.total_net_weight)},
            "total_gross_weight_kg": {"raw": str(cr.total_gross_weight), "normalized": str(cr.total_gross_weight)},
        }
        rows.append(
            {
                "section_key": "cartons",
                "row_index": cr.row_index,
                "row_key": f"ctn_{cr.carton_no}",
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
