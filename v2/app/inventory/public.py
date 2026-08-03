"""Fachada pública Inventory (J#5 I5-4)."""

from __future__ import annotations

from app.inventory.commands import (
    add_receipt_lines,
    confirm_receipt,
    create_receipt,
    rebuild_stock_balances,
    record_adjustment,
    record_receipt,
    reverse_receipt,
)
from app.inventory.errors import (
    InventoryError,
    InventoryNotImplemented,
    LocationNotFound,
    NationalizationRequired,
    OverReceiptError,
    ReceiptConflict,
    ReceiptImmutable,
    ReceiptNotFound,
)
from app.inventory.queries import (
    get_sku_position,
    get_stock_balance,
    list_movements,
    stock_balance_bulk,
)
from app.inventory.repository import (
    ensure_default_locations,
    get_receipt as _get_receipt,
    list_locations,
    list_receipts,
)


def get_receipt(db, receipt_id: int):
    r = _get_receipt(db, receipt_id)
    if not r:
        raise ReceiptNotFound(receipt_id)
    return r

# Aliases estáveis do scaffold I5-0
stock_balance = get_stock_balance

__all__ = [
    "InventoryError",
    "InventoryNotImplemented",
    "LocationNotFound",
    "ReceiptNotFound",
    "ReceiptConflict",
    "ReceiptImmutable",
    "NationalizationRequired",
    "OverReceiptError",
    "create_receipt",
    "add_receipt_lines",
    "confirm_receipt",
    "reverse_receipt",
    "record_receipt",
    "record_adjustment",
    "list_movements",
    "get_stock_balance",
    "stock_balance",
    "stock_balance_bulk",
    "get_sku_position",
    "rebuild_stock_balances",
    "list_locations",
    "list_receipts",
    "get_receipt",
    "ensure_default_locations",
]
