"""Adapter ordine_heroes_v1 — extrator de Ordine de Compra da Heroe's Srl.

Corpus: Ordine_589 (corpus_589/Ordine_589.pdf).
Estratégia:
- pypdf layout mode → cabeçalho (normaliza espaços entre caracteres fonte)
- pypdf default mode → tabela de linhas (colunas em linhas separadas)
- parse_it para números e datas italianos

Separação de responsabilidades:
- extract(bytes) → AdapterRawResult — puro, sem DB
- match_catalog(db, raw) → enrich issues para SKUs ambíguos/não encontrados
- run_adapter(db, occurrence_id, actor_id, quarantine_path) → seeds IngestionDocument

Regra: I.V. 1 / I.V. 2 NUNCA viram SKU canônico silenciosamente →
       emite issue AMBIGUOUS_SKU e exige revisão de matching.
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

ADAPTER_ID = "ordine_heroes_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "ORDINE_COMPRA"


def _compact(s: str) -> str:
    """Remove espaços múltiplos internos (artefato de font encoding PDF)."""
    return re.sub(r"\s+", " ", s).strip()


def _unsqueeze_pdf_glyphs(text: str) -> str:
    """Collapse glyph-spaced Heroes layout text (descriptions only).

    Example: 'ra c c hette 2027 GR AFIC AT E' → 'racchette 2027 GRAFICATE'.
    Do NOT use on SKU, EAN, NCM, dates, amounts, or units.
    """
    if not text or not str(text).strip():
        return text
    tokens = str(text).split()
    out: list[str] = []
    letter_buf: list[str] = []

    def flush() -> None:
        if letter_buf:
            out.append("".join(letter_buf))
            letter_buf.clear()

    for tok in tokens:
        if re.fullmatch(r"[A-Za-zÀ-ÿ]+", tok):
            letter_buf.append(tok)
        else:
            flush()
            out.append(tok)
    flush()
    result = " ".join(out)
    result = re.sub(r"(?i)\bNONGRAFICATE\b", "NON GRAFICATE", result)
    result = re.sub(r"(?i)\b(racchette)(\d{4})\b", r"\1 \2", result)
    return re.sub(r"\s+", " ", result).strip()


def _strip_currency(s: str) -> str:
    return re.sub(r"[€\s]", "", s).strip()


_MATH_TOL = Decimal("0.02")
_EXPORT_IVA_CODES = frozenset({"N3.1", "N31", "N3.1."})


def _validate_math_heroes_pdf(
    *,
    lines: list,
    total_document: Decimal | None,
    total_taxable: Decimal | None,
    total_exempt: Decimal | None,
    total_taxes: Decimal | None,
    total_discounts: Decimal | None,
    shipping_spese: Decimal | None = None,
) -> list[dict]:
    """L2 + L4 + L5 + total_document guardado + INFO N3.1 (±0.02 EUR).

    L5: qty × unit_price ≈ line_total
    L2: Σ line_total ≈ total_taxable + total_exempt (when bases present)
    L4: MATH_LINE_VAT_NATURE when line IVA contradicts taxable/exempt bases
    total_document: se IMPOSTE=SCONTI=Spese = 0/ausentes → total ≈ taxable+exempt;
      senão INFO composição não verificável (sem L3/SCONTI completo).
    """
    issues: list[dict] = []
    if not lines:
        return issues

    computed_total = sum((getattr(line, "line_total") for line in lines), Decimal("0"))
    taxable = total_taxable if total_taxable is not None else Decimal("0")
    exempt = total_exempt if total_exempt is not None else Decimal("0")
    taxes = total_taxes if total_taxes is not None else Decimal("0")
    discounts = total_discounts if total_discounts is not None else Decimal("0")
    shipping = shipping_spese if shipping_spese is not None else Decimal("0")

    for line in lines:
        qty = getattr(line, "quantity")
        price = getattr(line, "unit_price")
        line_total = getattr(line, "line_total")
        sc_pct = getattr(line, "discount_pct", None)
        if sc_pct is not None:
            try:
                sc = Decimal(str(sc_pct))
                expected = (qty * price * (Decimal("1") - sc / Decimal("100"))).quantize(Decimal("0.01"))
            except Exception:
                expected = (qty * price).quantize(Decimal("0.01"))
        else:
            expected = (qty * price).quantize(Decimal("0.01"))
        if abs(expected - line_total) > _MATH_TOL:
            issues.append(
                {
                    "severity": "ERROR",
                    "code": "MATH_LINE_TOTAL_MISMATCH",
                    "message": (
                        f"SKU {getattr(line, 'sku')}: {qty} × {price} "
                        f"= {expected} mas total declarado é {line_total}"
                    ),
                    "target_type": "ROW",
                    "target_id": getattr(line, "row_index"),
                    "entity_type": "PRODUCT",
                }
            )

        iva = (getattr(line, "iva_code", None) or "").strip()
        iva_norm = iva.upper().replace(" ", "")
        export_norms = {c.upper().replace(" ", "") for c in _EXPORT_IVA_CODES}
        # L4: bases 100% esenti — linha com IVA não-exportação é inconsistente
        if taxable == 0 and exempt > 0 and iva_norm and iva_norm not in export_norms:
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "MATH_LINE_VAT_NATURE",
                    "message": (
                        f"SKU {getattr(line, 'sku')}: código IVA '{iva}' inconsistente "
                        f"com documento 100% esenti (imponibile=0)."
                    ),
                    "target_type": "ROW",
                    "target_id": getattr(line, "row_index"),
                    "entity_type": "PRODUCT",
                }
            )

    if total_taxable is not None or total_exempt is not None:
        bases = taxable + exempt
        if abs(computed_total - bases) > _MATH_TOL:
            issues.append(
                {
                    "severity": "ERROR",
                    "code": "MATH_LINES_VS_TAX_BASES",
                    "message": (
                        f"Soma das linhas ({computed_total}) difere de "
                        f"imponibile+esenti ({bases})"
                    ),
                    "target_type": "DOCUMENT",
                    "entity_type": "DOCUMENT",
                }
            )

    # Guarded total_document (not full L3): only when taxes/discounts/shipping are 0/absent
    composition_clear = taxes == 0 and discounts == 0 and shipping == 0
    if total_document is not None:
        if composition_clear and (total_taxable is not None or total_exempt is not None):
            expected_doc = taxable + exempt
            if abs(total_document - expected_doc) > _MATH_TOL:
                issues.append(
                    {
                        "severity": "ERROR",
                        "code": "MATH_TOTAL_MISMATCH",
                        "message": (
                            f"Total documento ({total_document}) difere de "
                            f"imponibile+esenti ({expected_doc}) com IMPOSTE/SCONTI/Spese=0"
                        ),
                        "target_type": "DOCUMENT",
                        "entity_type": "DOCUMENT",
                    }
                )
        elif not composition_clear:
            issues.append(
                {
                    "severity": "INFO",
                    "code": "MATH_TOTAL_COMPOSITION_UNVERIFIED",
                    "message": (
                        "Composição do total não verificável nesta versão "
                        "(IMPOSTE/SCONTI/Spese ≠ 0)."
                    ),
                    "target_type": "DOCUMENT",
                    "entity_type": "DOCUMENT",
                }
            )

    # Export N3.1 info — never silences L2/L5 failures
    all_n31 = bool(lines) and all(
        (getattr(ln, "iva_code", None) or "").strip().upper().replace(" ", "")
        in {c.upper().replace(" ", "") for c in _EXPORT_IVA_CODES}
        for ln in lines
    )
    if (
        all_n31
        and taxable == 0
        and exempt > 0
        and taxes == 0
        and discounts == 0
        and shipping == 0
    ):
        issues.append(
            {
                "severity": "INFO",
                "code": "MATH_EXPORT_N31",
                "message": "Regime exportação N3.1 (IVA 0%): imponibile=0 e esenti=Σ linhas é esperado.",
                "target_type": "DOCUMENT",
                "entity_type": "DOCUMENT",
            }
        )

    return issues


def _spaced(keyword: str) -> str:
    """Converte texto para regex tolerante a espaços entre caracteres (artefato de PDF).
    Exemplo: 'TOTALE' → 'T\\s*O\\s*T\\s*A\\s*L\\s*E'
    """
    return r"\s*".join(re.escape(c) for c in keyword)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


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
    order_number: str | None
    order_date_iso: str | None
    order_date_needs_review: bool
    currency: str
    total_document: Decimal | None
    total_taxable: Decimal | None
    total_exempt: Decimal | None
    total_taxes: Decimal | None
    total_discounts: Decimal | None
    shipping_spese: Decimal | None = None
    lines: list[RawLineItem] = field(default_factory=list)
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Header extraction from layout-mode text
# ---------------------------------------------------------------------------

def _extract_header(layout_text: str) -> dict:
    """Extrai campos do cabeçalho usando o texto em modo layout (com espaços no font)."""
    compact = _compact(layout_text)

    result: dict = {}

    # Supplier name: "Her oe's Sr l" — tolerante a espaços entre chars
    m = re.search(r"(Her\s*oe['\u2019\s']*s\s+Sr\s*l)", compact, re.IGNORECASE)
    if m:
        result["supplier_name"] = "Heroe's Srl"

    # PI/CF — match "PI / C F: 02610500395" or "PI / CF: 02610500395"
    m = re.search(
        r"PI\s*/\s*C\s*F\s*:\s*([\d\s]+)\s*-\s*[\d\s]+",
        compact, re.IGNORECASE
    )
    if m:
        pi_raw = re.sub(r"\s+", "", m.group(1))
        if len(pi_raw) >= 11:
            result["supplier_pi_cf"] = pi_raw[:11]

    # Order number: "Numero: 589" (may have spaces)
    m = re.search(r"N\s*u\s*m\s*e\s*r\s*o\s*:\s*(\d+)", compact, re.IGNORECASE)
    if m:
        result["order_number"] = m.group(1).strip()

    # Date: "D el : 04/06/2026" — tolerant to spaces
    m = re.search(r"D\s*e\s*l\s*:\s*(\d{1,2}/\d{2}/\d{4})", compact, re.IGNORECASE)
    if m:
        result["order_date_raw"] = m.group(1)

    # Totals — fully space-tolerant using _spaced helper
    _td = _spaced("TOTALE") + r"\s+" + _spaced("DOCUMENTO") + r"\s*:\s*[€\s]*([\d.,]+)"
    m = re.search(_td, compact, re.IGNORECASE)
    if m:
        result["total_document"] = _strip_currency(m.group(1))

    _ti = _spaced("Totale") + r"\s+" + _spaced("imponibile") + r"\s*:\s*[€\s]*([\d.,]+)"
    m = re.search(_ti, compact, re.IGNORECASE)
    if m:
        result["total_taxable"] = _strip_currency(m.group(1))

    _te = _spaced("Totale") + r"\s+" + _spaced("esenti") + r"\s+" + _spaced("iva") + r"\s*:\s*[€\s]*([\d.,]+)"
    m = re.search(_te, compact, re.IGNORECASE)
    if m:
        result["total_exempt"] = _strip_currency(m.group(1))

    _imp = _spaced("IMPOSTE") + r"\s*:\s*[€\s]*([\d.,]+)"
    m = re.search(_imp, compact, re.IGNORECASE)
    if m:
        result["total_taxes"] = _strip_currency(m.group(1))

    _sc = _spaced("SCONTI") + r"\s*:\s*[€\s]*([\d.,]+)"
    m = re.search(_sc, compact, re.IGNORECASE)
    if m:
        result["total_discounts"] = _strip_currency(m.group(1))

    _sp = (
        _spaced("Spese")
        + r"\s+"
        + _spaced("di")
        + r"\s+"
        + _spaced("spedizione")
        + r"\s*:\s*[€\s]*([\d.,]+)"
    )
    m = re.search(_sp, compact, re.IGNORECASE)
    if m:
        result["shipping_spese"] = _strip_currency(m.group(1))

    return result


# ---------------------------------------------------------------------------
# Line items extraction from layout-mode text
# ---------------------------------------------------------------------------

_RE_LINE_LAYOUT = re.compile(
    r"(I\.\s*V\.\s*\d+)"           # sku "I.V. 1" or "I.V. 2" (group 1)
    r"\s+"
    r"(ra\s*c\s*c\s*hette\s+\d{4}\s+(?:NO\s*N\s+)?GR\s*AFIC\s*AT\s*E)"  # description (group 2)
    r"\s+(PZ|KG|MT|LT|CF)\s+"      # unit (group 3)
    r"(\d[\d.,]*)\s+"              # qty (group 4)
    r"[€]\s*([\d.,]+)\s+"          # unit_price (group 5)
    r"[€]\s*([\d.,]+)\s+"          # line_total (group 6)
    r"([A-Z0-9.]+)",               # iva_code (group 7)
    re.IGNORECASE,
)

# Fallback: column-per-line parsing from default mode
_RE_SKU = re.compile(r"^I\.V\.\s*\d+$")
_RE_UNIT = re.compile(r"^(PZ|KG|MT|LT|CF)$", re.IGNORECASE)
_RE_PRICE = re.compile(r"^[€\s]*[\d.,]+$")
_RE_IVA = re.compile(r"^[A-Z]\d+\.\d+$")


def _parse_lines_from_layout(layout_text: str) -> list[RawLineItem]:
    """Parse lines from layout mode text where each line contains all columns."""
    lines: list[RawLineItem] = []
    for idx, m in enumerate(_RE_LINE_LAYOUT.finditer(layout_text)):
        sku = _compact(m.group(1))
        sku = re.sub(r"\s+", " ", sku).strip()  # normalize "I.V.  2" → "I.V. 2"
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


def _parse_lines_from_default(default_text: str) -> list[RawLineItem]:
    """Fallback: parse from default text where each column is on its own line.

    Pattern for each record:
      I.V. 2
      racchette 2027 GRAFICATE
      PZ
      14600
      € 50,00
      € 730.000,00
      N3.1
    """
    lines_out: list[RawLineItem] = []
    text_lines = [l.strip() for l in default_text.splitlines()]

    i = 0
    row_idx = 0
    while i < len(text_lines):
        line = text_lines[i]
        if _RE_SKU.match(line):
            # Try to extract next 6 values
            if i + 6 < len(text_lines):
                sku = line.strip()
                description = text_lines[i + 1].strip()
                unit_raw = text_lines[i + 2].strip()
                qty_raw = text_lines[i + 3].strip()
                price_raw = text_lines[i + 4].strip()
                total_raw = text_lines[i + 5].strip()
                iva_raw = text_lines[i + 6].strip()

                if _RE_UNIT.match(unit_raw):
                    qty = parse_it_number(qty_raw) or Decimal("0")
                    unit_price = parse_it_number(_strip_currency(price_raw)) or Decimal("0")
                    line_total = parse_it_number(_strip_currency(total_raw)) or Decimal("0")
                    lines_out.append(
                        RawLineItem(
                            sku=sku,
                            description=description,
                            unit=unit_raw.upper(),
                            quantity=qty,
                            unit_price=unit_price,
                            line_total=line_total,
                            iva_code=iva_raw,
                            row_index=row_idx,
                        )
                    )
                    row_idx += 1
                    i += 7
                    continue
        i += 1
    return lines_out


# ---------------------------------------------------------------------------
# Main extract function
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    """Extração pura do PDF — sem DB. Retorna campos + linhas brutos."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))

    layout_pages: list[str] = []
    default_pages: list[str] = []
    for page in reader.pages:
        layout_pages.append(page.extract_text(extraction_mode="layout") or "")
        default_pages.append(page.extract_text() or "")

    layout_text = "\n".join(layout_pages)
    default_text = "\n".join(default_pages)

    # --- header ---
    header = _extract_header(layout_text)

    order_date_iso: str | None = None
    order_date_needs_review = False
    if header.get("order_date_raw"):
        order_date_iso, order_date_needs_review = parse_it_date(header["order_date_raw"])

    total_document = parse_it_number(header.get("total_document"))
    total_taxable = parse_it_number(header.get("total_taxable"))
    total_exempt = parse_it_number(header.get("total_exempt"))
    total_taxes = parse_it_number(header.get("total_taxes"))
    total_discounts = parse_it_number(header.get("total_discounts"))
    shipping_spese = parse_it_number(header.get("shipping_spese"))

    # --- lines: try layout first, fallback to default ---
    lines = _parse_lines_from_layout(layout_text)
    if not lines:
        lines = _parse_lines_from_default(default_text)

    return AdapterRawResult(
        supplier_name=header.get("supplier_name"),
        supplier_pi_cf=header.get("supplier_pi_cf"),
        order_number=header.get("order_number"),
        order_date_iso=order_date_iso,
        order_date_needs_review=order_date_needs_review,
        currency="EUR",
        total_document=total_document,
        total_taxable=total_taxable,
        total_exempt=total_exempt,
        total_taxes=total_taxes,
        total_discounts=total_discounts,
        shipping_spese=shipping_spese,
        lines=lines,
        raw_text=layout_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    """True se o documento parece ser um Ordine da Heroe's Srl."""
    if raw.supplier_name and "heroe" in raw.supplier_name.lower():
        return True
    if raw.order_number and raw.supplier_pi_cf:
        return True
    return False


# ---------------------------------------------------------------------------
# Mathematical validation → issues
# ---------------------------------------------------------------------------


def _validate_math(raw: AdapterRawResult) -> list[dict]:
    return _validate_math_heroes_pdf(
        lines=raw.lines,
        total_document=raw.total_document,
        total_taxable=raw.total_taxable,
        total_exempt=raw.total_exempt,
        total_taxes=raw.total_taxes,
        total_discounts=raw.total_discounts,
        shipping_spese=raw.shipping_spese,
    )


# ---------------------------------------------------------------------------
# Catalog matching (requires DB)
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    supplier_id: int | None
    supplier_found: bool
    line_matches: dict[str, int | None]
    ambiguous_skus: set[str]


def match_catalog(db: Session, raw: AdapterRawResult) -> tuple[MatchResult, list[dict]]:
    """Resolve Supplier e Products via Catalog public API (schema 019).

    Q3=(B): códigos I.V.* / classe fornecedor NÃO resolvem Product automaticamente —
    emitem UNMATCHED_SKU até vínculo humano. EAN / SKU EPIC: match por Product.sku.
    """
    issues: list[dict] = []

    # --- supplier ---
    supplier_id: int | None = None
    supplier_found = False

    if raw.supplier_pi_cf:
        digits = "".join(c for c in raw.supplier_pi_cf if c.isdigit())
        if digits:
            results = catalog_public.list_suppliers(db, q=digits, limit=5)
            if len(results) == 1:
                supplier_id = results[0].id
                supplier_found = True

    search_terms: list[str] = []
    if not supplier_found:
        if raw.supplier_name:
            search_terms.append(raw.supplier_name)
        search_terms.append("Heroe")

    for term in search_terms:
        results = catalog_public.list_suppliers(db, q=term, limit=5)
        if len(results) == 1:
            supplier_id = results[0].id
            supplier_found = True
            break
        elif len(results) > 1:
            # Preferência por nome exato (evita AMBIGUOUS com Heroes SPA / Heroes-*)
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
                        f"{[s.id for s in results]}. Selecione manualmente."
                    ),
                    "target_type": "DOCUMENT",
                    "entity_type": "SUPPLIER",
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
                    "no catálogo. Necessário criar ou vincular manualmente."
                ),
                "target_type": "DOCUMENT",
                "entity_type": "SUPPLIER",
            }
        )

    # --- products ---
    line_matches: dict[str, int | None] = {}
    ambiguous_skus: set[str] = set()

    def _is_supplier_class(code: str) -> bool:
        u = code.strip().upper()
        return u.startswith("I.V") or u.startswith("IV.") or u.startswith("IV ")

    for line in raw.lines:
        sku = line.sku
        product_id: int | None = None

        # Q3=(B): I.V.* = compromisso posicional — nunca auto-match Product
        if _is_supplier_class(sku):
            ambiguous_skus.add(sku)
            issues.append(
                {
                    "severity": "INFO",
                    "code": "UNMATCHED_SKU",
                    "message": (
                        f"Código de classe '{sku}' — linha de compromisso; "
                        "produtos reais virão pela fatura."
                    ),
                    "target_type": "ROW",
                    "target_id": line.row_index,
                    "entity_type": "PRODUCT",
                }
            )
            line_matches[sku] = None
            continue

        from app.catalog.public import CatalogError

        try:
            product = catalog_public.get_product_by_sku(db, sku)
            product_id = product.id
        except CatalogError:
            product_id = None

        if product_id is None:
            results = catalog_public.list_products(db, q=sku, limit=5)
            if len(results) == 1:
                product_id = results[0].id
            elif len(results) > 1:
                ambiguous_skus.add(sku)
                issues.append(
                    {
                        "severity": "WARNING",
                        "code": "AMBIGUOUS_SKU",
                        "message": (
                            f"SKU '{sku}' ambíguo: {len(results)} produtos no catálogo. "
                            "Requer revisão de matching antes do commit."
                        ),
                        "target_type": "ROW",
                        "target_id": line.row_index,
                        "entity_type": "PRODUCT",
                    }
                )
                line_matches[sku] = None
                continue

        if product_id is None:
            ambiguous_skus.add(sku)
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "UNMATCHED_SKU",
                    "message": (
                        f"Código externo '{sku}' sem produto vinculado. "
                        "Vincule um produto existente antes do commit."
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
# Full adapter run (DB-aware): extract + validate + match + seed IR
# ---------------------------------------------------------------------------


def build_ir_payload(
    db: Session,
    *,
    occurrence_id: int,
    quarantine_path: Path,
) -> dict:
    """Extrai Ordine do blob, valida, corresponde catálogo — payload para seed ou replace."""
    from app.ingestion.errors import IngestionError as IE

    occ = db.get(IngestionOccurrence, occurrence_id)
    if occ is None:
        from app.ingestion.errors import OccurrenceNotFound
        raise OccurrenceNotFound(occurrence_id)

    if occ.blob is None or occ.blob.physical_status != "PRESENT" or not occ.blob.storage_path:
        raise IE(
            f"Blob da occurrence {occurrence_id} indisponível",
            code="blob_unavailable",
        )

    path = quarantine_storage.resolve_quarantine_path(quarantine_path, occ.blob.storage_path)
    if path is None or not path.is_file():
        raise IE(
            f"Arquivo físico não encontrado para occurrence {occurrence_id}",
            code="blob_unavailable",
        )

    pdf_bytes = path.read_bytes()
    raw = extract(pdf_bytes)
    issues = _validate_math(raw)
    match_result, match_issues = match_catalog(db, raw)
    issues.extend(match_issues)

    sections = [
        {"section_key": "header", "title": "Cabeçalho do Ordine", "ordinal": 0},
        {"section_key": "lines", "title": "Linhas do Ordine", "ordinal": 1},
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
            "field_key": "supplier_id_catalog",
            "value_type": "integer",
            "raw_value": str(match_result.supplier_id) if match_result.supplier_id else None,
            "normalized_value": str(match_result.supplier_id) if match_result.supplier_id else None,
            "locator_json": None,
            "provenance_json": json.dumps({"source": "catalog_match"}),
        },
        {
            "section_key": "header",
            "field_key": "order_number",
            "value_type": "string",
            "raw_value": raw.order_number,
            "normalized_value": raw.order_number,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "order_date",
            "value_type": "date",
            "raw_value": raw.order_date_iso,
            "normalized_value": raw.order_date_iso,
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
            "section_key": "header",
            "field_key": "total_taxes",
            "value_type": "decimal",
            "raw_value": str(raw.total_taxes) if raw.total_taxes is not None else None,
            "normalized_value": str(raw.total_taxes) if raw.total_taxes is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "total_discounts",
            "value_type": "decimal",
            "raw_value": str(raw.total_discounts) if raw.total_discounts is not None else None,
            "normalized_value": str(raw.total_discounts) if raw.total_discounts is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "shipping_spese",
            "value_type": "decimal",
            "raw_value": str(raw.shipping_spese) if raw.shipping_spese is not None else None,
            "normalized_value": str(raw.shipping_spese) if raw.shipping_spese is not None else None,
            "locator_json": _locator(),
        },
        {
            "section_key": "header",
            "field_key": "pending_create_supplier",
            "value_type": "json",
            "raw_value": None,
            "normalized_value": None,
            "locator_json": None,
        },
    ]

    rows = []
    for line in raw.lines:
        matched_product_id = match_result.line_matches.get(line.sku)
        desc_norm = _unsqueeze_pdf_glyphs(line.description)
        cells = {
            "sku": {"raw": line.sku, "normalized": line.sku},
            "description": {"raw": line.description, "normalized": desc_norm},
            "unit": {"raw": line.unit, "normalized": line.unit},
            "quantity": {"raw": str(line.quantity), "normalized": str(line.quantity)},
            "unit_price": {"raw": str(line.unit_price), "normalized": str(line.unit_price)},
            "line_total": {"raw": str(line.line_total), "normalized": str(line.line_total)},
            "iva_code": {"raw": line.iva_code, "normalized": line.iva_code},
            "product_id_catalog": {
                "raw": str(matched_product_id) if matched_product_id else None,
                "normalized": str(matched_product_id) if matched_product_id else None,
            },
            # Q3=(B): sem pending_create_product — I.V.* é compromisso, não produto.
        }
        rows.append(
            {
                "section_key": "lines",
                "row_index": line.row_index,
                "row_key": line.sku,
                "cells_json": json.dumps(cells, ensure_ascii=False),
            }
        )

    return {
        "doc_type": DOC_TYPE,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "sections": sections,
        "fields": fields,
        "rows": rows,
        "issues": issues,
    }


def run_adapter(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str,
    quarantine_path: Path,
) -> "IngestionDocument":  # noqa: F821
    """Extrai Ordine do blob, valida, corresponde catálogo, semeia IR."""
    payload = build_ir_payload(
        db,
        occurrence_id=occurrence_id,
        quarantine_path=quarantine_path,
    )
    return staging_commands.seed_document_from_occurrence(
        db,
        occurrence_id=occurrence_id,
        actor_id=actor_id,
        doc_type=payload["doc_type"],
        adapter_id=payload["adapter_id"],
        adapter_version=payload["adapter_version"],
        sections=payload["sections"],
        fields=payload["fields"],
        rows=payload["rows"],
        issues=payload["issues"],
    )
