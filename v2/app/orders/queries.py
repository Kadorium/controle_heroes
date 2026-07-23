from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.orders import repository as repo
from app.orders.errors import OrderNotFound
from app.orders.models import Order, OrderItem
from app.orders.money import decimal_str, line_amount


@dataclass
class OrderTotals:
    priced_subtotal: Decimal | None
    unpriced_item_count: int
    commercial_total: Decimal | None


def compute_totals(items: list[OrderItem]) -> OrderTotals:
    if not items:
        return OrderTotals(priced_subtotal=None, unpriced_item_count=0, commercial_total=None)
    priced = Decimal("0")
    unpriced = 0
    any_priced = False
    for item in items:
        amt = line_amount(item.quantity, item.unit_price)
        if amt is None:
            unpriced += 1
        else:
            any_priced = True
            priced += amt
    priced_subtotal = priced if any_priced else None
    commercial_total = priced_subtotal if unpriced == 0 and any_priced else None
    return OrderTotals(
        priced_subtotal=priced_subtotal,
        unpriced_item_count=unpriced,
        commercial_total=commercial_total,
    )


def get_order(db: Session, order_id: int) -> Order:
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    return order


def get_order_locked(db: Session, order_id: int) -> Order:
    order = repo.get_order_for_update(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    return order


def list_orders(
    db: Session, *, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[Order]:
    return repo.list_orders(db, status=status, limit=limit, offset=offset)


def item_line_total_str(item: OrderItem) -> str | None:
    return decimal_str(line_amount(item.quantity, item.unit_price))


def totals_as_strings(order: Order) -> dict[str, str | int | None]:
    t = compute_totals(list(order.items))
    return {
        "priced_subtotal": decimal_str(t.priced_subtotal),
        "unpriced_item_count": t.unpriced_item_count,
        "commercial_total": decimal_str(t.commercial_total),
    }
