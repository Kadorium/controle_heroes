"""Inventory repository — I5-4."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.inventory.models import (
    DEFAULT_LOCATIONS,
    GoodsReceipt,
    GoodsReceiptLine,
    InventoryMovement,
    StockBalance,
    StockLocation,
)


def ensure_default_locations(db: Session) -> None:
    existing = {loc.code for loc in db.query(StockLocation).all()}
    for code, name, loc_type in DEFAULT_LOCATIONS:
        if code not in existing:
            db.add(StockLocation(code=code, name=name, location_type=loc_type, active=True))
    db.flush()


def get_location(db: Session, location_id: int) -> StockLocation | None:
    return db.query(StockLocation).filter(StockLocation.id == location_id).first()


def get_location_by_code(db: Session, code: str) -> StockLocation | None:
    return db.query(StockLocation).filter(StockLocation.code == code).first()


def list_locations(db: Session, *, active_only: bool = True) -> list[StockLocation]:
    ensure_default_locations(db)
    q = db.query(StockLocation).order_by(StockLocation.id.asc())
    if active_only:
        q = q.filter(StockLocation.active.is_(True))
    return q.all()


def get_receipt(db: Session, receipt_id: int) -> GoodsReceipt | None:
    return (
        db.query(GoodsReceipt)
        .options(joinedload(GoodsReceipt.lines), joinedload(GoodsReceipt.location))
        .filter(GoodsReceipt.id == receipt_id)
        .first()
    )


def get_receipt_for_update(db: Session, receipt_id: int) -> GoodsReceipt | None:
    return (
        db.query(GoodsReceipt)
        .filter(GoodsReceipt.id == receipt_id)
        .with_for_update()
        .first()
    )


def list_receipts(
    db: Session,
    *,
    process_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[GoodsReceipt]:
    q = (
        db.query(GoodsReceipt)
        .options(joinedload(GoodsReceipt.lines), joinedload(GoodsReceipt.location))
        .order_by(GoodsReceipt.id.desc())
    )
    if process_id is not None:
        q = q.filter(GoodsReceipt.process_id == process_id)
    if status:
        q = q.filter(GoodsReceipt.status == status)
    return q.offset(offset).limit(limit).all()


def list_movements(
    db: Session,
    *,
    product_id: int | None = None,
    location_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryMovement]:
    q = db.query(InventoryMovement).order_by(InventoryMovement.id.desc())
    if product_id is not None:
        q = q.filter(InventoryMovement.product_id == product_id)
    if location_id is not None:
        q = q.filter(InventoryMovement.location_id == location_id)
    return q.offset(offset).limit(limit).all()


def get_balance(
    db: Session, *, location_id: int, product_id: int
) -> StockBalance | None:
    return (
        db.query(StockBalance)
        .filter(
            StockBalance.location_id == location_id,
            StockBalance.product_id == product_id,
        )
        .first()
    )


def list_balances_for_product(db: Session, product_id: int) -> list[StockBalance]:
    return (
        db.query(StockBalance)
        .options(joinedload(StockBalance.location))
        .filter(StockBalance.product_id == product_id)
        .all()
    )


def apply_balance_delta(
    db: Session, *, location_id: int, product_id: int, delta: Decimal
) -> StockBalance:
    bal = get_balance(db, location_id=location_id, product_id=product_id)
    if bal is None:
        bal = StockBalance(
            location_id=location_id, product_id=product_id, qty=Decimal("0")
        )
        db.add(bal)
        db.flush()
    bal.qty = Decimal(str(bal.qty)) + Decimal(str(delta))
    db.flush()
    return bal


def sum_movements(db: Session, *, location_id: int, product_id: int) -> Decimal:
    q = db.query(func.coalesce(func.sum(InventoryMovement.quantity_delta), 0)).filter(
        InventoryMovement.location_id == location_id,
        InventoryMovement.product_id == product_id,
    )
    return Decimal(str(q.scalar() or 0))


def sum_domestic_received_for_nat_item(db: Session, nationalization_item_id: int) -> Decimal:
    """Qty já recebida em DOMESTIC_IN confirmados (exclui REVERSED) para um nat item."""
    q = (
        db.query(func.coalesce(func.sum(GoodsReceiptLine.quantity), 0))
        .join(GoodsReceipt, GoodsReceiptLine.receipt_id == GoodsReceipt.id)
        .filter(
            GoodsReceiptLine.nationalization_item_id == nationalization_item_id,
            GoodsReceipt.status == "CONFIRMED",
            GoodsReceipt.receipt_type.in_(("DOMESTIC_IN", "RECLASS")),
        )
    )
    return Decimal(str(q.scalar() or 0))


def sum_domestic_received_for_product(db: Session, product_id: int) -> Decimal:
    q = (
        db.query(func.coalesce(func.sum(GoodsReceiptLine.quantity), 0))
        .join(GoodsReceipt, GoodsReceiptLine.receipt_id == GoodsReceipt.id)
        .filter(
            GoodsReceiptLine.product_id == product_id,
            GoodsReceipt.status == "CONFIRMED",
            GoodsReceipt.receipt_type.in_(("DOMESTIC_IN", "RECLASS")),
        )
    )
    return Decimal(str(q.scalar() or 0))


def clear_all_balances(db: Session) -> None:
    db.query(StockBalance).delete()
    db.flush()
