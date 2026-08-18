from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.catalog import public as catalog_public
from app.catalog.public import CatalogError
from app.documents import public as documents_public
from app.foundation.billing_facts import issued_qty_for_order_item
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.orders import public as orders_public
from app.orders.errors import OrdersError
from app.orders.models import Order
from app.orders.money import decimal_str

router = APIRouter(tags=["orders"])


class OrderCreate(BaseModel):
    code: str
    supplier_id: int
    currency: str = "EUR"
    order_date: date | None = None
    notes: str | None = None
    external_ref: str | None = None


class OrderUpdate(BaseModel):
    expected_version: int
    supplier_id: int | None = None
    currency: str | None = None
    order_date: date | None = None
    notes: str | None = None
    external_ref: str | None = None


class ItemCreate(BaseModel):
    expected_version: int
    product_id: int | None = None
    sku: str | None = None
    quantity: str
    unit_price: str | None = None
    unit: str | None = None
    line_kind: str | None = None  # PRODUCT (default) | COMMITMENT
    external_code: str | None = None
    description: str | None = None


class ItemUpdate(BaseModel):
    expected_version: int
    quantity: str | None = None
    unit_price: str | None = None
    unit: str | None = None


class BindProductBody(BaseModel):
    expected_version: int
    product_id: int


class VersionBody(BaseModel):
    expected_version: int


class CancelBody(BaseModel):
    expected_version: int
    reason_code: str | None = None


class ScheduleLineIn(BaseModel):
    due_date: date | None = None
    condition_text: str | None = None
    percent: str | None = None
    amount: str | None = None


class ScheduleReplace(BaseModel):
    expected_version: int
    mode: str | None = None
    lines: list[ScheduleLineIn] = Field(default_factory=list)
    reason_code: str | None = None


class ScheduleLineOut(BaseModel):
    id: int
    sequence: int
    due_date: date | None = None
    condition_text: str | None = None
    percent: str | None = None
    amount: str | None = None
    derived_amount: str | None = None


class ScheduleView(BaseModel):
    order_id: int
    order_version: int
    order_status: str
    currency: str
    mode: str | None = None
    commercial_total: str | None = None
    amount_sum: str | None = None
    delta: str | None = None
    coherence: str | None = None
    lines: list[ScheduleLineOut] = Field(default_factory=list)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int | None
    line_kind: str
    external_code: str | None = None
    sku_snapshot: str
    description_snapshot: str
    quantity: str
    unit: str | None = None
    unit_price: str | None
    line_total: str | None
    position: int


class DocumentBrief(BaseModel):
    id: int
    original_filename: str
    mime_type: str | None = None
    role: str | None = None


class OrderResponse(BaseModel):
    id: int
    code: str
    external_ref: str | None
    source_system: str
    supplier_id: int
    supplier_name: str | None = None
    supplier_is_active: bool | None = None
    status: str
    currency: str
    order_date: date
    created_by_actor_id: str
    notes: str | None
    version: int
    cancel_reason_code: str | None = None
    cancelled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[OrderItemResponse] = Field(default_factory=list)
    priced_subtotal: str | None = None
    unpriced_item_count: int = 0
    commercial_total: str | None = None
    documents: list[DocumentBrief] = Field(default_factory=list)


class OrderListItem(BaseModel):
    id: int
    code: str
    supplier_id: int
    supplier_name: str | None = None
    status: str
    currency: str
    order_date: date
    created_by_actor_id: str
    version: int
    updated_at: datetime | None = None
    commercial_total: str | None = None
    unpriced_item_count: int = 0


def _map_error(exc: OrdersError | CatalogError) -> AppError:
    code = exc.code
    status = 400
    if code in (
        "item_not_commitment",
        "line_already_invoiced",
        "invalid_product",
        "schedule_when_required",
        "schedule_mode_mixed",
        "schedule_amount_mismatch",
        "reason_required",
    ):
        status = 422
    elif code.endswith("not_found"):
        status = 404
    elif code == "conflict":
        status = 409
    elif code in ("order_not_draft", "invalid_transition"):
        status = 409
    return AppError(exc.message, code=code, status_code=status)


def _order_response(db: Session, order: Order, *, include_docs: bool = True) -> OrderResponse:
    totals = orders_public.totals_as_strings(order)
    items = [
        OrderItemResponse(
            id=i.id,
            product_id=i.product_id,
            line_kind=i.line_kind,
            external_code=i.external_code,
            sku_snapshot=i.sku_snapshot,
            description_snapshot=i.description_snapshot,
            quantity=decimal_str(i.quantity) or "0",
            unit=i.unit,
            unit_price=decimal_str(i.unit_price),
            line_total=orders_public.item_line_total_str(i),
            position=i.position,
        )
        for i in order.items
    ]
    docs: list[DocumentBrief] = []
    if include_docs:
        for d in documents_public.list_by_entity(db, "order", str(order.id)):
            docs.append(
                DocumentBrief(
                    id=d.id,
                    original_filename=d.original_filename,
                    mime_type=d.mime_type,
                )
            )
    # Enrichment via Catalog public API only (same pattern as list_orders).
    supplier = catalog_public.get_suppliers_bulk(db, {order.supplier_id}).get(order.supplier_id)
    return OrderResponse(
        id=order.id,
        code=order.code,
        external_ref=order.external_ref,
        source_system=order.source_system,
        supplier_id=order.supplier_id,
        supplier_name=supplier.name if supplier else None,
        supplier_is_active=supplier.is_active if supplier else None,
        status=order.status,
        currency=order.currency,
        order_date=order.order_date,
        created_by_actor_id=order.created_by_actor_id,
        notes=order.notes,
        version=order.version,
        cancel_reason_code=order.cancel_reason_code,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        priced_subtotal=totals["priced_subtotal"],  # type: ignore[arg-type]
        unpriced_item_count=int(totals["unpriced_item_count"] or 0),
        commercial_total=totals["commercial_total"],  # type: ignore[arg-type]
        documents=docs,
    )


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            order = orders_public.create_order(
                uow.session,
                code=payload.code,
                supplier_id=payload.supplier_id,
                created_by_actor_id=str(user.id),
                currency=payload.currency,
                order_date=payload.order_date,
                notes=payload.notes,
                external_ref=payload.external_ref,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="order",
                entity_id=str(order.id),
                action="create",
                reason_code="ORDER_CREATE",
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:read")
    rows = orders_public.list_orders(db, status=status, limit=limit, offset=offset)
    from app.catalog import public as catalog_public

    suppliers = catalog_public.get_suppliers_bulk(db, {o.supplier_id for o in rows})
    out: list[OrderListItem] = []
    for o in rows:
        t = orders_public.totals_as_strings(o)
        supplier = suppliers.get(o.supplier_id)
        out.append(
            OrderListItem(
                id=o.id,
                code=o.code,
                supplier_id=o.supplier_id,
                supplier_name=supplier.name if supplier else None,
                status=o.status,
                currency=o.currency,
                order_date=o.order_date,
                created_by_actor_id=o.created_by_actor_id,
                version=o.version,
                updated_at=o.updated_at,
                commercial_total=t["commercial_total"],  # type: ignore[arg-type]
                unpriced_item_count=int(t["unpriced_item_count"] or 0),
            )
        )
    return out


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:read")
    try:
        order = orders_public.get_order(db, order_id)
        return _order_response(db, order)
    except OrdersError as e:
        raise _map_error(e) from e


@router.patch("/orders/{order_id}", response_model=OrderResponse)
def patch_order(
    order_id: int,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            kwargs: dict = {
                "expected_version": payload.expected_version,
                "supplier_id": payload.supplier_id,
                "currency": payload.currency,
                "order_date": payload.order_date,
            }
            if "notes" in payload.model_fields_set:
                kwargs["notes"] = payload.notes
            if "external_ref" in payload.model_fields_set:
                kwargs["external_ref"] = payload.external_ref
            order, actions = orders_public.update_order_header(
                uow.session,
                order_id,
                **kwargs,
            )
            for action in actions or ["update_header"]:
                audit_public.record_event(
                    uow.session,
                    actor_id=str(user.id),
                    entity_type="order",
                    entity_id=str(order.id),
                    action=action,
                    reason_code="ORDER_UPDATE_DRAFT",
                )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.post("/orders/{order_id}/items", response_model=OrderResponse, status_code=201)
def add_item(
    order_id: int,
    payload: ItemCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            order = orders_public.add_item(
                uow.session,
                order_id,
                expected_version=payload.expected_version,
                product_id=payload.product_id,
                sku=payload.sku,
                quantity=payload.quantity,
                unit_price=payload.unit_price,
                unit=payload.unit,
                line_kind=payload.line_kind,
                external_code=payload.external_code,
                description=payload.description,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="order",
                entity_id=str(order.id),
                action="add_item",
                reason_code="ORDER_ADD_ITEM",
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.patch("/orders/{order_id}/items/{item_id}", response_model=OrderResponse)
def patch_item(
    order_id: int,
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            kwargs: dict = {"expected_version": payload.expected_version}
            if payload.quantity is not None:
                kwargs["quantity"] = payload.quantity
            if "unit_price" in payload.model_fields_set:
                kwargs["unit_price"] = payload.unit_price
            if "unit" in payload.model_fields_set:
                kwargs["unit"] = payload.unit
            order, material = orders_public.update_item(uow.session, order_id, item_id, **kwargs)
            if material:
                audit_public.record_event(
                    uow.session,
                    actor_id=str(user.id),
                    entity_type="order",
                    entity_id=str(order.id),
                    action="update_item",
                    reason_code="ORDER_UPDATE_ITEM",
                    details=f"item_id={item_id}",
                )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.delete("/orders/{order_id}/items/{item_id}", response_model=OrderResponse)
def delete_item(
    order_id: int,
    item_id: int,
    expected_version: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            order = orders_public.remove_item(
                uow.session, order_id, item_id, expected_version=expected_version
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="order",
                entity_id=str(order.id),
                action="remove_item",
                reason_code="ORDER_REMOVE_ITEM",
                details=f"item_id={item_id}",
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.post("/orders/{order_id}/items/{item_id}/bind-product", response_model=OrderResponse)
def bind_commitment_product(
    order_id: int,
    item_id: int,
    payload: BindProductBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            issued = issued_qty_for_order_item(uow.session, order_id, item_id)
            order = orders_public.bind_commitment_product(
                uow.session,
                order_id,
                item_id,
                payload.product_id,
                actor=str(user.id),
                expected_version=payload.expected_version,
                issued_qty=issued,
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.post("/orders/{order_id}/confirm", response_model=OrderResponse)
def confirm_order(
    order_id: int,
    payload: VersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            order = orders_public.confirm_order(
                uow.session, order_id, expected_version=payload.expected_version
            )
            summary = orders_public.commitment_line_summary(order)
            audit_details = None
            reason = "ORDER_CONFIRM"
            if summary["has_commitment_lines"]:
                reason = "ORDER_CONFIRM_WITH_COMMITMENT"
                import json as _json

                audit_details = _json.dumps(
                    {
                        "commitment_count": summary["commitment_count"],
                        "product_count": summary["product_count"],
                        "total_items": summary["total_items"],
                        "commitment_item_ids": summary["commitment_item_ids"],
                        "note": (
                            "Confirmação consciente: ordem inclui linhas COMMITMENT "
                            "sem Product resolvido (RUX-3B / V2-b)"
                        ),
                    },
                    ensure_ascii=False,
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="order",
                entity_id=str(order.id),
                action="confirm",
                reason_code=reason,
                details=audit_details,
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    payload: CancelBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Peek status for permission
    try:
        current = orders_public.get_order(db, order_id)
    except OrdersError as e:
        raise _map_error(e) from e
    if current.status == "CONFIRMED":
        enforce_permission(user, "orders:cancel")
        require_reason = True
    else:
        enforce_permission(user, "orders:write")
        require_reason = False
    try:
        with UnitOfWork(db) as uow:
            order = orders_public.cancel_order(
                uow.session,
                order_id,
                expected_version=payload.expected_version,
                reason_code=payload.reason_code,
                require_reason=require_reason,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="order",
                entity_id=str(order.id),
                action="cancel",
                reason_code=payload.reason_code or "ORDER_CANCEL",
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return _order_response(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e


@router.get("/orders/{order_id}/payment-schedule", response_model=ScheduleView)
def get_payment_schedule(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:read")
    try:
        order = orders_public.get_order(db, order_id)
        return orders_public.payment_schedule_view(db, order)
    except OrdersError as e:
        raise _map_error(e) from e


@router.put("/orders/{order_id}/payment-schedule", response_model=ScheduleView)
def put_payment_schedule(
    order_id: int,
    payload: ScheduleReplace,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "orders:write")
    try:
        with UnitOfWork(db) as uow:
            order = orders_public.set_payment_schedule(
                uow.session,
                order_id,
                expected_version=payload.expected_version,
                actor=str(user.id),
                mode=payload.mode,
                lines=[line.model_dump() for line in payload.lines],
                reason_code=payload.reason_code,
            )
            uow.commit()
            order = orders_public.get_order(uow.session, order.id)
            return orders_public.payment_schedule_view(uow.session, order)
    except (OrdersError, CatalogError) as e:
        raise _map_error(e) from e
