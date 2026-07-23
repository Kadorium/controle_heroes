from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.orders import repository as repo
from app.orders.errors import (
    InvalidTransition,
    OrderConflict,
    OrderItemNotFound,
    OrderNotDraft,
    OrderNotFound,
    OrderValidationError,
)
from app.orders.models import Order, OrderItem
from app.orders.money import parse_decimal, require_positive_qty


def _require_draft(order: Order) -> None:
    if order.status != "DRAFT":
        raise OrderNotDraft()


def _lock(db: Session, order: Order, expected_version: int) -> Order:
    if not repo.bump_version_if_match(db, order.id, expected_version):
        raise OrderConflict()
    refreshed = repo.get_order(db, order.id)
    assert refreshed is not None
    return refreshed


def create_order(
    db: Session,
    *,
    code: str,
    supplier_id: int,
    created_by_actor_id: str,
    currency: str = "EUR",
    order_date: date | None = None,
    notes: str | None = None,
    external_ref: str | None = None,
    source_system: str = "MANUAL",
) -> Order:
    code_norm = (code or "").strip()
    if not code_norm:
        raise OrderValidationError("Código da ordem é obrigatório")
    if not created_by_actor_id or not str(created_by_actor_id).strip():
        raise OrderValidationError("Ator da criação é obrigatório")
    if repo.get_order_by_code(db, code_norm):
        raise OrderValidationError(f"Código de ordem já existe: {code_norm}")
    catalog_public.get_supplier(db, supplier_id)
    cur = (currency or "EUR").strip().upper()
    if len(cur) < 3:
        raise OrderValidationError("Moeda inválida")
    order = Order(
        code=code_norm,
        supplier_id=supplier_id,
        status="DRAFT",
        currency=cur,
        order_date=order_date or date.today(),
        created_by_actor_id=str(created_by_actor_id).strip(),
        notes=notes.strip() if notes and notes.strip() else None,
        external_ref=external_ref.strip() if external_ref and external_ref.strip() else None,
        source_system=(source_system or "MANUAL").strip().upper(),
        version=1,
    )
    return repo.add_order(db, order)


def update_order_header(
    db: Session,
    order_id: int,
    *,
    expected_version: int,
    supplier_id: int | None = None,
    currency: str | None = None,
    order_date: date | None = None,
    notes: str | None = ...,  # type: ignore[assignment]
    external_ref: str | None = ...,  # type: ignore[assignment]
) -> tuple[Order, list[str]]:
    """Retorna ordem e lista de ações auditáveis (ex.: supplier_changed)."""
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    _require_draft(order)
    audit_actions: list[str] = []
    if supplier_id is not None and supplier_id != order.supplier_id:
        catalog_public.get_supplier(db, supplier_id)
        order.supplier_id = supplier_id
        audit_actions.append("supplier_changed")
    if currency is not None:
        order.currency = currency.strip().upper()
    if order_date is not None:
        order.order_date = order_date
    if notes is not ...:
        order.notes = notes.strip() if notes and notes.strip() else None
    if external_ref is not ...:
        order.external_ref = external_ref.strip() if external_ref and external_ref.strip() else None
    return _lock(db, order, expected_version), audit_actions


def add_item(
    db: Session,
    order_id: int,
    *,
    expected_version: int,
    product_id: int | None = None,
    sku: str | None = None,
    quantity: str | Decimal,
    unit_price: str | Decimal | None = None,
) -> Order:
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    _require_draft(order)
    product = catalog_public.resolve_product(db, product_id=product_id, sku=sku)
    qty = require_positive_qty(quantity)
    price = parse_decimal(unit_price)
    pos = repo.next_item_position(db, order_id)
    repo.add_item(
        db,
        OrderItem(
            order_id=order_id,
            product_id=product.id,
            sku_snapshot=product.sku,
            description_snapshot=product.description,
            quantity=qty,
            unit_price=price,
            position=pos,
        ),
    )
    return _lock(db, order, expected_version)


def update_item(
    db: Session,
    order_id: int,
    item_id: int,
    *,
    expected_version: int,
    quantity: str | Decimal | None = None,
    unit_price: str | Decimal | None | object = ...,
) -> tuple[Order, bool]:
    """Retorna (order, price_or_qty_changed)."""
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    _require_draft(order)
    item = repo.get_item(db, order_id, item_id)
    if not item:
        raise OrderItemNotFound(item_id)
    material = False
    if quantity is not None:
        item.quantity = require_positive_qty(quantity)
        material = True
    if unit_price is not ...:
        item.unit_price = parse_decimal(unit_price)  # type: ignore[arg-type]
        material = True
    return _lock(db, order, expected_version), material


def remove_item(
    db: Session, order_id: int, item_id: int, *, expected_version: int
) -> Order:
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    _require_draft(order)
    item = repo.get_item(db, order_id, item_id)
    if not item:
        raise OrderItemNotFound(item_id)
    repo.delete_item(db, item)
    return _lock(db, order, expected_version)


def confirm_order(db: Session, order_id: int, *, expected_version: int) -> Order:
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    if order.status != "DRAFT":
        raise InvalidTransition("Só DRAFT pode ser confirmada")
    if not order.items:
        raise OrderValidationError("Ordem sem itens não pode ser confirmada")
    order.status = "CONFIRMED"
    return _lock(db, order, expected_version)


def cancel_order(
    db: Session,
    order_id: int,
    *,
    expected_version: int,
    reason_code: str | None,
    require_reason: bool,
) -> Order:
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    if order.status not in ("DRAFT", "CONFIRMED"):
        raise InvalidTransition(f"Não é possível cancelar ordem em {order.status}")
    if order.status == "CONFIRMED" or require_reason:
        if not reason_code or not reason_code.strip():
            raise OrderValidationError("reason_code obrigatório para cancelar ordem CONFIRMADA")
    order.status = "CANCELLED"
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancel_reason_code = reason_code.strip() if reason_code and reason_code.strip() else None
    return _lock(db, order, expected_version)
