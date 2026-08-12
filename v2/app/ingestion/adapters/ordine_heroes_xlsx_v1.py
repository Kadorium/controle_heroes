"""Adapter ordine_heroes_xlsx_v1 — extrator de Ordine XLSX da Heroe's Srl.

Corpus: ordine758.xlsx, ordine759.xlsx (tests/fixtures/ingestion/xlsx/).

Estrutura do XLSX:
- Planilha "Ordine NNN":
  - Linha 1: "versato" + valor pago total
  - Linha 2: "ordine NNN" (número do pedido)
  - Linhas 4+: tabela de rastreamento de faturas (data, n* fattura, qtd, produto, acconto...)
  - Seção "DA SPEDIRE": itens a enviar (racchetta, qtd, preço lista, preço fatura, sconto)

Provenance: locator JSON com sheet, row, col para cada célula lida.
Fórmulas: preservadas SEM execução (data_only=False). Células com fórmula
registram is_formula=true no locator e formula string como raw_value.

Separação de responsabilidades:
- extract(bytes) → AdapterRawResult — puro, sem DB
- classify(raw) → bool
- run_adapter(db, ...) → IngestionDocument
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.ingestion import staging_commands
from app.ingestion import storage as quarantine_storage
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence

ADAPTER_ID = "ordine_heroes_xlsx_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "ORDINE_COMPRA_XLSX"

_ORDER_RE = re.compile(r"ordine\s+(\d+)", re.IGNORECASE)
_VERSATO_RE = re.compile(r"versato", re.IGNORECASE)
_DA_SPEDIRE_RE = re.compile(r"da\s+spedire", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Provenance locator
# ---------------------------------------------------------------------------


def _locator(sheet: str, row: int, col: int, is_formula: bool = False) -> str:
    d: dict[str, Any] = {"sheet": sheet, "row": row, "col": col, "source": "openpyxl"}
    if is_formula:
        d["is_formula"] = True
    return json.dumps(d, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CellValue:
    """A cell value with its provenance."""

    value: Any
    raw_str: str | None
    is_formula: bool
    sheet: str
    row: int
    col: int

    @property
    def locator(self) -> str:
        return _locator(self.sheet, self.row, self.col, self.is_formula)

    @property
    def normalized_str(self) -> str | None:
        if self.is_formula:
            return None
        if self.value is None:
            return None
        if isinstance(self.value, (datetime, date)):
            return self.value.strftime("%Y-%m-%d")
        return str(self.value)


@dataclass
class XlsxShipItem:
    """Item da seção 'DA SPEDIRE' — produto a enviar com preços."""

    row_index: int
    sku_raw: str | None
    quantity: Decimal | None
    list_price: Decimal | None
    invoice_price: Decimal | None
    discount: Decimal | None
    sku_cell: CellValue | None = None
    qty_cell: CellValue | None = None
    list_price_cell: CellValue | None = None
    invoice_price_cell: CellValue | None = None
    discount_cell: CellValue | None = None


@dataclass
class XlsxInvoiceRecord:
    """Linha da tabela de rastreamento de faturas."""

    row_index: int
    date_raw: str | None
    invoice_ref: str | None
    quantity: int | None
    product_name: str | None
    acconto: Decimal | None
    acconto_rimasto: Decimal | None
    credito_per_racchetta: Decimal | None
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass
class AdapterRawResult:
    order_number: str | None
    order_number_cell: CellValue | None
    versato: Decimal | None
    versato_cell: CellValue | None
    sheet_name: str
    all_sheets: list[str]
    ship_items: list[XlsxShipItem] = field(default_factory=list)
    invoice_records: list[XlsxInvoiceRecord] = field(default_factory=list)
    formula_cells: list[CellValue] = field(default_factory=list)
    currency: str = "EUR"
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_decimal(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _read_cell(ws, row: int, col: int, sheet_name: str) -> CellValue:
    cell = ws.cell(row=row, column=col)
    raw = cell.value
    is_formula = isinstance(raw, str) and raw.startswith("=")
    raw_str = str(raw) if raw is not None else None
    return CellValue(
        value=raw,
        raw_str=raw_str,
        is_formula=is_formula,
        sheet=sheet_name,
        row=row,
        col=col,
    )


def _row_values(ws, row: int, max_col: int, sheet_name: str) -> list[CellValue]:
    return [_read_cell(ws, row, col, sheet_name) for col in range(1, max_col + 1)]


def _is_blank_row(cells: list[CellValue]) -> bool:
    return all(c.value is None for c in cells)


def _str_lower(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip().lower()


# ---------------------------------------------------------------------------
# Main sheet parsing
# ---------------------------------------------------------------------------


def _parse_sheet(ws, sheet_name: str) -> tuple[
    str | None,
    CellValue | None,
    Decimal | None,
    CellValue | None,
    list[XlsxInvoiceRecord],
    list[XlsxShipItem],
    list[CellValue],
]:
    max_row = ws.max_row
    max_col = max(ws.max_column, 7)

    order_number: str | None = None
    order_number_cell: CellValue | None = None
    versato: Decimal | None = None
    versato_cell: CellValue | None = None
    formula_cells: list[CellValue] = []
    invoice_records: list[XlsxInvoiceRecord] = []
    ship_items: list[XlsxShipItem] = []

    da_spedire_row: int | None = None
    invoice_header_row: int | None = None

    # First pass: find markers and collect formula cells
    for r in range(1, max_row + 1):
        cells = _row_values(ws, r, max_col, sheet_name)
        for c in cells:
            if c.is_formula:
                formula_cells.append(c)

        if r <= 5:
            for c in cells:
                if c.value is None:
                    continue
                s = _str_lower(c.value)
                if _VERSATO_RE.search(s):
                    # next cell is the versato amount
                    for nc in cells[cells.index(c) + 1:]:
                        if nc.value is not None:
                            versato = _to_decimal(nc.value)
                            versato_cell = nc
                            break
                m = _ORDER_RE.search(s)
                if m:
                    order_number = m.group(1)
                    order_number_cell = c

        # Detect DA SPEDIRE section marker
        for c in cells:
            if c.value is not None and _DA_SPEDIRE_RE.search(_str_lower(c.value)):
                da_spedire_row = r

        # Detect invoice header row: contains "data" and "n* fattura" or "quantit"
        if invoice_header_row is None:
            texts = [_str_lower(c.value) for c in cells if c.value is not None]
            if "data" in texts and any("fattura" in t for t in texts):
                invoice_header_row = r

    # Parse invoice records table (between header and DA SPEDIRE or end)
    if invoice_header_row:
        end_of_invoices = (da_spedire_row - 1) if da_spedire_row else max_row
        for r in range(invoice_header_row + 1, end_of_invoices + 1):
            cells = _row_values(ws, r, max_col, sheet_name)
            if _is_blank_row(cells):
                continue
            if da_spedire_row and r >= da_spedire_row:
                break

            c_date = cells[0]
            c_inv = cells[1] if len(cells) > 1 else None
            c_qty = cells[2] if len(cells) > 2 else None
            c_prod = cells[3] if len(cells) > 3 else None
            c_acc = cells[4] if len(cells) > 4 else None
            c_acc_rim = cells[5] if len(cells) > 5 else None
            c_cred = cells[6] if len(cells) > 6 else None

            date_str: str | None = None
            if c_date and c_date.value is not None:
                if isinstance(c_date.value, (datetime, date)):
                    date_str = c_date.value.strftime("%Y-%m-%d")
                else:
                    date_str = str(c_date.value)
            elif not c_date or c_date.value is None:
                date_str = None

            qty_val: int | None = None
            if c_qty and c_qty.value is not None and not c_qty.is_formula:
                try:
                    qty_val = int(c_qty.value)
                except (ValueError, TypeError):
                    pass

            prov: dict[str, str] = {}
            if c_date and c_date.value is not None:
                prov["date"] = c_date.locator
            if c_inv and c_inv.value is not None:
                prov["invoice_ref"] = c_inv.locator
            if c_qty and c_qty.value is not None:
                prov["quantity"] = c_qty.locator
            if c_prod and c_prod.value is not None:
                prov["product"] = c_prod.locator

            rec = XlsxInvoiceRecord(
                row_index=r,
                date_raw=date_str,
                invoice_ref=str(c_inv.value) if c_inv and c_inv.value else None,
                quantity=qty_val,
                product_name=str(c_prod.value) if c_prod and c_prod.value else None,
                acconto=_to_decimal(c_acc.value) if c_acc else None,
                acconto_rimasto=_to_decimal(c_acc_rim.value) if c_acc_rim else None,
                credito_per_racchetta=_to_decimal(c_cred.value) if c_cred else None,
                provenance=prov,
            )
            invoice_records.append(rec)

    # Parse DA SPEDIRE section
    if da_spedire_row:
        # find sub-header: racchetta, quantità, prezzo listino, prezzo fattura, sconto
        sub_header_row: int | None = None
        for r in range(da_spedire_row + 1, min(da_spedire_row + 4, max_row + 1)):
            cells = _row_values(ws, r, max_col, sheet_name)
            texts = [_str_lower(c.value) for c in cells if c.value is not None]
            if any("racch" in t or "articol" in t for t in texts):
                sub_header_row = r
                break

        start_items = (sub_header_row + 1) if sub_header_row else (da_spedire_row + 1)
        item_idx = 0
        for r in range(start_items, max_row + 1):
            cells = _row_values(ws, r, max_col, sheet_name)
            if _is_blank_row(cells):
                continue

            c_sku = cells[0]
            c_qty = cells[1] if len(cells) > 1 else None
            c_list = cells[2] if len(cells) > 2 else None
            c_inv_p = cells[3] if len(cells) > 3 else None
            c_disc = cells[4] if len(cells) > 4 else None

            sku_raw = str(c_sku.value).strip() if c_sku and c_sku.value is not None else None
            qty = None
            if c_qty and c_qty.value is not None and not c_qty.is_formula:
                qty = _to_decimal(c_qty.value)
            list_price = _to_decimal(c_list.value) if c_list else None
            invoice_price = _to_decimal(c_inv_p.value) if c_inv_p else None
            discount = _to_decimal(c_disc.value) if c_disc else None

            ship_items.append(
                XlsxShipItem(
                    row_index=r,
                    sku_raw=sku_raw,
                    quantity=qty,
                    list_price=list_price,
                    invoice_price=invoice_price,
                    discount=discount,
                    sku_cell=c_sku,
                    qty_cell=c_qty,
                    list_price_cell=c_list,
                    invoice_price_cell=c_inv_p,
                    discount_cell=c_disc,
                )
            )
            item_idx += 1

    return (
        order_number,
        order_number_cell,
        versato,
        versato_cell,
        invoice_records,
        ship_items,
        formula_cells,
    )


# ---------------------------------------------------------------------------
# Main extract function
# ---------------------------------------------------------------------------


def extract(xlsx_bytes: bytes) -> AdapterRawResult:
    """Extração pura do XLSX — sem DB. Preserva fórmulas SEM execução."""
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl required for XLSX ingestion") from exc

    wb = openpyxl.load_workbook(
        io.BytesIO(xlsx_bytes),
        read_only=False,
        keep_vba=False,
        data_only=False,  # preserve formula strings, NOT computed values
    )
    all_sheets = wb.sheetnames

    # Primary sheet: first sheet named "Ordine NNN" or just first sheet
    primary_sheet = wb.active
    if primary_sheet is None and all_sheets:
        primary_sheet = wb[all_sheets[0]]

    sheet_name = primary_sheet.title if primary_sheet is not None else ""

    if primary_sheet is None:
        return AdapterRawResult(
            order_number=None,
            order_number_cell=None,
            versato=None,
            versato_cell=None,
            sheet_name=sheet_name,
            all_sheets=all_sheets,
        )

    (
        order_number,
        order_number_cell,
        versato,
        versato_cell,
        invoice_records,
        ship_items,
        formula_cells,
    ) = _parse_sheet(primary_sheet, sheet_name)

    # Raw text summary for classification
    raw_parts: list[str] = [f"sheet:{sheet_name}"]
    if order_number:
        raw_parts.append(f"ordine:{order_number}")
    for item in ship_items:
        if item.sku_raw:
            raw_parts.append(item.sku_raw)
    raw_text = "|".join(raw_parts)

    return AdapterRawResult(
        order_number=order_number,
        order_number_cell=order_number_cell,
        versato=versato,
        versato_cell=versato_cell,
        sheet_name=sheet_name,
        all_sheets=all_sheets,
        ship_items=ship_items,
        invoice_records=invoice_records,
        formula_cells=formula_cells,
        currency="EUR",
        raw_text=raw_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    """True se o documento parece ser um Ordine da Heroe's Srl em XLSX."""
    if raw.order_number:
        return True
    sheet_lower = raw.sheet_name.lower()
    if "ordine" in sheet_lower:
        return True
    return bool(raw.ship_items or raw.invoice_records)


# ---------------------------------------------------------------------------
# Mathematical validation → issues
# ---------------------------------------------------------------------------


def _validate_items(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []

    for idx, item in enumerate(raw.ship_items):
        if item.sku_raw is None:
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "XLSX_MISSING_SKU",
                    "message": f"Item DA SPEDIRE linha {item.row_index} sem SKU.",
                    "target_type": "ROW",
                    "target_id": idx,
                    "locator_json": item.sku_cell.locator if item.sku_cell else None,
                }
            )

        if item.invoice_price is not None and item.quantity is not None:
            expected_total = (item.quantity * item.invoice_price).quantize(Decimal("0.01"))
        else:
            expected_total = None

        if item.list_price and item.invoice_price and item.discount:
            expected_discount_price = (
                item.list_price * (1 - item.discount / 100)
            ).quantize(Decimal("0.01"))
            if abs(expected_discount_price - item.invoice_price) > Decimal("0.10"):
                issues.append(
                    {
                        "severity": "INFO",
                        "code": "XLSX_DISCOUNT_PRICE_DIVERGENCE",
                        "message": (
                            f"Item '{item.sku_raw}': preço listino {item.list_price} "
                            f"× (1-{item.discount}%) = {expected_discount_price} "
                            f"mas preço fatura é {item.invoice_price}"
                        ),
                        "target_type": "ROW",
                        "target_id": idx,
                    }
                )

    if raw.formula_cells:
        issues.append(
            {
                "severity": "INFO",
                "code": "XLSX_FORMULA_NOT_EXECUTED",
                "message": (
                    f"{len(raw.formula_cells)} célula(s) com fórmula detectada(s). "
                    "Fórmulas preservadas como texto; valores não executados."
                ),
                "target_type": "DOCUMENT",
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Catalog matching (requires DB)
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    supplier_id: int | None
    supplier_found: bool
    sku_matches: dict[str, int | None]
    ambiguous_skus: set[str]


def match_catalog(db: Session, raw: AdapterRawResult) -> tuple[MatchResult, list[dict]]:
    """Resolve Supplier e SKUs via Catalog public API."""
    issues: list[dict] = []

    supplier_id: int | None = None
    supplier_found = False
    for term in ("Heroe", "Heroe's Srl"):
        try:
            results = catalog_public.list_suppliers(db, q=term, limit=5)
        except Exception:
            results = []
        if len(results) == 1:
            supplier_id = results[0].id
            supplier_found = True
            break
        elif len(results) > 1:
            issues.append(
                {
                    "severity": "WARNING",
                    "code": "AMBIGUOUS_SUPPLIER",
                    "message": f"Múltiplos fornecedores para '{term}': {[s.id for s in results]}",
                    "target_type": "DOCUMENT",
                }
            )
            break

    if not supplier_found:
        issues.append(
            {
                "severity": "WARNING",
                "code": "SUPPLIER_NOT_FOUND",
                "message": "Fornecedor Heroe's Srl não encontrado no catálogo.",
                "target_type": "DOCUMENT",
            }
        )

    sku_matches: dict[str, int | None] = {}
    ambiguous_skus: set[str] = set()

    all_skus = [item.sku_raw for item in raw.ship_items if item.sku_raw]
    # Also check invoice records for product names
    all_skus.extend(
        rec.product_name for rec in raw.invoice_records if rec.product_name and rec.product_name not in all_skus
    )

    for sku in all_skus:
        if sku in sku_matches:
            continue
        product_id: int | None = None
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
                        "message": f"SKU '{sku}': {len(results)} produtos no catálogo.",
                        "target_type": "DOCUMENT",
                    }
                )
            else:
                ambiguous_skus.add(sku)
                issues.append(
                    {
                        "severity": "WARNING",
                        "code": "AMBIGUOUS_SKU",
                        "message": f"SKU '{sku}' não encontrado no catálogo.",
                        "target_type": "DOCUMENT",
                    }
                )

        sku_matches[sku] = product_id

    return (
        MatchResult(
            supplier_id=supplier_id,
            supplier_found=supplier_found,
            sku_matches=sku_matches,
            ambiguous_skus=ambiguous_skus,
        ),
        issues,
    )


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
    """Extrai Ordine XLSX, valida, corresponde catálogo, semeia IR + registra métrica."""
    from app.ingestion.metrics_commands import record_adapter_run, record_matching_result

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

    xlsx_bytes = path.read_bytes()
    raw = extract(xlsx_bytes)
    issues = _validate_items(raw)
    match_result, match_issues = match_catalog(db, raw)
    issues.extend(match_issues)

    classified = classify(raw)

    sections = [
        {"section_key": "header", "title": "Cabeçalho do Ordine XLSX", "ordinal": 0},
        {"section_key": "ship_items", "title": "Itens DA SPEDIRE", "ordinal": 1},
        {"section_key": "invoice_tracking", "title": "Rastreamento de Faturas", "ordinal": 2},
    ]

    fields = [
        {
            "section_key": "header",
            "field_key": "order_number",
            "value_type": "string",
            "raw_value": raw.order_number,
            "normalized_value": raw.order_number,
            "locator_json": raw.order_number_cell.locator if raw.order_number_cell else None,
        },
        {
            "section_key": "header",
            "field_key": "sheet_name",
            "value_type": "string",
            "raw_value": raw.sheet_name,
            "normalized_value": raw.sheet_name,
            "locator_json": json.dumps({"sheet": raw.sheet_name, "source": "openpyxl"}),
        },
        {
            "section_key": "header",
            "field_key": "all_sheets",
            "value_type": "json",
            "raw_value": json.dumps(raw.all_sheets),
            "normalized_value": json.dumps(raw.all_sheets),
            "locator_json": None,
        },
        {
            "section_key": "header",
            "field_key": "versato",
            "value_type": "decimal",
            "raw_value": str(raw.versato) if raw.versato is not None else None,
            "normalized_value": str(raw.versato) if raw.versato is not None else None,
            "locator_json": raw.versato_cell.locator if raw.versato_cell else None,
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
            "field_key": "supplier_id_catalog",
            "value_type": "integer",
            "raw_value": str(match_result.supplier_id) if match_result.supplier_id else None,
            "normalized_value": str(match_result.supplier_id) if match_result.supplier_id else None,
            "locator_json": None,
            "provenance_json": json.dumps({"source": "catalog_match"}),
        },
        {
            "section_key": "header",
            "field_key": "formula_cell_count",
            "value_type": "integer",
            "raw_value": str(len(raw.formula_cells)),
            "normalized_value": str(len(raw.formula_cells)),
            "locator_json": None,
            "provenance_json": json.dumps({"note": "formulas_preserved_not_executed"}),
        },
    ]

    rows = []
    for item in raw.ship_items:
        matched_id = match_result.sku_matches.get(item.sku_raw) if item.sku_raw else None
        cells: dict = {
            "sku": {
                "raw": item.sku_raw,
                "normalized": item.sku_raw,
                "locator": item.sku_cell.locator if item.sku_cell else None,
            },
            "quantity": {
                "raw": str(item.quantity) if item.quantity is not None else None,
                "normalized": str(item.quantity) if item.quantity is not None else None,
                "locator": item.qty_cell.locator if item.qty_cell else None,
            },
            "list_price": {
                "raw": str(item.list_price) if item.list_price is not None else None,
                "normalized": str(item.list_price) if item.list_price is not None else None,
                "locator": item.list_price_cell.locator if item.list_price_cell else None,
            },
            "invoice_price": {
                "raw": str(item.invoice_price) if item.invoice_price is not None else None,
                "normalized": str(item.invoice_price) if item.invoice_price is not None else None,
                "locator": item.invoice_price_cell.locator if item.invoice_price_cell else None,
            },
            "discount": {
                "raw": str(item.discount) if item.discount is not None else None,
                "normalized": str(item.discount) if item.discount is not None else None,
                "locator": item.discount_cell.locator if item.discount_cell else None,
            },
            "product_id_catalog": {
                "raw": str(matched_id) if matched_id else None,
                "normalized": str(matched_id) if matched_id else None,
                "locator": None,
            },
        }
        rows.append(
            {
                "section_key": "ship_items",
                "row_index": item.row_index,
                "row_key": item.sku_raw or f"row_{item.row_index}",
                "cells_json": json.dumps(cells, ensure_ascii=False),
            }
        )

    # Invoice tracking rows in section invoice_tracking
    for rec in raw.invoice_records:
        cells = {
            "date": {"raw": rec.date_raw, "normalized": rec.date_raw, "locator": rec.provenance.get("date")},
            "invoice_ref": {"raw": rec.invoice_ref, "normalized": rec.invoice_ref, "locator": rec.provenance.get("invoice_ref")},
            "quantity": {"raw": str(rec.quantity) if rec.quantity is not None else None, "normalized": str(rec.quantity) if rec.quantity is not None else None, "locator": rec.provenance.get("quantity")},
            "product_name": {"raw": rec.product_name, "normalized": rec.product_name, "locator": rec.provenance.get("product")},
            "acconto": {"raw": str(rec.acconto) if rec.acconto is not None else None, "normalized": str(rec.acconto) if rec.acconto is not None else None},
            "acconto_rimasto": {"raw": str(rec.acconto_rimasto) if rec.acconto_rimasto is not None else None, "normalized": str(rec.acconto_rimasto) if rec.acconto_rimasto is not None else None},
        }
        rows.append(
            {
                "section_key": "invoice_tracking",
                "row_index": rec.row_index,
                "row_key": rec.invoice_ref or f"inv_row_{rec.row_index}",
                "cells_json": json.dumps(cells, ensure_ascii=False),
            }
        )

    doc = staging_commands.seed_document_from_occurrence(
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

    # Record metrics (best-effort — do not fail if metrics recording fails)
    error_count = sum(1 for i in issues if i.get("severity") == "ERROR")
    warn_count = sum(1 for i in issues if i.get("severity") == "WARNING")
    try:
        record_adapter_run(
            db,
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            document_id=doc.id,
            occurrence_id=occurrence_id,
            field_count=len(fields),
            row_count=len(rows),
            issue_count=len(issues),
            error_count=error_count,
            warn_count=warn_count,
            classified=classified,
        )
        # Record matching metrics
        total_skus = len(match_result.sku_matches)
        matched_count = sum(1 for v in match_result.sku_matches.values() if v is not None)
        ambiguous_count = len(match_result.ambiguous_skus)
        unmatched_count = total_skus - matched_count
        record_matching_result(
            db,
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            document_id=doc.id,
            matched_lines=matched_count,
            ambiguous_lines=ambiguous_count,
            unmatched_lines=unmatched_count,
            supplier_found=match_result.supplier_found,
        )
    except Exception:
        pass  # metrics are best-effort

    return doc
