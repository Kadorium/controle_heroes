"""Adapter print_declaration_v1 — Dichiarazione di Libera Esportazione.

Corpus: corpus_202/PrintDeclaration_202.pdf (2 páginas).
Decisão P0: texto livre + coleção estruturada de Y-codes SEM coluna fixa por código.
- Sem line items comerciais
- Seção 'declarations' = coleção JSON de {y_code, title, text_snippet}
- Sem catalog matching
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion import staging_commands
from app.ingestion import storage as quarantine_storage
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.ingestion.parse_it import parse_it_date

ADAPTER_ID = "print_declaration_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "PRINT_DECLARATION"

# Y-code pattern: "certificato Y900", "certificati Y904 - Y905 - Y906", "Y932", etc.
_RE_YCODES = re.compile(
    r"\b(Y\d{3,4})\b",
    re.IGNORECASE,
)

# Known Y-code titles from the standard dictionary
_YTITLE: dict[str, str] = {
    "Y900": "Dichiarazione di Washington (flora/fauna)",
    "Y901": "Duplice uso",
    "Y902": "Dichiarazione per l'ozono",
    "Y903": "Beni culturali",
    "Y904": "Pena di morte / tortura (1)",
    "Y905": "Pena di morte / tortura (2)",
    "Y906": "Pena di morte / tortura (3)",
    "Y908": "Pena di morte / tortura (4)",
    "Y909": "Controllo pesca",
    "Y911": "Iran",
    "Y916": "Sostanze chimiche pericolose (1)",
    "Y917": "Sostanze chimiche pericolose (2)",
    "Y920": "Misure restrittive paese",
    "Y921": "Misure restrittive paese (2)",
    "Y922": "Pellicce cani/gatti",
    "Y923": "Gestione rifiuti",
    "Y924": "Mercurio",
    "Y926": "Gas fluorurati",
    "Y927": "Pesca illegale",
    "Y032": "Prodotti foca",
    "Y935": "Autorizzazione all'esportazione",
    "Y939": "Reg. UE 833/2014",
    "Y949": "Iran merci alternative",
    "Y966": "Iran beni alternativi",
    "Y975": "Reg. UE 2020/402",
}


def _compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RawDeclaration:
    y_codes: list[str]
    title: str
    text_snippet: str
    row_index: int


@dataclass
class AdapterRawResult:
    declarant_name: str | None
    company_name: str | None
    invoice_ref: str | None
    destination: str | None
    document_date_iso: str | None
    subject: str | None
    declarations: list[RawDeclaration] = field(default_factory=list)
    all_y_codes: list[str] = field(default_factory=list)
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Header extraction
# ---------------------------------------------------------------------------


def _extract_header(text: str) -> dict:
    result: dict = {}

    # Subject line
    m = re.search(r"OGGETTO\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["subject"] = _compact(m.group(1))

    # Declarant: "Io ANDREA BRUNELLI sottoscritto"
    m = re.search(r"Io\s+([A-Z][A-Z\s]+)\s+sottoscritto", text)
    if m:
        result["declarant_name"] = _compact(m.group(1))

    # Company: "LEGALE RAPPRESENTANTE DI HEROE'S SRL"
    m = re.search(r"LEGALE\s+RAPPRESENTANTE\s+DI\s+(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["company_name"] = _compact(m.group(1))

    # Invoice ref: "ns. fattura 202"
    m = re.search(r"fattura\s+(\d+)", text, re.IGNORECASE)
    if m:
        result["invoice_ref"] = m.group(1)

    # Destination: "con destinazione BRASILE"
    m = re.search(r"con destinazione\s+(\w+)", text, re.IGNORECASE)
    if m:
        result["destination"] = _compact(m.group(1))

    # Date: "data 16/04/2026"
    m = re.search(r"data\s+(\d{1,2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if m:
        result["document_date_raw"] = m.group(1)

    return result


# ---------------------------------------------------------------------------
# Y-code section extraction
# ---------------------------------------------------------------------------


def _parse_declarations(text: str) -> tuple[list[RawDeclaration], list[str]]:
    """Extract declaration blocks by DICHIARAZIONE sections."""
    declarations: list[RawDeclaration] = []
    all_y_codes_seen: list[str] = []
    seen_codes: set[str] = set()

    # Split on each "DICHIARAZIONE" section header
    section_re = re.compile(
        r"(DICHIARAZIONE\s+[^\n]+(?:\n[^\n]+)*?)(?=DICHIARAZIONE|$)",
        re.IGNORECASE | re.DOTALL,
    )

    # Fallback: find all Y-codes in the whole text
    all_codes_in_text = _RE_YCODES.findall(text)
    for c in all_codes_in_text:
        uc = c.upper()
        if uc not in seen_codes:
            seen_codes.add(uc)
            all_y_codes_seen.append(uc)

    # Build declaration rows from section blocks
    row_idx = 0
    for section_match in section_re.finditer(text):
        block = section_match.group(1)
        # Extract Y-codes from this block
        y_codes = list({c.upper() for c in _RE_YCODES.findall(block)})
        # Title = first line
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        title = lines[0] if lines else ""
        # Snippet = first meaningful sentence (up to 200 chars)
        snippet = _compact(block)[:200] if block else ""

        if y_codes or title:
            declarations.append(
                RawDeclaration(
                    y_codes=sorted(y_codes),
                    title=_compact(title),
                    text_snippet=snippet,
                    row_index=row_idx,
                )
            )
            row_idx += 1

    # If section parsing yielded nothing, create a single aggregate row
    if not declarations and all_y_codes_seen:
        declarations.append(
            RawDeclaration(
                y_codes=all_y_codes_seen,
                title="Dichiarazioni multiple",
                text_snippet=_compact(text[:300]),
                row_index=0,
            )
        )

    return declarations, all_y_codes_seen


# ---------------------------------------------------------------------------
# Main extract
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")

    text = "\n".join(pages)
    header = _extract_header(text)
    declarations, all_y_codes = _parse_declarations(text)

    doc_date_iso: str | None = None
    if header.get("document_date_raw"):
        doc_date_iso, _ = parse_it_date(header["document_date_raw"])

    return AdapterRawResult(
        declarant_name=header.get("declarant_name"),
        company_name=header.get("company_name"),
        invoice_ref=header.get("invoice_ref"),
        destination=header.get("destination"),
        document_date_iso=doc_date_iso,
        subject=header.get("subject"),
        declarations=declarations,
        all_y_codes=all_y_codes,
        raw_text=text,
    )


def classify(raw: AdapterRawResult) -> bool:
    if raw.company_name and "heroe" in raw.company_name.lower():
        return True
    if raw.subject and "libera esportazione" in raw.subject.lower():
        return True
    return False


def _validate(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []
    if not raw.declarations:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_DECLARATIONS_EXTRACTED",
                "message": "Nenhum bloco de declaração Y-code extraído do PrintDeclaration.",
                "target_type": "DOCUMENT",
            }
        )
    if not raw.invoice_ref:
        issues.append(
            {
                "severity": "WARNING",
                "code": "INVOICE_REF_MISSING",
                "message": "Referência de fattura não encontrada no PrintDeclaration.",
                "target_type": "DOCUMENT",
            }
        )
    return issues


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
        {"section_key": "header", "title": "Cabeçalho PrintDeclaration", "ordinal": 0},
        {
            "section_key": "declarations",
            "title": "Declarações Y-code (coleção estruturada)",
            "ordinal": 1,
        },
    ]

    def _loc(p: int = 0) -> str:
        return json.dumps({"page": p, "source": "pypdf_default"})

    # Y-codes as JSON collection (no fixed DB column per Y-code — P0 decision)
    y_codes_json = json.dumps(
        [
            {
                "y_codes": decl.y_codes,
                "titles": [_YTITLE.get(c, c) for c in decl.y_codes],
                "title_raw": decl.title,
                "snippet": decl.text_snippet,
            }
            for decl in raw.declarations
        ],
        ensure_ascii=False,
    )

    fields = [
        {
            "section_key": "header",
            "field_key": "declarant_name",
            "value_type": "string",
            "raw_value": raw.declarant_name,
            "normalized_value": raw.declarant_name,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "company_name",
            "value_type": "string",
            "raw_value": raw.company_name,
            "normalized_value": raw.company_name,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "invoice_ref",
            "value_type": "string",
            "raw_value": raw.invoice_ref,
            "normalized_value": raw.invoice_ref,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "destination",
            "value_type": "string",
            "raw_value": raw.destination,
            "normalized_value": raw.destination,
            "locator_json": _loc(),
        },
        {
            "section_key": "header",
            "field_key": "document_date",
            "value_type": "date",
            "raw_value": raw.document_date_iso,
            "normalized_value": raw.document_date_iso,
            "locator_json": _loc(1),
        },
        {
            "section_key": "header",
            "field_key": "subject",
            "value_type": "string",
            "raw_value": raw.subject,
            "normalized_value": raw.subject,
            "locator_json": _loc(),
        },
        {
            "section_key": "declarations",
            "field_key": "y_codes_collection_json",
            "value_type": "json",
            "raw_value": y_codes_json,
            "normalized_value": y_codes_json,
            "locator_json": None,
            "provenance_json": json.dumps(
                {"note": "P0: no fixed DB column per Y-code; structured collection"}
            ),
        },
        {
            "section_key": "declarations",
            "field_key": "all_y_codes_csv",
            "value_type": "string",
            "raw_value": ",".join(raw.all_y_codes),
            "normalized_value": ",".join(raw.all_y_codes),
            "locator_json": None,
        },
    ]

    # One row per declaration block
    rows = []
    for decl in raw.declarations:
        cells = {
            "y_codes": {"raw": json.dumps(decl.y_codes), "normalized": json.dumps(decl.y_codes)},
            "title": {"raw": decl.title, "normalized": decl.title},
            "snippet": {"raw": decl.text_snippet, "normalized": decl.text_snippet},
        }
        rows.append(
            {
                "section_key": "declarations",
                "row_index": decl.row_index,
                "row_key": f"decl_{decl.row_index}",
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
