"""Adapter fattura_heroes_v1 — extrator de Fattura di Vendita da Heroe's Srl.

Corpus: Fattura_202 (corpus_202/Fattura_202.pdf).
Estratégia:
- pypdf DEFAULT mode → cabeçalho, scadenze, pagamento (texto limpo, não spaced)
- pypdf LAYOUT mode → tabela de linhas (EAN + descr + UM + qty + preço + total + IVA)
- parse_it para números e datas italianos

Separação de responsabilidades:
- extract(bytes) → AdapterRawResult — puro, sem DB
- match_catalog(db, raw) → enrich issues para SKUs ambíguos/não encontrados
- run_adapter(db, occurrence_id, actor_id, quarantine_path) → seeds IngestionDocument

Regras:
- SKUs EAN (13+ dígitos) são buscados primeiro por EAN exato, depois por fragment
- Scadenze extraídas do texto e armazenadas em campo scadenze_json (lista de dicts)
- payment_terms_text preservado tal qual
- DDT ref preservado
- Totale esenti iva = TOTALE DOCUMENTO (exportação N3.1, IVA zero)
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.ingestion import staging_commands
from app.ingestion import storage as quarantine_storage
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.ingestion.parse_it import parse_it_date, parse_it_number

ADAPTER_ID = "fattura_heroes_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "FATTURA_VENDITA"


def _compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _strip_currency(s: str) -> str:
    return re.sub(r"[€\s]", "", s).strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RawScadenza:
    due_date_raw: str
    due_date_iso: str | None
    amount: Decimal
    sequence: int


@dataclass
class RawLineItem:
    sku: str
    description: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    iva_code: str
    row_index: int


@dataclass
class AdapterRawResult:
    supplier_name: str | None
    supplier_pi_cf: str | None
    invoice_number: str | None
    invoice_date_iso: str | None
    invoice_date_needs_review: bool
    currency: str
    ddt_ref: str | None
    payment_terms_text: str | None
    total_document: Decimal | None
    total_taxable: Decimal | None
    total_exempt: Decimal | None
    total_taxes: Decimal | None
    total_discounts: Decimal | None
    scadenze: list[RawScadenza] = field(default_factory=list)
    lines: list[RawLineItem] = field(default_factory=list)
    raw_text: str = ""
    destination_iban: str | None = None
    destination_bank: str | None = None


# ---------------------------------------------------------------------------
# Header extraction — uses default-mode text (clean, no font encoding gaps)
# ---------------------------------------------------------------------------


def _extract_header(default_text: str) -> dict:
    """Extract header fields from default-mode pypdf text.

    Default mode produces clean lines like:
      Numero:
      202
      Del:
      30/03/2026
      TOTALE DOCUMENTO:
      € 30.188,00
    """
    lines = [l.strip() for l in default_text.splitlines() if l.strip()]
    result: dict = {}

    # Find values by label on prior line
    for i, line in enumerate(lines):
        low = line.lower().replace(" ", "")

        # Supplier name: "Heroe's Srl" in the footer repeated block
        if "heroe" in low and "srl" in low:
            result.setdefault("supplier_name", "Heroe's Srl")

        # PI/CF: "PI / CF: 02610500395 - 02610500395" on one line
        m = re.search(r"PI\s*/\s*CF\s*:\s*([\d]+)\s*-", line, re.IGNORECASE)
        if m:
            pi_raw = re.sub(r"\s+", "", m.group(1))
            if len(pi_raw) >= 11:
                result.setdefault("supplier_pi_cf", pi_raw[:11])

        # Invoice number — "Numero:" on line, value on next line
        if re.match(r"^Numero\s*:", line, re.IGNORECASE):
            if i + 1 < len(lines):
                num = lines[i + 1].strip()
                if re.match(r"^\d+$", num):
                    result.setdefault("invoice_number", num)

        # Invoice date — "Del:" on line, value on next line
        if re.match(r"^D\s*e\s*l\s*:", line, re.IGNORECASE):
            if i + 1 < len(lines):
                d = lines[i + 1].strip()
                m2 = re.match(r"(\d{1,2}/\d{2}/\d{4})", d)
                if m2:
                    result.setdefault("invoice_date_raw", m2.group(1))

        # DDT ref: "DDT 389 - 30/03/2026" on one line
        m = re.search(r"DDT\s+(\d+)\s*-\s*(\d{1,2}/\d{2}/\d{4})", line, re.IGNORECASE)
        if m:
            result.setdefault("ddt_ref", f"DDT {m.group(1)} - {m.group(2)}")

        # Payment terms — "Pagamento:" on line, value on next line
        if re.match(r"^Pagamento\s*:", line, re.IGNORECASE):
            if i + 1 < len(lines):
                result.setdefault("payment_terms_text", lines[i + 1].strip())
            dest = _extract_payment_destination(lines, i)
            if dest.get("destination_iban"):
                result.setdefault("destination_iban", dest["destination_iban"])
            if dest.get("destination_bank"):
                result.setdefault("destination_bank", dest["destination_bank"])

        # TOTALE DOCUMENTO — label on line, value on next line
        if re.match(r"^TOTALE\s+DOCUMENTO\s*:", line, re.IGNORECASE):
            if i + 1 < len(lines):
                val = _strip_currency(lines[i + 1])
                if val:
                    result.setdefault("total_document", val)

        # Totale imponibile — label on line, value on next (or same)
        if re.match(r"^Totale\s+imponibile\s*:", line, re.IGNORECASE):
            # Try inline
            m2 = re.search(r"[€\s]*([\d.,]+)", line)
            if m2:
                result.setdefault("total_taxable", _strip_currency(m2.group(1)))
            elif i + 1 < len(lines):
                val = _strip_currency(lines[i + 1])
                if val:
                    result.setdefault("total_taxable", val)

        # Totale esenti iva
        if re.match(r"^Totale\s+esenti\s+iva\s*:", line, re.IGNORECASE):
            m2 = re.search(r"[€\s]*([\d.,]+)", line)
            if m2:
                result.setdefault("total_exempt", _strip_currency(m2.group(1)))
            elif i + 1 < len(lines):
                val = _strip_currency(lines[i + 1])
                if val:
                    result.setdefault("total_exempt", val)

        # IMPOSTE
        if re.match(r"^IMPOSTE\s*:", line, re.IGNORECASE):
            m2 = re.search(r"[€\s]*([\d.,]+)", line)
            if m2:
                result.setdefault("total_taxes", _strip_currency(m2.group(1)))
            elif i + 1 < len(lines):
                val = _strip_currency(lines[i + 1])
                if val:
                    result.setdefault("total_taxes", val)

        # SCONTI
        if re.match(r"^SCONTI\s*:", line, re.IGNORECASE):
            m2 = re.search(r"[€\s]*([\d.,]+)", line)
            if m2:
                result.setdefault("total_discounts", _strip_currency(m2.group(1)))
            elif i + 1 < len(lines):
                val = _strip_currency(lines[i + 1])
                if val:
                    result.setdefault("total_discounts", val)

    return result


# Italian IBAN = 27 chars. Do NOT take letterhead INTESA — only the block after Pagamento.
_RE_IT_IBAN = re.compile(r"(IT[0-9]{2}[A-Z0-9]{23})", re.IGNORECASE)


def _extract_payment_destination(lines: list[str], pagamento_idx: int) -> dict:
    """Banco + IBAN da linha de pagamento (após Pagamento:), nunca o rodapé."""
    out: dict = {}
    start = pagamento_idx + 2
    end = min(pagamento_idx + 8, len(lines))
    for j in range(start, end):
        line = lines[j].strip()
        if re.match(r"^Scadenze\s*:", line, re.IGNORECASE):
            break
        compact = re.sub(r"\s+", "", line)
        m = _RE_IT_IBAN.search(compact)
        if not m:
            continue
        iban = m.group(1).upper()
        out["destination_iban"] = iban
        bank = re.sub(_RE_IT_IBAN, "", line).replace("-", " ")
        bank = re.sub(r"\s+", " ", bank).strip(" -")
        if bank:
            out["destination_bank"] = bank[:128]
        break
    return out


# ---------------------------------------------------------------------------
# Scadenze extraction — uses default-mode text
# ---------------------------------------------------------------------------


def _extract_scadenze(default_text: str) -> list[RawScadenza]:
    """Extrai scadenze do default-mode text.

    Default mode format (each value on own line):
      Scadenze:
      30/03/2026
      15.094,00 €
      Scadenze:
      30/06/2026
      15.094,00 €
    """
    scadenze: list[RawScadenza] = []
    lines = [l.strip() for l in default_text.splitlines() if l.strip()]

    seq = 1
    i = 0
    while i < len(lines):
        if re.match(r"^Scadenze\s*:", lines[i], re.IGNORECASE):
            # Expect next two lines: date and amount
            date_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            amount_line = lines[i + 2].strip() if i + 2 < len(lines) else ""

            # Sometimes date and amount are on same line: "30/03/2026 15.094,00 €"
            m_combined = re.search(
                r"(\d{1,2}/\d{2}/\d{4})\s+([\d.,]+)\s*[€E]?", lines[i]
            )
            if not m_combined and i + 1 < len(lines):
                m_combined = re.search(
                    r"(\d{1,2}/\d{2}/\d{4})\s+([\d.,]+)\s*[€E]?", lines[i + 1]
                )

            m_date = re.match(r"(\d{1,2}/\d{2}/\d{4})", date_line)
            m_amount = re.search(r"([\d.,]+)", _strip_currency(amount_line))

            if m_date and m_amount:
                date_raw = m_date.group(1)
                date_iso, _ = parse_it_date(date_raw)
                amount = parse_it_number(m_amount.group(1)) or Decimal("0")
                scadenze.append(
                    RawScadenza(
                        due_date_raw=date_raw,
                        due_date_iso=date_iso,
                        amount=amount,
                        sequence=seq,
                    )
                )
                seq += 1
                i += 3
                continue
        i += 1

    return scadenze


# ---------------------------------------------------------------------------
# Line item extraction
# ---------------------------------------------------------------------------

# Pattern: EAN(13+ digits) DESCRIPTION(any) UNIT QTY € PRICE € TOTAL IVA_CODE
# Handles dots as thousands separators in price/total (e.g. 1.300,00)
_RE_LINE = re.compile(
    r"(\d{7,16})"           # EAN/code (group 1)
    r"\s+"
    r"(.+?)"                # description (group 2, non-greedy)
    r"\s+(PZ|KG|MT|LT|CF)"  # unit (group 3)
    r"\s+(\d[\d.,]*)"       # qty (group 4)
    r"\s+€\s*([\d.,]+)"     # unit_price (group 5)
    r"\s+€\s*([\d.,]+)"     # line_total (group 6)
    r"\s+([A-Z]\d+\.\d+)",  # iva_code (group 7)
    re.IGNORECASE,
)


_RE_SHORT_SKU_ITEM = re.compile(
    r"^\s*(\d{1,6})\s+.+\s+(PZ|KG|MT|LT|CF)\s+",
    re.IGNORECASE,
)


def _unparsed_line_issues(layout_text: str) -> list[dict]:
    """Linha de item visível que o EAN 7–16 não capturou — ERROR, não alargar o regex."""
    issues: list[dict] = []
    for idx, line in enumerate(layout_text.splitlines()):
        if _RE_LINE.search(line):
            continue
        m = _RE_SHORT_SKU_ITEM.search(line)
        if not m:
            continue
        sku = m.group(1)
        issues.append(
            {
                "severity": "ERROR",
                "code": "UNPARSED_LINE",
                "message": (
                    f"Linha de item com código '{sku}' não extraída "
                    "(código com menos de 7 dígitos; o adapter exige EAN 7–16). "
                    "Revise o PDF — commit bloqueado."
                ),
                "target_type": "ROW",
                "target_id": idx,
            }
        )
    return issues


def _parse_lines_from_layout(layout_text: str) -> list[RawLineItem]:
    lines: list[RawLineItem] = []
    for idx, m in enumerate(_RE_LINE.finditer(layout_text)):
        sku = m.group(1).strip()
        description = _compact(m.group(2))
        unit = m.group(3).strip().upper()
        qty = parse_it_number(m.group(4).strip()) or Decimal("0")
        unit_price = parse_it_number(m.group(5).strip()) or Decimal("0")
        line_total = parse_it_number(m.group(6).strip()) or Decimal("0")
        iva_code = m.group(7).strip()
        lines.append(
            RawLineItem(
                sku=sku,
                description=description,
                unit=unit,
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
                iva_code=iva_code,
                row_index=idx,
            )
        )
    return lines


# ---------------------------------------------------------------------------
# Math validation
# ---------------------------------------------------------------------------


def _validate_math(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []
    issues.extend(_unparsed_line_issues(raw.raw_text or ""))

    if not raw.lines:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_LINE_ITEMS",
                "message": "Nenhum item extraído da Fattura — verifique o PDF.",
                "target_type": "DOCUMENT",
            }
        )
        taxable = raw.total_taxable if raw.total_taxable is not None else Decimal("0")
        exempt = raw.total_exempt if raw.total_exempt is not None else Decimal("0")
        if raw.total_taxable is not None or raw.total_exempt is not None:
            bases = taxable + exempt
            if abs(Decimal("0") - bases) > Decimal("0.02"):
                issues.append(
                    {
                        "severity": "ERROR",
                        "code": "MATH_LINES_VS_TAX_BASES",
                        "message": (
                            f"Soma das linhas (0) difere de imponibile+esenti ({bases})"
                        ),
                        "target_type": "DOCUMENT",
                        "entity_type": "DOCUMENT",
                    }
                )
    else:
        from app.ingestion.adapters.ordine_heroes_v1 import _validate_math_heroes_pdf

        issues.extend(
            _validate_math_heroes_pdf(
                lines=raw.lines,
                total_document=raw.total_document,
                total_taxable=raw.total_taxable,
                total_exempt=raw.total_exempt,
                total_taxes=raw.total_taxes,
                total_discounts=raw.total_discounts,
                shipping_spese=None,
            )
        )

    # Validate scadenze sum = total document
    if raw.scadenze and raw.total_document is not None:
        scad_sum = sum(s.amount for s in raw.scadenze)
        if abs(scad_sum - raw.total_document) > Decimal("0.02"):
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "SCADENZE_SUM_MISMATCH",
                    "message": (
                        f"Soma das scadenze ({scad_sum}) difere do total ({raw.total_document})"
                    ),
                    "target_type": "DOCUMENT",
                }
            )

    return issues


# ---------------------------------------------------------------------------
# Catalog matching
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    supplier_id: int | None
    supplier_found: bool
    line_matches: dict[str, int | None]
    ambiguous_skus: set[str]


def match_catalog(db: Session, raw: AdapterRawResult) -> tuple[MatchResult, list[dict]]:
    """Resolve Supplier e Products via Catalog public API.

    SKUs EAN: busca por EAN exato primeiro; se não encontrado → AMBIGUOUS_SKU.
    NUNCA silencioso.
    """
    issues: list[dict] = []

    # --- supplier ---
    supplier_id: int | None = None
    supplier_found = False

    search_terms: list[str] = []
    if raw.supplier_pi_cf:
        search_terms.append(raw.supplier_pi_cf)
    if raw.supplier_name:
        search_terms.append(raw.supplier_name)
    search_terms.append("Heroe")

    for term in search_terms:
        try:
            results = catalog_public.list_suppliers(db, q=term, limit=5)
        except Exception:
            results = []
        if len(results) == 1:
            supplier_id = results[0].id
            supplier_found = True
            break
        elif len(results) > 1:
            target = (raw.supplier_name or "").strip().lower()
            exact = [
                s for s in results if (s.name or "").strip().lower() == target
            ]
            if len(exact) == 1:
                supplier_id = exact[0].id
                supplier_found = True
                break
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "AMBIGUOUS_SUPPLIER",
                    "message": (
                        f"Múltiplos fornecedores encontrados para '{term}': "
                        f"{[s.id for s in results]}."
                    ),
                    "target_type": "DOCUMENT",
                }
            )
            break

    if not supplier_found:
        issues.append(
            {
                "severity": "WARNING",
                "code": "SUPPLIER_NOT_FOUND",
                "message": (
                    f"Fornecedor '{raw.supplier_name or raw.supplier_pi_cf}' não encontrado "
                    "no catálogo."
                ),
                "target_type": "DOCUMENT",
            }
        )

    # --- products by EAN ---
    line_matches: dict[str, int | None] = {}
    ambiguous_skus: set[str] = set()

    for line in raw.lines:
        sku = line.sku
        product_id: int | None = None

        # Try exact SKU/EAN match first
        try:
            product = catalog_public.get_product_by_sku(db, sku)
            product_id = product.id
        except Exception:
            product_id = None

        if product_id is None:
            try:
                results = catalog_public.list_products(db, q=sku, limit=5)
            except Exception:
                results = []

            if len(results) == 1:
                product_id = results[0].id
            elif len(results) > 1:
                ambiguous_skus.add(sku)
                issues.append(
                    {
                        "severity": "WARNING",
                        "code": "AMBIGUOUS_SKU",
                        "message": (
                            f"EAN '{sku}' ambíguo: {len(results)} produtos no catálogo. "
                            "Requer revisão de matching antes do commit."
                        ),
                        "target_type": "ROW",
                        "target_id": line.row_index,
                        "entity_type": "PRODUCT",
                    }
                )
            else:
                ambiguous_skus.add(sku)
                issues.append(
                    {
                        "severity": "WARNING",
                        "code": "UNMATCHED_SKU",
                        "message": (
                            f"EAN '{sku}' não encontrado no catálogo. "
                            "Requer matching manual ou criar produto antes do commit."
                        ),
                        "target_type": "ROW",
                        "target_id": line.row_index,
                        "entity_type": "PRODUCT",
                    }
                )

        line_matches[sku] = product_id

    return (
        MatchResult(
            supplier_id=supplier_id,
            supplier_found=supplier_found,
            line_matches=line_matches,
            ambiguous_skus=ambiguous_skus,
        ),
        issues,
    )


# ---------------------------------------------------------------------------
# Main extract function
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    """Extração pura do PDF — sem DB. Retorna campos + linhas + scadenze brutos."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))

    layout_pages: list[str] = []
    default_pages: list[str] = []
    for page in reader.pages:
        layout_pages.append(page.extract_text(extraction_mode="layout") or "")
        default_pages.append(page.extract_text() or "")

    layout_text = "\n".join(layout_pages)
    default_text = "\n".join(default_pages)

    # --- header from default mode (cleaner, no spaced chars) ---
    header = _extract_header(default_text)

    invoice_date_iso: str | None = None
    invoice_date_needs_review = False
    if header.get("invoice_date_raw"):
        invoice_date_iso, invoice_date_needs_review = parse_it_date(header["invoice_date_raw"])

    total_document = parse_it_number(header.get("total_document"))
    total_taxable = parse_it_number(header.get("total_taxable"))
    total_exempt = parse_it_number(header.get("total_exempt"))
    total_taxes = parse_it_number(header.get("total_taxes"))
    total_discounts = parse_it_number(header.get("total_discounts"))

    # --- scadenze from default mode ---
    scadenze = _extract_scadenze(default_text)

    # --- lines from layout mode (preserves column alignment for EAN rows) ---
    lines = _parse_lines_from_layout(layout_text)

    return AdapterRawResult(
        supplier_name=header.get("supplier_name"),
        supplier_pi_cf=header.get("supplier_pi_cf"),
        invoice_number=header.get("invoice_number"),
        invoice_date_iso=invoice_date_iso,
        invoice_date_needs_review=invoice_date_needs_review,
        currency="EUR",
        ddt_ref=header.get("ddt_ref"),
        payment_terms_text=header.get("payment_terms_text"),
        destination_iban=header.get("destination_iban"),
        destination_bank=header.get("destination_bank"),
        total_document=total_document,
        total_taxable=total_taxable,
        total_exempt=total_exempt,
        total_taxes=total_taxes,
        total_discounts=total_discounts,
        scadenze=scadenze,
        lines=lines,
        raw_text=layout_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    """True se o documento parece ser uma Fattura da Heroe's Srl."""
    if raw.supplier_name and "heroe" in raw.supplier_name.lower():
        if raw.invoice_number and raw.invoice_date_iso:
            return True
    if raw.supplier_pi_cf and raw.invoice_number:
        return True
    return False


# ---------------------------------------------------------------------------
# Full adapter run (DB-aware): extract + validate + match + seed IR
# ---------------------------------------------------------------------------


def run_adapter(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str,
    quarantine_path: Path,
) -> "IngestionDocument":  # noqa: F821
    """Extrai Fattura do blob, valida, corresponde catálogo, semeia IR."""
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
    match_result, match_issues = match_catalog(db, raw)
    issues.extend(match_issues)

    sections = [
        {"section_key": "header", "title": "Cabeçalho da Fattura", "ordinal": 0},
        {"section_key": "lines", "title": "Linhas da Fattura", "ordinal": 1},
        {"section_key": "payment", "title": "Condições de Pagamento", "ordinal": 2},
    ]

    def _locator(page: int = 0) -> str:
        return json.dumps({"page": page, "source": "pypdf_layout"})

    scadenze_json = json.dumps(
        [
            {
                "sequence": s.sequence,
                "due_date_raw": s.due_date_raw,
                "due_date_iso": s.due_date_iso,
                "amount": str(s.amount),
            }
            for s in raw.scadenze
        ],
        ensure_ascii=False,
    )

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
            "field_key": "supplier_id_catalog",
            "value_type": "integer",
            "raw_value": str(match_result.supplier_id) if match_result.supplier_id else None,
            "normalized_value": str(match_result.supplier_id) if match_result.supplier_id else None,
            "locator_json": None,
            "provenance_json": json.dumps({"source": "catalog_match"}),
        },
        {
            "section_key": "header",
            "field_key": "invoice_number",
            "value_type": "string",
            "raw_value": raw.invoice_number,
            "normalized_value": raw.invoice_number,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "invoice_date",
            "value_type": "date",
            "raw_value": raw.invoice_date_iso,
            "normalized_value": raw.invoice_date_iso,
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
            "field_key": "ddt_ref",
            "value_type": "string",
            "raw_value": raw.ddt_ref,
            "normalized_value": raw.ddt_ref,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_document",
            "value_type": "decimal",
            "raw_value": str(raw.total_document) if raw.total_document is not None else None,
            "normalized_value": str(raw.total_document) if raw.total_document is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_taxable",
            "value_type": "decimal",
            "raw_value": str(raw.total_taxable) if raw.total_taxable is not None else None,
            "normalized_value": str(raw.total_taxable) if raw.total_taxable is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_exempt",
            "value_type": "decimal",
            "raw_value": str(raw.total_exempt) if raw.total_exempt is not None else None,
            "normalized_value": str(raw.total_exempt) if raw.total_exempt is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "payment",
            "field_key": "payment_terms_text",
            "value_type": "string",
            "raw_value": raw.payment_terms_text,
            "normalized_value": raw.payment_terms_text,
            "locator_json": _locator(),
        },
        {
            "section_key": "payment",
            "field_key": "destination_iban",
            "value_type": "string",
            "raw_value": raw.destination_iban,
            "normalized_value": raw.destination_iban,
            "locator_json": _locator(),
        },
        {
            "section_key": "payment",
            "field_key": "destination_bank",
            "value_type": "string",
            "raw_value": raw.destination_bank,
            "normalized_value": raw.destination_bank,
            "locator_json": _locator(),
        },
        {
            "section_key": "payment",
            "field_key": "scadenze_json",
            "value_type": "json",
            "raw_value": scadenze_json,
            "normalized_value": scadenze_json,
            "locator_json": _locator(),
        },
    ]

    rows = []
    for line in raw.lines:
        matched_product_id = match_result.line_matches.get(line.sku)
        cells = {
            "sku": {"raw": line.sku, "normalized": line.sku},
            "description": {"raw": line.description, "normalized": line.description},
            "unit": {"raw": line.unit, "normalized": line.unit},
            "quantity": {"raw": str(line.quantity), "normalized": str(line.quantity)},
            "unit_price": {"raw": str(line.unit_price), "normalized": str(line.unit_price)},
            "line_total": {"raw": str(line.line_total), "normalized": str(line.line_total)},
            "iva_code": {"raw": line.iva_code, "normalized": line.iva_code},
            "product_id_catalog": {
                "raw": str(matched_product_id) if matched_product_id else None,
                "normalized": str(matched_product_id) if matched_product_id else None,
            },
        }
        rows.append(
            {
                "section_key": "lines",
                "row_index": line.row_index,
                "row_key": line.sku,
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
