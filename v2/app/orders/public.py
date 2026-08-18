"""Fachada pública Orders."""

from app.orders.commands import (
    add_item,
    bind_commitment_product,
    cancel_order,
    commitment_line_summary,
    confirm_order,
    create_order,
    remove_item,
    set_payment_schedule,
    update_item,
    update_order_header,
)
from app.orders.errors import OrdersError
from app.orders.queries import (
    find_confirmed_order_items,
    get_order,
    get_order_item,
    get_order_items_bulk,
    get_order_locked,
    get_orders_bulk,
    item_line_total_str,
    list_orders,
    totals_as_strings,
)
from app.orders.repository import get_order_by_code
from app.orders.schedule import build_view as payment_schedule_view

__all__ = [
    "OrdersError",
    "create_order",
    "update_order_header",
    "add_item",
    "update_item",
    "remove_item",
    "bind_commitment_product",
    "confirm_order",
    "commitment_line_summary",
    "cancel_order",
    "set_payment_schedule",
    "payment_schedule_view",
    "get_order",
    "get_order_by_code",
    "get_order_item",
    "get_order_items_bulk",
    "get_order_locked",
    "get_orders_bulk",
    "list_orders",
    "find_confirmed_order_items",
    "item_line_total_str",
    "totals_as_strings",
]
