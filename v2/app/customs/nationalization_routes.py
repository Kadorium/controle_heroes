"""Customs nationalization HTTP routes — I5-4."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.customs import public as customs_public
from app.customs.errors import CustomsError
from app.customs.models import Nationalization, NationalizationItem
from app.customs.queries import dec_str
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork

router = APIRouter(tags=["customs-nationalization"])


def _map_error(exc: CustomsError) -> AppError:
    code = getattr(exc, "code", "customs_error")
    status = 400
    if code in ("process_not_found", "nationalization_not_found"):
        status = 404
    elif code in (
        "conflict",
        "nationalization_immutable",
        "process_immutable",
        "over_nationalization",
        "process_already_cleared",
        "process_not_submitted",
    ):
        status = 409
    elif code in (
        "validation_error",
        "invalid_decimal",
        "invalid_quantity",
        "empty_items",
        "missing_source",
        "doganale_line_not_found",
        "invoice_item_not_allocated",
        "shipment_item_not_allocated",
        "product_not_found",
        "text_too_long",
    ):
        status = 422
    return AppError(exc.message, code=code, status_code=status)


class NatItemIn(BaseModel):
    quantity: str
    doganale_line_id: int | None = None
    invoice_item_id: int | None = None
    shipment_item_id: int | None = None
    product_id: int | None = None
    notes: str | None = None


class NatItemOut(BaseModel):
    id: int
    doganale_line_id: int | None
    invoice_item_id: int | None
    shipment_item_id: int | None
    product_id: int | None
    quantity: str
    notes: str | None


class NatCreate(BaseModel):
    reference: str | None = None
    notes: str | None = None


class NatAddItems(BaseModel):
    expected_version: int
    items: list[NatItemIn]


class NatVersionBody(BaseModel):
    expected_version: int


class NatOut(BaseModel):
    id: int
    process_id: int
    reference: str | None
    status: str
    version: int
    notes: str | None
    confirmed_at: datetime | None
    reversed_at: datetime | None
    created_at: datetime | None
    items: list[NatItemOut]


class ClearanceResidualOut(BaseModel):
    source_kind: str
    shipment_item_id: int | None = None
    invoice_item_id: int | None = None
    allocated_qty: str
    nationalized_qty: str
    residual_qty: str
    product_id: int | None = None
    product_sku: str | None = None
    product_name: str | None = None
    shipped_qty: str | None = None


def _item_out(it: NationalizationItem) -> NatItemOut:
    return NatItemOut(
        id=it.id,
        doganale_line_id=it.doganale_line_id,
        invoice_item_id=it.invoice_item_id,
        shipment_item_id=it.shipment_item_id,
        product_id=it.product_id,
        quantity=dec_str(it.quantity) or "0",
        notes=it.notes,
    )


def _nat_out(n: Nationalization) -> NatOut:
    return NatOut(
        id=n.id,
        process_id=n.process_id,
        reference=n.reference,
        status=n.status,
        version=n.version,
        notes=n.notes,
        confirmed_at=n.confirmed_at,
        reversed_at=n.reversed_at,
        created_at=n.created_at,
        items=[_item_out(i) for i in (n.items or [])],
    )


@router.get(
    "/import-processes/{process_id}/nationalizations",
    response_model=list[NatOut],
)
def api_list_nationalizations(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        rows = customs_public.list_nationalizations(db, process_id)
        return [_nat_out(n) for n in rows]
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/nationalizations",
    response_model=NatOut,
    status_code=201,
)
def api_create_nationalization(
    process_id: int,
    body: NatCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            nat = customs_public.create_nationalization(
                uow.session,
                process_id,
                reference=body.reference,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="nationalization",
                entity_id=str(nat.id),
                action="nationalization.create",
            )
            uow.commit()
            return _nat_out(customs_public.get_nationalization(uow.session, nat.id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/nationalizations/{nat_id}",
    response_model=NatOut,
)
def api_get_nationalization(
    process_id: int,
    nat_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        nat = customs_public.get_nationalization(db, nat_id)
        if nat.process_id != process_id:
            raise AppError("Nationalization não pertence ao processo", code="not_found", status_code=404)
        return _nat_out(nat)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/nationalizations/{nat_id}/items",
    response_model=NatOut,
)
def api_add_nat_items(
    process_id: int,
    nat_id: int,
    body: NatAddItems,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            nat = customs_public.get_nationalization(uow.session, nat_id)
            if nat.process_id != process_id:
                raise AppError(
                    "Nationalization não pertence ao processo",
                    code="not_found",
                    status_code=404,
                )
            nat = customs_public.add_nationalization_items(
                uow.session,
                nat_id,
                expected_version=body.expected_version,
                items=[i.model_dump() for i in body.items],
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="nationalization",
                entity_id=str(nat_id),
                action="nationalization.add_items",
            )
            uow.commit()
            return _nat_out(customs_public.get_nationalization(uow.session, nat.id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/nationalizations/{nat_id}/confirm",
    response_model=NatOut,
)
def api_confirm_nationalization(
    process_id: int,
    nat_id: int,
    body: NatVersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:clear")
    try:
        with UnitOfWork(db) as uow:
            nat = customs_public.get_nationalization(uow.session, nat_id)
            if nat.process_id != process_id:
                raise AppError(
                    "Nationalization não pertence ao processo",
                    code="not_found",
                    status_code=404,
                )
            nat = customs_public.confirm_nationalization(
                uow.session, nat_id, expected_version=body.expected_version
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="nationalization",
                entity_id=str(nat_id),
                action="nationalization.confirm",
            )
            uow.commit()
            return _nat_out(customs_public.get_nationalization(uow.session, nat.id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/nationalizations/{nat_id}/reverse",
    response_model=NatOut,
)
def api_reverse_nationalization(
    process_id: int,
    nat_id: int,
    body: NatVersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            nat = customs_public.get_nationalization(uow.session, nat_id)
            if nat.process_id != process_id:
                raise AppError(
                    "Nationalization não pertence ao processo",
                    code="not_found",
                    status_code=404,
                )
            nat = customs_public.reverse_nationalization(
                uow.session, nat_id, expected_version=body.expected_version
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="nationalization",
                entity_id=str(nat_id),
                action="nationalization.reverse",
            )
            uow.commit()
            return _nat_out(customs_public.get_nationalization(uow.session, nat.id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/clearance-residuals",
    response_model=list[ClearanceResidualOut],
)
def api_clearance_residuals(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        rows = customs_public.clearance_residuals(db, process_id)
        return [ClearanceResidualOut(**r) for r in rows]
    except CustomsError as exc:
        raise _map_error(exc) from exc
