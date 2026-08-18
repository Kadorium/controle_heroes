"""Inventory HTTP routes — I5-4."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.inventory import public as inventory_public
from app.inventory.errors import InventoryError
from app.inventory.models import GoodsReceipt

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _map_error(exc: InventoryError) -> AppError:
    code = getattr(exc, "code", "inventory_error")
    status = 400
    if code in ("location_not_found", "receipt_not_found", "process_not_found"):
        status = 404
    elif code in (
        "conflict",
        "receipt_immutable",
        "nationalization_required",
        "over_receipt",
        "insufficient_bonded",
    ):
        status = 409
    elif code in (
        "validation_error",
        "invalid_decimal",
        "invalid_quantity",
        "invalid_receipt_type",
        "invalid_movement_type",
        "location_type_mismatch",
        "empty_lines",
        "product_not_found",
        "product_mismatch",
    ):
        status = 422
    return AppError(exc.message, code=code, status_code=status)


class LocationOut(BaseModel):
    id: int
    code: str
    name: str
    location_type: str
    active: bool


class ReceiptLineIn(BaseModel):
    product_id: int
    quantity: str
    nationalization_item_id: int | None = None
    shipment_item_id: int | None = None
    notes: str | None = None


class ReceiptLineOut(BaseModel):
    id: int
    product_id: int
    quantity: str
    nationalization_item_id: int | None
    shipment_item_id: int | None
    notes: str | None


class ReceiptCreate(BaseModel):
    location_id: int | None = None
    location_code: str | None = None
    from_location_code: str | None = None
    process_id: int | None = None
    nationalization_id: int | None = None
    receipt_type: str
    document_id: int | None = None
    notes: str | None = None


class ReceiptAddLines(BaseModel):
    expected_version: int
    lines: list[ReceiptLineIn]


class ReceiptVersionBody(BaseModel):
    expected_version: int
    reason: str | None = None


class ReceiptOut(BaseModel):
    id: int
    location_id: int
    location_code: str | None = None
    location_type: str | None = None
    process_id: int | None
    nationalization_id: int | None
    receipt_type: str
    status: str
    version: int
    document_id: int | None
    notes: str | None
    received_at: datetime | None
    created_at: datetime | None
    lines: list[ReceiptLineOut]


class MovementOut(BaseModel):
    id: int
    location_id: int
    location_code: str | None = None
    location_type: str | None = None
    location_name: str | None = None
    product_id: int
    product_sku: str | None = None
    product_description: str | None = None
    quantity_delta: str
    movement_type: str
    receipt_line_id: int | None
    nationalization_item_id: int | None
    reversal_of_id: int | None
    reason: str | None
    created_at: datetime | None


class BalanceOut(BaseModel):
    location_id: int
    location_code: str | None = None
    location_type: str | None = None
    product_id: int
    qty: str


class AdjustmentIn(BaseModel):
    location_code: str
    product_id: int
    quantity_delta: str
    movement_type: str = "ADJUSTMENT"
    reason: str | None = None


class SkuPositionOut(BaseModel):
    product_id: int
    available_qty: str
    bonded_qty: str
    quarantine_qty: str
    cleared_not_received_qty: str
    in_clearance_qty: str
    in_transit_qty: str
    future_order_qty: str | None
    future_order_qty_note: str | None = None
    etas: list[dict[str, Any]] = []
    balances: list[dict[str, Any]] = []


class ReceiptResidualOut(BaseModel):
    nationalization_id: int
    nationalization_item_id: int
    product_id: int | None
    product_sku: str | None
    product_name: str | None
    nationalized_qty: str
    received_qty: str
    residual_qty: str


def _receipt_out(r: GoodsReceipt) -> ReceiptOut:
    return ReceiptOut(
        id=r.id,
        location_id=r.location_id,
        location_code=r.location.code if r.location else None,
        location_type=r.location.location_type if r.location else None,
        process_id=r.process_id,
        nationalization_id=r.nationalization_id,
        receipt_type=r.receipt_type,
        status=r.status,
        version=r.version,
        document_id=r.document_id,
        notes=r.notes,
        received_at=r.received_at,
        created_at=r.created_at,
        lines=[
            ReceiptLineOut(
                id=ln.id,
                product_id=ln.product_id,
                quantity=str(ln.quantity),
                nationalization_item_id=ln.nationalization_item_id,
                shipment_item_id=ln.shipment_item_id,
                notes=ln.notes,
            )
            for ln in (r.lines or [])
        ],
    )


@router.get("/locations", response_model=list[LocationOut])
def api_list_locations(db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "inventory:read")
    locs = inventory_public.list_locations(db)
    return [
        LocationOut(
            id=loc.id,
            code=loc.code,
            name=loc.name,
            location_type=loc.location_type,
            active=loc.active,
        )
        for loc in locs
    ]


@router.get(
    "/processes/{process_id}/receipt-residuals",
    response_model=list[ReceiptResidualOut],
)
def api_list_receipt_residuals(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:read")
    try:
        rows = inventory_public.list_receipt_residuals(db, process_id)
        return [ReceiptResidualOut(**r) for r in rows]
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.post("/receipts", response_model=ReceiptOut, status_code=201)
def api_create_receipt(
    body: ReceiptCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:write")
    try:
        with UnitOfWork(db) as uow:
            r = inventory_public.create_receipt(
                uow.session,
                location_id=body.location_id,
                location_code=body.location_code,
                from_location_code=body.from_location_code,
                process_id=body.process_id,
                nationalization_id=body.nationalization_id,
                receipt_type=body.receipt_type,
                document_id=body.document_id,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="goods_receipt",
                entity_id=str(r.id),
                action="goods_receipt.create",
            )
            uow.commit()
            return _receipt_out(inventory_public.get_receipt(uow.session, r.id))
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.get("/receipts", response_model=list[ReceiptOut])
def api_list_receipts(
    process_id: int | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:read")
    rows = inventory_public.list_receipts(
        db, process_id=process_id, status=status, limit=limit
    )
    return [_receipt_out(r) for r in rows]


@router.get("/receipts/{receipt_id}", response_model=ReceiptOut)
def api_get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:read")
    try:
        return _receipt_out(inventory_public.get_receipt(db, receipt_id))
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.post("/receipts/{receipt_id}/lines", response_model=ReceiptOut)
def api_add_receipt_lines(
    receipt_id: int,
    body: ReceiptAddLines,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:write")
    try:
        with UnitOfWork(db) as uow:
            r = inventory_public.add_receipt_lines(
                uow.session,
                receipt_id,
                expected_version=body.expected_version,
                lines=[ln.model_dump() for ln in body.lines],
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="goods_receipt",
                entity_id=str(receipt_id),
                action="goods_receipt.add_lines",
            )
            uow.commit()
            return _receipt_out(inventory_public.get_receipt(uow.session, r.id))
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.post("/receipts/{receipt_id}/confirm", response_model=ReceiptOut)
def api_confirm_receipt(
    receipt_id: int,
    body: ReceiptVersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:write")
    try:
        with UnitOfWork(db) as uow:
            r = inventory_public.confirm_receipt(
                uow.session, receipt_id, expected_version=body.expected_version
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="goods_receipt",
                entity_id=str(receipt_id),
                action="goods_receipt.confirm",
            )
            uow.commit()
            return _receipt_out(inventory_public.get_receipt(uow.session, r.id))
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.post("/receipts/{receipt_id}/reverse", response_model=ReceiptOut)
def api_reverse_receipt(
    receipt_id: int,
    body: ReceiptVersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:write")
    try:
        with UnitOfWork(db) as uow:
            r = inventory_public.reverse_receipt(
                uow.session,
                receipt_id,
                expected_version=body.expected_version,
                reason=body.reason,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="goods_receipt",
                entity_id=str(receipt_id),
                action="goods_receipt.reverse",
            )
            uow.commit()
            return _receipt_out(inventory_public.get_receipt(uow.session, r.id))
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.get("/movements", response_model=list[MovementOut])
def api_list_movements(
    product_id: int | None = None,
    location_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:read")
    rows = inventory_public.list_movements(
        db, product_id=product_id, location_id=location_id, limit=limit
    )
    return [MovementOut(**r) for r in rows]


@router.get("/balances", response_model=BalanceOut)
def api_get_balance(
    product_id: int,
    location_id: int | None = None,
    location_code: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:read")
    try:
        return BalanceOut(
            **inventory_public.get_stock_balance(
                db,
                location_id=location_id,
                location_code=location_code,
                product_id=product_id,
            )
        )
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.get("/sku/{product_id}/position", response_model=SkuPositionOut)
def api_sku_position(
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:read")
    try:
        return SkuPositionOut(**inventory_public.get_sku_position(db, product_id))
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.post("/adjustments", response_model=MovementOut, status_code=201)
def api_adjustment(
    body: AdjustmentIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:adjust")
    try:
        with UnitOfWork(db) as uow:
            mov = inventory_public.record_adjustment(
                uow.session,
                location_code=body.location_code,
                product_id=body.product_id,
                quantity_delta=body.quantity_delta,
                movement_type=body.movement_type,
                reason=body.reason,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="inventory_movement",
                entity_id=str(mov.id),
                action="inventory.adjustment",
            )
            uow.commit()
            return MovementOut(
                id=mov.id,
                location_id=mov.location_id,
                product_id=mov.product_id,
                quantity_delta=str(mov.quantity_delta),
                movement_type=mov.movement_type,
                receipt_line_id=mov.receipt_line_id,
                nationalization_item_id=mov.nationalization_item_id,
                reversal_of_id=mov.reversal_of_id,
                reason=mov.reason,
                created_at=mov.created_at,
            )
    except InventoryError as exc:
        raise _map_error(exc) from exc


@router.post("/rebuild-balances")
def api_rebuild_balances(
    product_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "inventory:adjust")
    try:
        with UnitOfWork(db) as uow:
            count = inventory_public.rebuild_stock_balances(
                uow.session, product_id=product_id
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="stock_balance",
                entity_id=str(product_id or "all"),
                action="stock_balance.rebuild",
            )
            uow.commit()
            return {"rebuilt_rows": count}
    except InventoryError as exc:
        raise _map_error(exc) from exc
