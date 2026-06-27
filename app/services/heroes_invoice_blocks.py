"""Agrupa invoice_items flat em invoice_blocks — acconto na fatura, itens separados."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _item_without_acconto(row: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(row)
    out.pop("acconto_amount", None)
    out.pop("acconto_remaining", None)
    return out


def _normalize_inv_key(invoice_number: str | None) -> str:
    return str(invoice_number) if invoice_number else "—"


def build_invoice_blocks(flat_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Converte linhas flat em blocos fatura → acconto_payments + items (sem acconto nos items)."""
    order: list[str] = []
    blocks: dict[str, dict[str, Any]] = {}

    for row in flat_items:
        inv_key = _normalize_inv_key(row.get("invoice_number"))
        if inv_key not in blocks:
            blocks[inv_key] = {
                "invoice_number": None if inv_key == "—" else inv_key,
                "invoice_date": row.get("invoice_date"),
                "acconto_remaining": row.get("acconto_remaining"),
                "acconto_payments": [],
                "items": [],
            }
            order.append(inv_key)
        block = blocks[inv_key]

        if row.get("invoice_date"):
            block["invoice_date"] = row["invoice_date"]
        if row.get("acconto_remaining") and not block.get("acconto_remaining"):
            block["acconto_remaining"] = row["acconto_remaining"]

        acconto = row.get("acconto_amount")
        row_number = row.get("row_number")
        if acconto is not None and str(acconto).strip():
            block["acconto_payments"].append(
                {
                    "amount": str(acconto),
                    "row_number": row_number,
                }
            )

        product = row.get("product_name_raw")
        if product:
            block["items"].append(_item_without_acconto(row))

    result: list[dict[str, Any]] = []
    for inv_key in order:
        block = blocks[inv_key]
        inv_num = block["invoice_number"] or inv_key
        payments = block["acconto_payments"]
        if len(payments) > 1:
            amounts = [p["amount"] for p in payments]
            if len(set(amounts)) == 1:
                payments = [payments[0]]
                payments[0]["receipt_reference"] = f"ACCONTO-{inv_num}"
            else:
                for p in payments:
                    p["receipt_reference"] = f"ACCONTO-{inv_num}-{p['row_number']}"
        elif len(payments) == 1:
            payments[0]["receipt_reference"] = f"ACCONTO-{inv_num}"
        block["acconto_payments"] = payments
        result.append(block)
    return result


def get_invoice_blocks_for_preview(preview: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = preview.get("invoice_blocks")
    if blocks is not None:
        return blocks
    return build_invoice_blocks(preview.get("invoice_items") or [])


def attach_invoice_blocks_to_preview(preview: dict[str, Any]) -> dict[str, Any]:
    """Popula invoice_blocks e invoices_detected a partir de invoice_items."""
    items = preview.get("invoice_items") or []
    blocks = build_invoice_blocks(items)
    preview["invoice_blocks"] = blocks
    preview["invoices_detected"] = [
        {
            "invoice_number": b.get("invoice_number"),
            "invoice_date": b.get("invoice_date"),
            "acconto_payments": b.get("acconto_payments"),
            "items": b.get("items"),
        }
        for b in blocks
    ]
    return preview
