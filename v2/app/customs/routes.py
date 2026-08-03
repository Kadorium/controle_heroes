"""HTTP Customs — /api/import-processes (I5-1)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.customs import public as customs_public
from app.customs.errors import CustomsError
from app.customs.models import ImportProcess
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork

router = APIRouter(tags=["customs"])


def _map_error(exc: CustomsError) -> AppError:
    code = getattr(exc, "code", "customs_error")
    status = 400
    if code == "process_not_found":
        status = 404
    elif code in ("conflict", "over_allocation", "already_linked", "invoice_already_linked", "shipment_already_linked"):
        status = 409
    elif code in (
        "process_not_draft",
        "process_immutable",
        "already_submitted",
        "already_cancelled",
    ):
        status = 409
    elif code in (
        "invoice_not_issued",
        "invoice_not_found",
        "shipment_not_found",
        "invoice_item_not_in_process",
        "shipment_item_not_in_process",
        "invalid_qty",
        "external_reference_required",
        "invoice_required",
        "reason_required",
        "not_linked",
        "not_allocated",
        "validation_error",
    ):
        status = 422
    return AppError(exc.message, code=code, status_code=status)


class ProcessCreate(BaseModel):
    external_reference: str | None = None
    notes: str | None = None


class ProcessUpdate(BaseModel):
    expected_version: int
    external_reference: str | None = None
    notes: str | None = None


class VersionBody(BaseModel):
    expected_version: int


class LinkInvoiceBody(BaseModel):
    expected_version: int
    invoice_id: int
    notes: str | None = None


class UnlinkInvoiceBody(BaseModel):
    expected_version: int
    invoice_id: int


class AllocInvoiceItemBody(BaseModel):
    expected_version: int
    invoice_item_id: int
    allocated_qty: str


class DeallocInvoiceItemBody(BaseModel):
    expected_version: int
    invoice_item_id: int


class LinkShipmentBody(BaseModel):
    expected_version: int
    shipment_id: int
    notes: str | None = None


class UnlinkShipmentBody(BaseModel):
    expected_version: int
    shipment_id: int


class AllocShipmentItemBody(BaseModel):
    expected_version: int
    shipment_item_id: int
    allocated_qty: str


class DeallocShipmentItemBody(BaseModel):
    expected_version: int
    shipment_item_id: int


class CancelBody(BaseModel):
    expected_version: int
    reason: str = Field(min_length=1)


class InvoiceLinkOut(BaseModel):
    id: int
    invoice_id: int
    notes: str | None
    created_at: datetime | None


class InvoiceItemAllocOut(BaseModel):
    id: int
    invoice_item_id: int
    allocated_qty: str


class ShipmentLinkOut(BaseModel):
    id: int
    shipment_id: int
    notes: str | None
    created_at: datetime | None


class ShipmentItemAllocOut(BaseModel):
    id: int
    shipment_item_id: int
    allocated_qty: str


class ProcessListItem(BaseModel):
    id: int
    code: str
    external_reference: str | None
    status: str
    version: int
    notes: str | None
    submitted_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    invoice_count: int
    shipment_count: int


class ProcessOut(BaseModel):
    id: int
    code: str
    external_reference: str | None
    status: str
    version: int
    notes: str | None
    submitted_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime | None
    updated_at: datetime | None
    invoices: list[InvoiceLinkOut]
    invoice_item_allocations: list[InvoiceItemAllocOut]
    shipments: list[ShipmentLinkOut]
    shipment_item_allocations: list[ShipmentItemAllocOut]


class ResidualInvoiceItemOut(BaseModel):
    invoice_id: int
    invoice_item_id: int
    product_sku: str | None
    quantity: str
    allocated_qty: str
    residual_qty: str


class ResidualShipmentItemOut(BaseModel):
    shipment_id: int
    shipment_item_id: int
    order_item_id: int
    quantity: str
    allocated_qty: str
    residual_qty: str


def _to_list_item(p: ImportProcess) -> ProcessListItem:
    return ProcessListItem(
        id=p.id,
        code=p.code,
        external_reference=p.external_reference,
        status=p.status,
        version=p.version,
        notes=p.notes,
        submitted_at=p.submitted_at,
        cancelled_at=p.cancelled_at,
        created_at=p.created_at,
        updated_at=p.updated_at,
        invoice_count=len(p.invoices) if p.invoices is not None else 0,
        shipment_count=len(p.shipments) if p.shipments is not None else 0,
    )


def _to_out(p: ImportProcess) -> ProcessOut:
    return ProcessOut(
        id=p.id,
        code=p.code,
        external_reference=p.external_reference,
        status=p.status,
        version=p.version,
        notes=p.notes,
        submitted_at=p.submitted_at,
        cancelled_at=p.cancelled_at,
        cancel_reason=p.cancel_reason,
        created_at=p.created_at,
        updated_at=p.updated_at,
        invoices=[
            InvoiceLinkOut(
                id=x.id, invoice_id=x.invoice_id, notes=x.notes, created_at=x.created_at
            )
            for x in (p.invoices or [])
        ],
        invoice_item_allocations=[
            InvoiceItemAllocOut(
                id=x.id,
                invoice_item_id=x.invoice_item_id,
                allocated_qty=str(x.allocated_qty),
            )
            for x in (p.invoice_items or [])
        ],
        shipments=[
            ShipmentLinkOut(
                id=x.id, shipment_id=x.shipment_id, notes=x.notes, created_at=x.created_at
            )
            for x in (p.shipments or [])
        ],
        shipment_item_allocations=[
            ShipmentItemAllocOut(
                id=x.id,
                shipment_item_id=x.shipment_item_id,
                allocated_qty=str(x.allocated_qty),
            )
            for x in (p.shipment_items or [])
        ],
    )


def _reload(db: Session, process_id: int) -> ImportProcess:
    return customs_public.get_import_process(db, process_id)


@router.get("/import-processes", response_model=list[ProcessListItem])
def api_list_processes(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    rows = customs_public.list_import_processes(db, status=status, limit=limit, offset=offset)
    # list_processes doesn't eager-load; load counts cheaply via get
    out: list[ProcessListItem] = []
    for p in rows:
        full = customs_public.get_import_process(db, p.id)
        out.append(_to_list_item(full))
    return out


@router.post("/import-processes", response_model=ProcessOut, status_code=201)
def api_create_process(
    body: ProcessCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            p = customs_public.create_import_process(
                uow.session,
                external_reference=body.external_reference,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(p.id),
                action="import_process.create"
            )
            uow.commit()
            full = _reload(uow.session, p.id)
            return _to_out(full)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get("/import-processes/{process_id}", response_model=ProcessOut)
def api_get_process(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return _to_out(customs_public.get_import_process(db, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.patch("/import-processes/{process_id}", response_model=ProcessOut)
def api_update_process(
    process_id: int,
    body: ProcessUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.update_import_process(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                external_reference=body.external_reference,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.update"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/invoices", response_model=ProcessOut)
def api_link_invoice(
    process_id: int,
    body: LinkInvoiceBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.link_invoice(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                invoice_id=body.invoice_id,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.link_invoice"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/invoices/unlink", response_model=ProcessOut)
def api_unlink_invoice(
    process_id: int,
    body: UnlinkInvoiceBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.unlink_invoice(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                invoice_id=body.invoice_id,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.unlink_invoice"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/invoice-items/allocate", response_model=ProcessOut)
def api_alloc_invoice_item(
    process_id: int,
    body: AllocInvoiceItemBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.allocate_invoice_item(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                invoice_item_id=body.invoice_item_id,
                allocated_qty=body.allocated_qty,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.allocate_invoice_item"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/invoice-items/deallocate", response_model=ProcessOut)
def api_dealloc_invoice_item(
    process_id: int,
    body: DeallocInvoiceItemBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.deallocate_invoice_item(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                invoice_item_id=body.invoice_item_id,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.deallocate_invoice_item"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/shipments", response_model=ProcessOut)
def api_link_shipment(
    process_id: int,
    body: LinkShipmentBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.link_shipment(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                shipment_id=body.shipment_id,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.link_shipment"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/shipments/unlink", response_model=ProcessOut)
def api_unlink_shipment(
    process_id: int,
    body: UnlinkShipmentBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.unlink_shipment(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                shipment_id=body.shipment_id,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.unlink_shipment"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/shipment-items/allocate", response_model=ProcessOut)
def api_alloc_shipment_item(
    process_id: int,
    body: AllocShipmentItemBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.allocate_shipment_item(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                shipment_item_id=body.shipment_item_id,
                allocated_qty=body.allocated_qty,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.allocate_shipment_item"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/shipment-items/deallocate", response_model=ProcessOut)
def api_dealloc_shipment_item(
    process_id: int,
    body: DeallocShipmentItemBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.deallocate_shipment_item(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                shipment_item_id=body.shipment_item_id,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.deallocate_shipment_item"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/submit", response_model=ProcessOut)
def api_submit(
    process_id: int,
    body: VersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.submit_import_process(
                uow.session, process_id, expected_version=body.expected_version
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.submit"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post("/import-processes/{process_id}/cancel", response_model=ProcessOut)
def api_cancel(
    process_id: int,
    body: CancelBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            customs_public.cancel_import_process(
                uow.session,
                process_id,
                expected_version=body.expected_version,
                reason=body.reason,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="import_process",
                entity_id=str(process_id),
                action="import_process.cancel"
            )
            uow.commit()
            return _to_out(_reload(uow.session, process_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/residuals/invoice-items",
    response_model=list[ResidualInvoiceItemOut],
)
def api_invoice_residuals(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return customs_public.invoice_item_residuals(db, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/residuals/shipment-items",
    response_model=list[ResidualShipmentItemOut],
)
def api_shipment_residuals(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return customs_public.shipment_item_residuals(db, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc
