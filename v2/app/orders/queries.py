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


def get_orders_bulk(db: Session, order_ids: list[int] | set[int]) -> dict[int, Order]:
    """Resolve pedidos em lote. Ids ausentes não entram no mapa."""
    from app.orders import repository as repo

    return {o.id: o for o in repo.get_orders_by_ids(db, order_ids)}


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


def get_order_item(db: Session, order_item_id: int) -> OrderItem:
    from app.orders.errors import OrderItemNotFound

    item = repo.get_item_by_id(db, order_item_id)
    if not item:
        raise OrderItemNotFound(order_item_id)
    return item


def get_order_items_bulk(db: Session, item_ids: list[int] | set[int]) -> dict[int, OrderItem]:
    return {i.id: i for i in repo.get_items_by_ids(db, item_ids)}


def list_orders(
    db: Session, *, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[Order]:
    return repo.list_orders(db, status=status, limit=limit, offset=offset)


def find_confirmed_order_items(
    db: Session,
    *,
    order_id: int | None = None,
    order_code: str | None = None,
    external_ref: str | None = None,
    sku: str | None = None,
    supplier_id: int | None = None,
    limit: int = 50,
) -> list[tuple[Order, OrderItem]]:
    """Candidatos para Logistics — só CONFIRMED. Retorna pares (order, item)."""
    from sqlalchemy.orm import joinedload

    q = (
        db.query(OrderItem)
        .join(Order)
        .options(joinedload(OrderItem.order))
        .filter(Order.status == "CONFIRMED")
    )
    if order_id is not None:
        q = q.filter(Order.id == order_id)
    if order_code:
        q = q.filter(Order.code == order_code.strip())
    if external_ref:
        q = q.filter(Order.external_ref == external_ref.strip())
    if supplier_id is not None:
        q = q.filter(Order.supplier_id == supplier_id)
    if sku:
        q = q.filter(OrderItem.sku_snapshot.ilike(f"%{sku.strip()}%"))
    items = q.limit(min(limit, 100)).all()
    return [(item.order, item) for item in items]


def item_line_total_str(item: OrderItem) -> str | None:
    return decimal_str(line_amount(item.quantity, item.unit_price))


def totals_as_strings(order: Order) -> dict[str, str | int | None]:
    t = compute_totals(list(order.items))
    return {
        "priced_subtotal": decimal_str(t.priced_subtotal),
        "unpriced_item_count": t.unpriced_item_count,
        "commercial_total": decimal_str(t.commercial_total),
    }
