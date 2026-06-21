"""Heroes Order Import Format v1 — schema canônico e export normalizado."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

from pydantic import BaseModel, Field

FORMAT_VERSION = "Heroes Order Import Format v1"


class HeroesOrderBlock(BaseModel):
    source_file: str | None = None
    file_checksum: str | None = None
    sheet_name: str
    detected_order_number: str | None = None
    confirmed_order_number: str | None = None
    supplier: str = "Heroes Itália"
    currency: str = "EUR"
    parser_confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)


class HeroesInvoiceBlock(BaseModel):
    invoice_number: str | None = None
    invoice_date: str | None = None
    invoice_type: str | None = None
    currency: str = "EUR"
    invoice_total: str | None = None
    paid_total: str | None = None
    remaining_balance: str | None = None
    source_row_start: int | None = None
    source_row_end: int | None = None


class HeroesInvoiceItemBlock(BaseModel):
    invoice_number: str | None = None
    row_number: int
    product_name_raw: str
    product_category_suggested: str | None = None
    sku_epic: str | None = None
    quantity: int | None = None
    unit_price_invoice: str | None = None
    discount_unit: str | None = None
    credit_unit: str | None = None
    credit_accumulated: str | None = None
    source_column_product_header: str | None = None
    parser_confidence: float | None = None
    needs_review: bool = False


class HeroesDispatchBlock(BaseModel):
    product_name_raw: str
    category_suggested: str | None = None
    quantity_to_dispatch: int | None = None
    price_listino: str | None = None
    price_fattura: str | None = None
    discount: str | None = None
    acconto: str | None = None
    credit_remaining: str | None = None
    notes: str | None = None
    parser_confidence: float | None = None
    needs_review: bool = False


class HeroesPaymentPreviewBlock(BaseModel):
    payment_date: str | None = None
    invoice_reference: str | None = None
    order_reference: str | None = None
    amount: str | None = None
    currency: str = "EUR"
    source_sheet: str | None = None
    confidence: float | None = None
    needs_review: bool = True


class HeroesLogisticsPreviewBlock(BaseModel):
    invoice_number: str | None = None
    product_name_raw: str | None = None
    po_reference: str | None = None
    modal: str | None = None
    boxes: int | None = None
    pcs_per_box: int | None = None
    total_pcs: int | None = None
    status: str | None = None
    confidence: float | None = None
    needs_review: bool = True


def preview_to_canonical(preview: dict[str, Any], *, source_file: str | None = None) -> dict[str, Any]:
    order = HeroesOrderBlock(
        source_file=source_file or preview.get("source_file"),
        file_checksum=preview.get("file_checksum"),
        sheet_name=preview.get("sheet_name", ""),
        detected_order_number=preview.get("order_number_from_content") or preview.get("order_number"),
        confirmed_order_number=preview.get("confirmed_order_number") or preview.get("order_number"),
        supplier=preview.get("supplier", "Heroes Itália"),
        currency=preview.get("currency", "EUR"),
        parser_confidence=preview.get("parser_confidence"),
        warnings=preview.get("warnings") or [],
    )

    invoices: list[HeroesInvoiceBlock] = []
    inv_rows: dict[str, HeroesInvoiceBlock] = {}
    for it in preview.get("invoice_items") or []:
        inv_no = it.get("invoice_number") or "—"
        if inv_no not in inv_rows:
            inv_rows[inv_no] = HeroesInvoiceBlock(
                invoice_number=inv_no if inv_no != "—" else None,
                invoice_date=it.get("invoice_date"),
                source_row_start=it.get("row_number"),
                source_row_end=it.get("row_number"),
            )
        else:
            block = inv_rows[inv_no]
            if block.source_row_end is not None:
                block.source_row_end = max(block.source_row_end, it.get("row_number") or block.source_row_end)
        paid = it.get("acconto_amount")
        if paid:
            inv_rows[inv_no].paid_total = str(
                (float(inv_rows[inv_no].paid_total or 0) + float(paid)) if inv_rows[inv_no].paid_total else paid
            )
    invoices = list(inv_rows.values())

    items = [
        HeroesInvoiceItemBlock(
            invoice_number=it.get("invoice_number"),
            row_number=it.get("row_number"),
            product_name_raw=it.get("product_name_raw"),
            product_category_suggested=it.get("suggested_category"),
            quantity=it.get("item_quantity"),
            credit_unit=it.get("credit_per_unit"),
            credit_accumulated=it.get("credit_accumulated"),
            source_column_product_header=it.get("source_column_product_header"),
            parser_confidence=it.get("parser_confidence"),
            needs_review=bool(it.get("needs_review") or it.get("category_review")),
        )
        for it in preview.get("invoice_items") or []
    ]

    dispatch = [
        HeroesDispatchBlock(
            product_name_raw=d.get("product_name_raw"),
            category_suggested=d.get("suggested_category"),
            quantity_to_dispatch=d.get("quantity_to_dispatch"),
            price_listino=d.get("price_listino"),
            price_fattura=d.get("invoice_price"),
            discount=d.get("discount"),
            acconto=d.get("acconto"),
            credit_remaining=d.get("credit_remaining"),
            notes=d.get("notes"),
            needs_review=bool(d.get("category_review")),
        )
        for d in preview.get("da_spedire") or []
    ]

    payments: list[HeroesPaymentPreviewBlock] = []
    fin = preview.get("financial_preview") or {}
    for p in fin.get("payments_preview") or []:
        payments.append(
            HeroesPaymentPreviewBlock(
                payment_date=p.get("date"),
                invoice_reference=p.get("invoice_number"),
                amount=p.get("amount"),
                source_sheet=fin.get("sheet_name"),
                confidence=p.get("confidence"),
            )
        )

    logistics: list[HeroesLogisticsPreviewBlock] = []
    log = preview.get("logistics_preview") or {}
    for line in log.get("logistics_lines") or []:
        logistics.append(
            HeroesLogisticsPreviewBlock(
                invoice_number=line.get("invoice_number"),
                product_name_raw=line.get("product_name_raw"),
                po_reference=line.get("po_reference"),
                modal=line.get("modal"),
                boxes=line.get("boxes"),
                pcs_per_box=line.get("pcs_per_box"),
                total_pcs=line.get("total_pcs"),
                status=line.get("status"),
            )
        )

    return {
        "format_version": FORMAT_VERSION,
        "order": order.model_dump(),
        "invoices": [i.model_dump() for i in invoices],
        "invoice_items": [i.model_dump() for i in items],
        "dispatch_pending": [d.model_dump() for d in dispatch],
        "payments_preview": [p.model_dump() for p in payments],
        "logistics_preview": [l.model_dump() for l in logistics],
        "warnings": preview.get("warnings") or [],
    }


def _rows_to_csv(headers: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in headers})
    return buf.getvalue()


def export_normalized_zip(canonical: dict[str, Any]) -> bytes:
    """Gera ZIP com CSVs: orders, invoices, invoice_items, dispatch_pending, payments_preview, logistics_preview, warnings."""
    files = {
        "orders.csv": _rows_to_csv(
            list(HeroesOrderBlock.model_fields.keys()),
            [canonical["order"]],
        ),
        "invoices.csv": _rows_to_csv(
            list(HeroesInvoiceBlock.model_fields.keys()),
            canonical.get("invoices") or [],
        ),
        "invoice_items.csv": _rows_to_csv(
            list(HeroesInvoiceItemBlock.model_fields.keys()),
            canonical.get("invoice_items") or [],
        ),
        "dispatch_pending.csv": _rows_to_csv(
            list(HeroesDispatchBlock.model_fields.keys()),
            canonical.get("dispatch_pending") or [],
        ),
        "payments_preview.csv": _rows_to_csv(
            list(HeroesPaymentPreviewBlock.model_fields.keys()),
            canonical.get("payments_preview") or [],
        ),
        "logistics_preview.csv": _rows_to_csv(
            list(HeroesLogisticsPreviewBlock.model_fields.keys()),
            canonical.get("logistics_preview") or [],
        ),
        "warnings.csv": _rows_to_csv(["warning"], [{"warning": w} for w in canonical.get("warnings") or []]),
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return out.getvalue()


def export_normalized_xlsx(canonical: dict[str, Any]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)

    sheets_map = {
        "orders": ([canonical["order"]], list(HeroesOrderBlock.model_fields.keys())),
        "invoices": (canonical.get("invoices") or [], list(HeroesInvoiceBlock.model_fields.keys())),
        "invoice_items": (canonical.get("invoice_items") or [], list(HeroesInvoiceItemBlock.model_fields.keys())),
        "dispatch_pending": (canonical.get("dispatch_pending") or [], list(HeroesDispatchBlock.model_fields.keys())),
        "payments_preview": (canonical.get("payments_preview") or [], list(HeroesPaymentPreviewBlock.model_fields.keys())),
        "logistics_preview": (canonical.get("logistics_preview") or [], list(HeroesLogisticsPreviewBlock.model_fields.keys())),
        "warnings": ([{"warning": w} for w in canonical.get("warnings") or []], ["warning"]),
    }

    for title, (rows, headers) in sheets_map.items():
        ws = wb.create_sheet(title)
        ws.append(headers)
        for row in rows:
            ws.append([str(row.get(h)) if isinstance(row.get(h), list) else row.get(h) for h in headers])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
