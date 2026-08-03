from sqlalchemy import update
from sqlalchemy.orm import Session, joinedload

from app.orders.models import Order, OrderItem


def get_order(db: Session, order_id: int) -> Order | None:
    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )


def get_orders_by_ids(db: Session, order_ids: list[int] | set[int]) -> list[Order]:
    """Uma query IN (...) — ids vazios → []. Sem joinedload (só cabeçalho)."""
    ids = sorted({int(i) for i in order_ids})
    if not ids:
        return []
    return db.query(Order).filter(Order.id.in_(ids)).all()


def get_order_for_update(db: Session, order_id: int) -> Order | None:
    """Lock order row + items for concurrent invoice qty checks (Billing)."""
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )
    if not order:
        return None
    (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .with_for_update()
        .all()
    )
    return get_order(db, order_id)


def get_order_by_code(db: Session, code: str) -> Order | None:
    return db.query(Order).filter(Order.code == code).first()


def list_orders(
    db: Session, *, status: str | None, limit: int, offset: int
) -> list[Order]:
    q = db.query(Order).options(joinedload(Order.items))
    if status:
        q = q.filter(Order.status == status)
    return q.order_by(Order.updated_at.desc()).offset(offset).limit(limit).all()


def add_order(db: Session, order: Order) -> Order:
    db.add(order)
    db.flush()
    return order


def add_item(db: Session, item: OrderItem) -> OrderItem:
    db.add(item)
    db.flush()
    return item


def get_item(db: Session, order_id: int, item_id: int) -> OrderItem | None:
    return (
        db.query(OrderItem)
        .filter(OrderItem.id == item_id, OrderItem.order_id == order_id)
        .first()
    )


def get_item_by_id(db: Session, item_id: int) -> OrderItem | None:
    return db.query(OrderItem).filter(OrderItem.id == item_id).first()


def get_items_by_ids(db: Session, item_ids: list[int] | set[int]) -> list[OrderItem]:
    ids = sorted({int(i) for i in item_ids})
    if not ids:
        return []
    return db.query(OrderItem).filter(OrderItem.id.in_(ids)).all()


def delete_item(db: Session, item: OrderItem) -> None:
    db.delete(item)
    db.flush()


def bump_version_if_match(db: Session, order_id: int, expected_version: int) -> bool:
    """Update atômico; retorna False se versão não bater."""
    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.version == expected_version)
        .values(version=expected_version + 1)
    )
    db.flush()
    return result.rowcount == 1  # type: ignore[attr-defined]


def next_item_position(db: Session, order_id: int) -> int:
    current = (
        db.query(OrderItem.position)
        .filter(OrderItem.order_id == order_id)
        .order_by(OrderItem.position.desc())
        .first()
    )
    return (current[0] + 1) if current else 1
