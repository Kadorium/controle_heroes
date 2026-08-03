"""Customs commands — I5-1 ImportProcess. Caller owns UoW."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.customs import repository as repo
from app.customs.errors import (
    OverAllocationError,
    ProcessConflict,
    ProcessImmutable,
    ProcessNotDraft,
    ProcessNotFound,
    ProcessValidationError,
)
from app.customs.models import (
    ImportProcess,
    ImportProcessInvoice,
    ImportProcessInvoiceItem,
    ImportProcessShipment,
    ImportProcessShipmentItem,
)
from app.logistics import public as logistics_public


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dec(value: str | Decimal) -> Decimal:
    return Decimal(str(value))


def _require(db: Session, process_id: int) -> ImportProcess:
    p = repo.get_process_for_update(db, process_id)
    if not p:
        raise ProcessNotFound(process_id)
    return p


def _check_version(process: ImportProcess, expected_version: int) -> None:
    if process.version != expected_version:
        raise ProcessConflict()


def _bump(process: ImportProcess) -> None:
    process.version += 1


def _assert_draft_mutable(process: ImportProcess) -> None:
    if process.status == "CANCELLED":
        raise ProcessImmutable("Processo cancelado")
    if process.status != "DRAFT":
        raise ProcessNotDraft()


def _gen_code() -> str:
    return f"IMP-{uuid.uuid4().hex[:12].upper()}"


def create_import_process(
    db: Session,
    *,
    external_reference: str | None = None,
    notes: str | None = None,
) -> ImportProcess:
    code = _gen_code()
    while repo.get_by_code(db, code):
        code = _gen_code()
    process = ImportProcess(
        code=code,
        external_reference=(external_reference or "").strip() or None,
        status="DRAFT",
        version=1,
        notes=(notes or "").strip() or None,
    )
    db.add(process)
    db.flush()
    return process


def update_import_process(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    external_reference: str | None = None,
    notes: str | None = None,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)
    if external_reference is not None:
        process.external_reference = external_reference.strip() or None
    if notes is not None:
        process.notes = notes.strip() or None
    _bump(process)
    db.flush()
    return process


def link_invoice(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    invoice_id: int,
    notes: str | None = None,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    existing = repo.find_invoice_link(db, invoice_id)
    if existing:
        if existing.process_id == process_id:
            raise ProcessValidationError("Invoice já vinculada a este processo", code="already_linked")
        raise ProcessValidationError(
            "Invoice já vinculada a outro ImportProcess",
            code="invoice_already_linked",
        )

    try:
        inv = billing_public.get_invoice(db, invoice_id)
    except billing_public.BillingError as exc:
        code = getattr(exc, "code", "invoice_error")
        if code == "invoice_not_found":
            raise ProcessValidationError(str(exc), code="invoice_not_found") from exc
        raise ProcessValidationError(str(exc), code="invoice_error") from exc

    if inv.status != "ISSUED":
        raise ProcessValidationError(
            "Somente Invoice ISSUED pode ser vinculada",
            code="invoice_not_issued",
        )

    db.add(
        ImportProcessInvoice(
            process_id=process.id,
            invoice_id=invoice_id,
            notes=(notes or "").strip() or None,
        )
    )
    _bump(process)
    db.flush()
    return process


def unlink_invoice(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    invoice_id: int,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    link = next((x for x in process.invoices if x.invoice_id == invoice_id), None)
    if not link:
        raise ProcessValidationError("Invoice não vinculada a este processo", code="not_linked")

    # remove item allocations for items belonging to this invoice
    inv = billing_public.get_invoice(db, invoice_id)
    item_ids = {it.id for it in inv.items}
    for alloc in list(process.invoice_items):
        if alloc.invoice_item_id in item_ids:
            db.delete(alloc)

    db.delete(link)
    _bump(process)
    db.flush()
    return process


def allocate_invoice_item(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    invoice_item_id: int,
    allocated_qty: str | Decimal,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    qty = _dec(allocated_qty)
    if qty <= 0:
        raise ProcessValidationError("allocated_qty deve ser > 0", code="invalid_qty")

    inv_item = None
    parent_invoice_id = None
    linked_invoice_ids = {x.invoice_id for x in process.invoices}
    for invoice_id in linked_invoice_ids:
        inv = billing_public.get_invoice(db, invoice_id)
        for it in inv.items:
            if it.id == invoice_item_id:
                inv_item = it
                parent_invoice_id = invoice_id
                break
        if inv_item:
            break

    if not inv_item or parent_invoice_id not in linked_invoice_ids:
        raise ProcessValidationError(
            "InvoiceItem deve pertencer a uma Invoice vinculada ao processo",
            code="invoice_item_not_in_process",
        )

    item_qty = Decimal(str(inv_item.quantity))
    existing = repo.get_invoice_item_alloc(db, process.id, invoice_item_id)
    current_other = repo.sum_allocated_invoice_item(db, invoice_item_id)
    if existing:
        current_other -= existing.allocated_qty

    if current_other + qty > item_qty:
        raise OverAllocationError(
            f"Alocação {qty} excede residual {item_qty - current_other} do InvoiceItem"
        )

    if existing:
        existing.allocated_qty = qty
    else:
        db.add(
            ImportProcessInvoiceItem(
                process_id=process.id,
                invoice_item_id=invoice_item_id,
                allocated_qty=qty,
            )
        )
    _bump(process)
    db.flush()
    return process


def deallocate_invoice_item(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    invoice_item_id: int,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    existing = repo.get_invoice_item_alloc(db, process.id, invoice_item_id)
    if not existing:
        raise ProcessValidationError("Alocação de InvoiceItem não encontrada", code="not_allocated")
    db.delete(existing)
    _bump(process)
    db.flush()
    return process


def link_shipment(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    shipment_id: int,
    notes: str | None = None,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    existing = repo.find_shipment_link(db, shipment_id)
    if existing:
        if existing.process_id == process_id:
            raise ProcessValidationError("Shipment já vinculado a este processo", code="already_linked")
        raise ProcessValidationError(
            "Shipment já vinculado a outro ImportProcess",
            code="shipment_already_linked",
        )

    try:
        logistics_public.get_shipment(db, shipment_id)
    except logistics_public.LogisticsError as exc:
        code = getattr(exc, "code", "shipment_error")
        if code == "shipment_not_found":
            raise ProcessValidationError(str(exc), code="shipment_not_found") from exc
        raise ProcessValidationError(str(exc), code="shipment_error") from exc

    db.add(
        ImportProcessShipment(
            process_id=process.id,
            shipment_id=shipment_id,
            notes=(notes or "").strip() or None,
        )
    )
    _bump(process)
    db.flush()
    return process


def unlink_shipment(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    shipment_id: int,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    link = next((x for x in process.shipments if x.shipment_id == shipment_id), None)
    if not link:
        raise ProcessValidationError("Shipment não vinculado a este processo", code="not_linked")

    shipment = logistics_public.get_shipment(db, shipment_id)
    item_ids = {it.id for it in shipment.items}
    for alloc in list(process.shipment_items):
        if alloc.shipment_item_id in item_ids:
            db.delete(alloc)

    db.delete(link)
    _bump(process)
    db.flush()
    return process


def allocate_shipment_item(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    shipment_item_id: int,
    allocated_qty: str | Decimal,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    qty = _dec(allocated_qty)
    if qty <= 0:
        raise ProcessValidationError("allocated_qty deve ser > 0", code="invalid_qty")

    ship_item = None
    linked_shipment_ids = {x.shipment_id for x in process.shipments}
    for shipment_id in linked_shipment_ids:
        shipment = logistics_public.get_shipment(db, shipment_id)
        for it in shipment.items:
            if it.id == shipment_item_id:
                ship_item = it
                break
        if ship_item:
            break

    if not ship_item:
        raise ProcessValidationError(
            "ShipmentItem deve pertencer a um Shipment vinculado ao processo",
            code="shipment_item_not_in_process",
        )

    shipped_qty = Decimal(str(ship_item.quantity))
    existing = repo.get_shipment_item_alloc(db, process.id, shipment_item_id)
    current_other = repo.sum_allocated_shipment_item(db, shipment_item_id)
    if existing:
        current_other -= existing.allocated_qty

    if current_other + qty > shipped_qty:
        raise OverAllocationError(
            f"Alocação {qty} excede residual {shipped_qty - current_other} do ShipmentItem"
        )

    if existing:
        existing.allocated_qty = qty
    else:
        db.add(
            ImportProcessShipmentItem(
                process_id=process.id,
                shipment_item_id=shipment_item_id,
                allocated_qty=qty,
            )
        )
    _bump(process)
    db.flush()
    return process


def deallocate_shipment_item(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    shipment_item_id: int,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    _assert_draft_mutable(process)

    existing = repo.get_shipment_item_alloc(db, process.id, shipment_item_id)
    if not existing:
        raise ProcessValidationError("Alocação de ShipmentItem não encontrada", code="not_allocated")
    db.delete(existing)
    _bump(process)
    db.flush()
    return process


def submit_import_process(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    if process.status == "CANCELLED":
        raise ProcessImmutable("Processo cancelado")
    if process.status == "SUBMITTED":
        raise ProcessValidationError("Processo já submetido", code="already_submitted")
    if process.status != "DRAFT":
        raise ProcessNotDraft()

    if not (process.external_reference or "").strip():
        raise ProcessValidationError(
            "external_reference (DUIMP/ref) obrigatória para submeter",
            code="external_reference_required",
        )
    if not process.invoices:
        raise ProcessValidationError(
            "Vincule ao menos uma Invoice ISSUED antes de submeter",
            code="invoice_required",
        )

    process.status = "SUBMITTED"
    process.submitted_at = _now()
    _bump(process)
    db.flush()
    return process


def cancel_import_process(
    db: Session,
    process_id: int,
    *,
    expected_version: int,
    reason: str,
) -> ImportProcess:
    process = _require(db, process_id)
    _check_version(process, expected_version)
    if process.status == "CANCELLED":
        raise ProcessValidationError("Processo já cancelado", code="already_cancelled")
    if process.status not in ("DRAFT", "SUBMITTED"):
        raise ProcessImmutable("Status não permite cancelamento neste checkpoint")

    text = (reason or "").strip()
    if not text:
        raise ProcessValidationError("Motivo de cancelamento obrigatório", code="reason_required")

    process.status = "CANCELLED"
    process.cancelled_at = _now()
    process.cancel_reason = text
    _bump(process)
    db.flush()
    return process
