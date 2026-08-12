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
from app.orders.models import (
    LINE_KIND_COMMITMENT,
    LINE_KIND_PRODUCT,
    Order,
    OrderItem,
)
from app.orders.money import normalize_unit, parse_decimal, require_positive_qty


def _require_draft(order: Order) -> None:
    if order.status != "DRAFT":
        raise OrderNotDraft()


def _lock(db: Session, order: Order, expected_version: int) -> Order:
    if not repo.bump_version_if_match(db, order.id, expected_version):
        raise OrderConflict()
    db.expire(order)  # invalidate identity-map cache (items relationship included)
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
    unit: str | None = None,
    line_kind: str | None = None,
    external_code: str | None = None,
    description: str | None = None,
) -> Order:
    """Adiciona item PRODUCT (catálogo) ou COMMITMENT (sem product_id).

    line_kind explícito (V2-a): COMMITMENT não resolve Product; PRODUCT exige product_id/sku.
    """
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    _require_draft(order)

    kind = (line_kind or LINE_KIND_PRODUCT).strip().upper()
    if kind not in (LINE_KIND_PRODUCT, LINE_KIND_COMMITMENT):
        raise OrderValidationError(
            f"line_kind inválido: {line_kind!r} (use PRODUCT ou COMMITMENT)"
        )

    qty = require_positive_qty(quantity)
    price = parse_decimal(unit_price)
    pos = repo.next_item_position(db, order_id)

    if kind == LINE_KIND_COMMITMENT:
        if product_id is not None:
            raise OrderValidationError(
                "Linha COMMITMENT não aceita product_id — use line_kind=PRODUCT"
            )
        code = (external_code or sku or "").strip()
        desc = (description or "").strip()
        if not code and not desc:
            raise OrderValidationError(
                "Linha COMMITMENT exige external_code (ou sku) e description"
            )
        if not desc:
            raise OrderValidationError("Linha COMMITMENT exige description")
        if not code:
            raise OrderValidationError("Linha COMMITMENT exige external_code (ou sku)")
        repo.add_item(
            db,
            OrderItem(
                order_id=order_id,
                product_id=None,
                line_kind=LINE_KIND_COMMITMENT,
                external_code=code[:128],
                sku_snapshot=code[:64],
                description_snapshot=desc[:512],
                quantity=qty,
                unit=normalize_unit(unit),
                unit_price=price,
                position=pos,
            ),
        )
        return _lock(db, order, expected_version)

    # PRODUCT — resolve no catálogo; nunca inventa Product
    product = catalog_public.resolve_product(db, product_id=product_id, sku=sku)
    repo.add_item(
        db,
        OrderItem(
            order_id=order_id,
            product_id=product.id,
            line_kind=LINE_KIND_PRODUCT,
            external_code=(external_code.strip()[:128] if external_code and external_code.strip() else None),
            sku_snapshot=product.sku,
            description_snapshot=product.description,
            quantity=qty,
            unit=normalize_unit(unit),
            unit_price=price,
            position=pos,
        ),
    )
    return _lock(db, order, expected_version)


def commitment_line_summary(order: Order) -> dict:
    """Contagens para Audit no confirm (V2-b backend)."""
    items = list(order.items or [])
    commitment_ids = [i.id for i in items if i.line_kind == LINE_KIND_COMMITMENT]
    product_ids = [i.id for i in items if i.line_kind == LINE_KIND_PRODUCT]
    return {
        "total_items": len(items),
        "commitment_count": len(commitment_ids),
        "product_count": len(product_ids),
        "commitment_item_ids": commitment_ids,
        "has_commitment_lines": bool(commitment_ids),
    }


def update_item(
    db: Session,
    order_id: int,
    item_id: int,
    *,
    expected_version: int,
    quantity: str | Decimal | None = None,
    unit_price: str | Decimal | None | object = ...,
    unit: str | None | object = ...,
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
    if unit is not ...:
        item.unit = normalize_unit(unit)  # type: ignore[arg-type]
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
