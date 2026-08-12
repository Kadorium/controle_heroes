from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.documents import public as documents_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
from app.treasury import public as treasury_public
from app.treasury.commands import money2
from app.treasury.errors import TreasuryError

router = APIRouter(tags=["treasury"])


def decimal_str(value) -> str | None:
    if value is None:
        return None
    return format(value, "f")


class PaymentCreate(BaseModel):
    supplier_id: int
    amount: str
    currency: str = "EUR"
    payment_date: date
    external_reference: str | None = None
    idempotency_key: str | None = None
    register_without_document: bool = False
    reason_code: str | None = None
    order_id: int | None = None


class AllocationLine(BaseModel):
    payable_id: int
    amount: str
    expected_version: int


class AllocateBody(BaseModel):
    expected_version: int
    idempotency_key: str
    allocations: list[AllocationLine]


class CancelBody(BaseModel):
    expected_version: int
    reason_code: str | None = None


class AllocationResponse(BaseModel):
    id: int
    payable_id: int
    amount: str
    batch_id: int
    created_at: datetime | None = None


class DocumentBrief(BaseModel):
    id: int
    original_filename: str


class PaymentResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str | None = None
    order_id: int | None = None
    amount: str
    currency: str
    payment_date: date
    external_reference: str | None
    status: str
    created_by_actor_id: str
    version: int
    idempotency_key: str | None = None
    register_without_document: bool = False
    amount_allocated: str
    amount_unallocated: str
    allocations: list[AllocationResponse] = Field(default_factory=list)
    documents: list[DocumentBrief] = Field(default_factory=list)
    cancelled_at: datetime | None = None
    cancel_reason_code: str | None = None


class AdvanceCreate(BaseModel):
    amount: str
    payment_date: date
    execution_date: date
    rate: str | None = None
    brl_amount: str | None = None
    currency: str | None = None
    external_reference: str | None = None
    idempotency_key: str | None = None
    register_without_fx_document: bool = True
    reason_code: str | None = None


class AdvanceItemResponse(BaseModel):
    payment_id: int
    amount: str
    currency: str
    payment_date: str
    external_reference: str | None = None
    status: str
    version: int = 1
    fx_execution_id: int | None = None
    foreign_amount: str | None = None
    brl_amount: str | None = None
    rate: str | None = None
    execution_date: str | None = None
    amount_unallocated: str | None = None
    fx_documents: list[DocumentBrief] = Field(default_factory=list)


class AdvanceCancelBody(BaseModel):
    expected_version: int
    reason: str



class AdvanceConsolidated(BaseModel):
    total_eur: str
    total_brl: str
    weighted_avg_rate: str | None = None
    count: int


class AdvanceListResponse(BaseModel):
    order_id: int
    order_code: str
    currency: str
    advances: list[AdvanceItemResponse]
    consolidated: AdvanceConsolidated


class AdvanceRegisterResponse(BaseModel):
    payment_id: int
    order_id: int
    amount: str
    currency: str
    payment_date: date
    fx_execution_id: int
    foreign_amount: str
    brl_amount: str
    rate: str
    execution_date: date
    fx_documents: list[DocumentBrief] = Field(default_factory=list)


class EligiblePayable(BaseModel):
    id: int
    invoice_id: int
    invoice_number: str | None = None
    order_id: int
    order_code: str | None = None
    sequence: int
    due_date: date
    amount: str
    balance: str
    allocated_amount: str
    currency: str
    status: str
    version: int


def _map_error(exc: TreasuryError | billing_public.BillingError) -> AppError:
    code = getattr(exc, "code", "treasury_error")
    status = 400
    if str(code).endswith("not_found"):
        status = 404
    elif code in ("conflict", "invalid_transition"):
        status = 409
    return AppError(
        getattr(exc, "message", str(exc)),
        code=code,
        status_code=status,
    )


def _supplier_name(suppliers: dict, supplier_id: int) -> str | None:
    supplier = suppliers.get(supplier_id)
    return supplier.name if supplier is not None else None


def _payment_response(db: Session, payment, *, supplier_name: str | None = None) -> PaymentResponse:
    allocated = payment.amount - treasury_public.amount_unallocated(db, payment)
    docs = [
        DocumentBrief(id=d.id, original_filename=d.original_filename)
        for d in documents_public.list_by_entity(db, "payment", str(payment.id))
    ]
    if supplier_name is None:
        bulk = catalog_public.get_suppliers_bulk(db, {payment.supplier_id})
        supplier_name = _supplier_name(bulk, payment.supplier_id)
    return PaymentResponse(
        id=payment.id,
        supplier_id=payment.supplier_id,
        supplier_name=supplier_name,
        order_id=payment.order_id,
        amount=decimal_str(payment.amount) or "0",
        currency=payment.currency,
        payment_date=payment.payment_date,
        external_reference=payment.external_reference,
        status=payment.status,
        created_by_actor_id=payment.created_by_actor_id,
        version=payment.version,
        idempotency_key=payment.idempotency_key,
        register_without_document=bool(payment.register_without_document),
        amount_allocated=decimal_str(money2(allocated)) or "0",
        amount_unallocated=decimal_str(treasury_public.amount_unallocated(db, payment)) or "0",
        allocations=[
            AllocationResponse(
                id=a.id,
                payable_id=a.payable_id,
                amount=decimal_str(a.amount) or "0",
                batch_id=a.batch_id,
                created_at=a.created_at,
            )
            for a in payment.allocations
        ],
        documents=docs,
        cancelled_at=payment.cancelled_at,
        cancel_reason_code=payment.cancel_reason_code,
    )


def _cleanup_files(paths: list[Path]) -> None:
    for p in paths:
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


@router.post("/payments", response_model=PaymentResponse)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:write")
    if payload.register_without_document:
        enforce_permission(user, "treasury:register_without_doc")
        if not (payload.reason_code or "").strip():
            raise AppError(
                "Override sem comprovante exige reason_code",
                code="validation_error",
                status_code=400,
            )
    try:
        with UnitOfWork(db) as uow:
            payment = treasury_public.register_payment(
                uow.session,
                supplier_id=payload.supplier_id,
                amount=payload.amount,
                currency=payload.currency,
                payment_date=payload.payment_date,
                created_by_actor_id=str(user.id),
                external_reference=payload.external_reference,
                idempotency_key=payload.idempotency_key,
                allow_without_document=payload.register_without_document,
                order_id=payload.order_id,
            )
            treasury_public.assert_payment_has_document(
                uow.session,
                payment,
                allow_without=payload.register_without_document,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="payment",
                entity_id=str(payment.id),
                action="register",
                reason_code=payload.reason_code or "PAYMENT_REGISTER",
                details="without_doc" if payload.register_without_document else None,
            )
            uow.commit()
            payment = treasury_public.get_payment(uow.session, payment.id)
            return _payment_response(uow.session, payment)
    except (TreasuryError, billing_public.BillingError) as e:
        raise _map_error(e) from e


@router.post("/payments/with-document", response_model=PaymentResponse)
async def create_payment_with_document(
    supplier_id: int = Form(...),
    amount: str = Form(...),
    currency: str = Form("EUR"),
    payment_date: date = Form(...),
    external_reference: str | None = Form(None),
    idempotency_key: str | None = Form(None),
    order_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:write")
    enforce_permission(user, "documents:write")
    settings = get_settings()
    content = await file.read()
    pending: list[Path] = []
    try:
        with UnitOfWork(db) as uow:
            payment = treasury_public.register_payment(
                uow.session,
                supplier_id=supplier_id,
                amount=amount,
                currency=currency,
                payment_date=payment_date,
                created_by_actor_id=str(user.id),
                external_reference=external_reference,
                idempotency_key=idempotency_key,
                allow_without_document=False,
                order_id=order_id,
            )
            doc = documents_public.store_document_tracked(
                uow.session,
                attachments_path=settings.attachments_path,
                actor_id=str(user.id),
                filename=file.filename or "comprovante.bin",
                content=content,
                mime_type=file.content_type,
                pending_files=pending,
            )
            documents_public.link_document(
                uow.session,
                document_id=doc.id,
                entity_type="payment",
                entity_id=str(payment.id),
                role="receipt",
            )
            treasury_public.assert_payment_has_document(
                uow.session, payment, allow_without=False
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="payment",
                entity_id=str(payment.id),
                action="register",
                reason_code="PAYMENT_REGISTER",
            )
            uow.commit()
            payment = treasury_public.get_payment(uow.session, payment.id)
            return _payment_response(uow.session, payment)
    except (TreasuryError, billing_public.BillingError) as e:
        _cleanup_files(pending)
        raise _map_error(e) from e
    except Exception:
        _cleanup_files(pending)
        raise


@router.get("/payments", response_model=list[PaymentResponse])
def list_payments(
    supplier_id: int | None = None,
    order_id: int | None = None,
    status: str | None = None,
    unallocated_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:read")
    rows = treasury_public.list_payments(
        db,
        supplier_id=supplier_id,
        order_id=order_id,
        status=status,
        unallocated_only=unallocated_only,
        limit=limit,
        offset=offset,
    )
    suppliers = catalog_public.get_suppliers_bulk(db, {p.supplier_id for p in rows})
    return [
        _payment_response(db, p, supplier_name=_supplier_name(suppliers, p.supplier_id))
        for p in rows
    ]


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:read")
    try:
        return _payment_response(db, treasury_public.get_payment(db, payment_id))
    except TreasuryError as e:
        raise _map_error(e) from e


@router.get("/payments/{payment_id}/eligible-payables", response_model=list[EligiblePayable])
def eligible_payables(
    payment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:read")
    try:
        payment = treasury_public.get_payment(db, payment_id)
        rows = billing_public.list_eligible_payables(
            db,
            supplier_id=payment.supplier_id,
            currency=payment.currency,
            order_id=payment.order_id,
        )
        out = []
        for p in rows:
            inv = billing_public.get_invoice(db, p.invoice_id)
            allocated = p.amount - p.balance
            out.append(
                EligiblePayable(
                    id=p.id,
                    invoice_id=p.invoice_id,
                    invoice_number=inv.invoice_number,
                    order_id=inv.order_id,
                    order_code=None,
                    sequence=p.sequence,
                    due_date=p.due_date,
                    amount=decimal_str(p.amount) or "0",
                    balance=decimal_str(p.balance) or "0",
                    allocated_amount=decimal_str(allocated) or "0",
                    currency=p.currency,
                    status=p.status,
                    version=p.version,
                )
            )
        return out
    except (TreasuryError, billing_public.BillingError) as e:
        raise _map_error(e) from e


@router.post("/payments/{payment_id}/allocations", response_model=PaymentResponse)
def allocate(
    payment_id: int,
    payload: AllocateBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:allocate")
    try:
        with UnitOfWork(db) as uow:
            payment = treasury_public.allocate_payment(
                uow.session,
                payment_id,
                expected_version=payload.expected_version,
                allocations=[a.model_dump() for a in payload.allocations],
                created_by_actor_id=str(user.id),
                batch_idempotency_key=payload.idempotency_key,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="payment",
                entity_id=str(payment.id),
                action="allocate",
                reason_code="PAYMENT_ALLOCATE",
                details=payload.idempotency_key,
            )
            uow.commit()
            return _payment_response(uow.session, treasury_public.get_payment(uow.session, payment.id))
    except (TreasuryError, billing_public.BillingError) as e:
        raise _map_error(e) from e


@router.post("/payments/{payment_id}/cancel", response_model=PaymentResponse)
def cancel_payment(
    payment_id: int,
    payload: CancelBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:cancel")
    try:
        with UnitOfWork(db) as uow:
            # Snapshot FX before/after cancel — rows preserved; void via Audit
            executions = treasury_public.fx.list_executions(uow.session, payment_id)
            payment = treasury_public.cancel_payment(
                uow.session,
                payment_id,
                expected_version=payload.expected_version,
                reason_code=payload.reason_code,
            )
            reason = (payload.reason_code or "PAYMENT_CANCEL").strip()
            _audit_payment_and_fx_void(
                uow.session,
                actor_id=str(user.id),
                payment=payment,
                reason=reason,
                executions=executions,
            )
            uow.commit()
            return _payment_response(uow.session, treasury_public.get_payment(uow.session, payment.id))
    except TreasuryError as e:
        raise _map_error(e) from e


def _audit_payment_and_fx_void(db: Session, *, actor_id: str, payment, reason: str, executions) -> None:
    """Um cancelamento = Payment CANCELLED + Audit void em cada FxExecution (sem apagar)."""
    payloads = treasury_public.advances.fx_void_audit_payloads(payment, executions, reason=reason)
    summary_parts = [
        f"order_id={payment.order_id}",
        f"payment_id={payment.id}",
        f"amount={payment.amount}",
        f"currency={payment.currency}",
        f"motivo={reason}",
    ]
    if payloads:
        first = payloads[0]
        summary_parts.extend(
            [
                f"eur={first['eur']}",
                f"brl={first['brl']}",
                f"rate={first['rate']}",
                f"fx_execution_id={first['fx_execution_id']}",
            ]
        )
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="payment",
        entity_id=str(payment.id),
        action="cancel",
        reason_code=(reason[:64] if reason else "PAYMENT_CANCEL"),
        details=";".join(summary_parts),
    )
    for p in payloads:
        audit_public.record_event(
            db,
            actor_id=actor_id,
            entity_type="fx_execution",
            entity_id=str(p["fx_execution_id"]),
            action="fx.realized.void_by_payment_cancel",
            reason_code=(reason[:64] if reason else "PAYMENT_CANCEL"),
            details=(
                f"order_id={p['order_id']};payment_id={p['payment_id']};"
                f"eur={p['eur']};brl={p['brl']};rate={p['rate']};"
                f"execution_date={p['execution_date']};motivo={p['motivo']}"
            ),
        )


def _advance_register_response(
    db: Session, payment, execution
) -> AdvanceRegisterResponse:
    fx_docs = [
        DocumentBrief(id=d.id, original_filename=d.original_filename)
        for d in documents_public.list_by_entity(db, "fx_execution", str(execution.id))
    ]
    return AdvanceRegisterResponse(
        payment_id=payment.id,
        order_id=payment.order_id,
        amount=decimal_str(payment.amount) or "0",
        currency=payment.currency,
        payment_date=payment.payment_date,
        fx_execution_id=execution.id,
        foreign_amount=decimal_str(execution.foreign_amount) or "0",
        brl_amount=decimal_str(execution.brl_amount) or "0",
        rate=decimal_str(execution.rate) or "0",
        execution_date=execution.execution_date,
        fx_documents=fx_docs,
    )


@router.get("/orders/{order_id}/advances", response_model=AdvanceListResponse)
def get_order_advances(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:read")
    try:
        raw = treasury_public.advances.list_order_advances(db, order_id)
        return AdvanceListResponse(
            order_id=raw["order_id"],
            order_code=raw["order_code"],
            currency=raw["currency"],
            advances=[
                AdvanceItemResponse(
                    payment_id=a["payment_id"],
                    amount=a["amount"],
                    currency=a["currency"],
                    payment_date=a["payment_date"],
                    external_reference=a.get("external_reference"),
                    status=a["status"],
                    version=int(a.get("version") or 1),
                    fx_execution_id=a.get("fx_execution_id"),
                    foreign_amount=a.get("foreign_amount"),
                    brl_amount=a.get("brl_amount"),
                    rate=a.get("rate"),
                    execution_date=a.get("execution_date"),
                    amount_unallocated=a.get("amount_unallocated"),
                    fx_documents=[
                        DocumentBrief(id=d["id"], original_filename=d["original_filename"])
                        for d in a.get("fx_documents") or []
                    ],
                )
                for a in raw["advances"]
            ],
            consolidated=AdvanceConsolidated(**raw["consolidated"]),
        )
    except TreasuryError as e:
        raise _map_error(e) from e


@router.post("/orders/{order_id}/advances", response_model=AdvanceRegisterResponse)
def create_order_advance(
    order_id: int,
    payload: AdvanceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:write")
    enforce_permission(user, "treasury:fx_write")
    if payload.register_without_fx_document:
        enforce_permission(user, "treasury:fx_without_document")
    try:
        with UnitOfWork(db) as uow:
            payment, execution = treasury_public.advances.register_order_advance(
                uow.session,
                order_id=order_id,
                amount=payload.amount,
                payment_date=payload.payment_date,
                execution_date=payload.execution_date,
                created_by_actor_id=str(user.id),
                rate=payload.rate,
                brl_amount=payload.brl_amount,
                currency=payload.currency,
                external_reference=payload.external_reference,
                idempotency_key=payload.idempotency_key,
                register_without_fx_document=payload.register_without_fx_document,
            )
            if not payload.register_without_fx_document:
                treasury_public.fx.assert_execution_has_document(uow.session, execution)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="payment",
                entity_id=str(payment.id),
                action="register",
                reason_code=payload.reason_code or "ORDER_ADVANCE",
                details=f"order_id={order_id}",
            )
            if payload.register_without_fx_document:
                audit_public.record_event(
                    uow.session,
                    actor_id=str(user.id),
                    entity_type="fx_execution",
                    entity_id=str(execution.id),
                    action="fx.without_document",
                    reason_code=payload.reason_code or "FX_NO_DOC",
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_execution",
                entity_id=str(execution.id),
                action="fx.realized.register",
                details=f"rate={execution.rate};order_advance={order_id}",
            )
            uow.commit()
            return _advance_register_response(
                uow.session,
                treasury_public.get_payment(uow.session, payment.id),
                execution,
            )
    except TreasuryError as e:
        raise _map_error(e) from e


@router.post("/orders/{order_id}/advances/with-document", response_model=AdvanceRegisterResponse)
async def create_order_advance_with_document(
    order_id: int,
    amount: str = Form(...),
    payment_date: date = Form(...),
    execution_date: date = Form(...),
    rate: str | None = Form(None),
    brl_amount: str | None = Form(None),
    currency: str | None = Form(None),
    external_reference: str | None = Form(None),
    idempotency_key: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:write")
    enforce_permission(user, "treasury:fx_write")
    enforce_permission(user, "documents:write")
    settings = get_settings()
    content = await file.read()
    pending: list[Path] = []
    try:
        with UnitOfWork(db) as uow:
            payment, execution = treasury_public.advances.register_order_advance(
                uow.session,
                order_id=order_id,
                amount=amount,
                payment_date=payment_date,
                execution_date=execution_date,
                created_by_actor_id=str(user.id),
                rate=rate,
                brl_amount=brl_amount,
                currency=currency,
                external_reference=external_reference,
                idempotency_key=idempotency_key,
                register_without_fx_document=False,
            )
            doc = documents_public.store_document_tracked(
                uow.session,
                attachments_path=settings.attachments_path,
                actor_id=str(user.id),
                filename=file.filename or "cambio.pdf",
                content=content,
                mime_type=file.content_type,
                pending_files=pending,
            )
            documents_public.link_document(
                uow.session,
                document_id=doc.id,
                entity_type="fx_execution",
                entity_id=str(execution.id),
                role="fx_evidence",
            )
            treasury_public.fx.assert_execution_has_document(uow.session, execution)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="payment",
                entity_id=str(payment.id),
                action="register",
                reason_code="ORDER_ADVANCE",
                details=f"order_id={order_id}",
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_execution",
                entity_id=str(execution.id),
                action="fx.realized.register",
                details=f"rate={execution.rate};order_advance={order_id}",
            )
            uow.commit()
            return _advance_register_response(
                uow.session,
                treasury_public.get_payment(uow.session, payment.id),
                execution,
            )
    except TreasuryError as e:
        _cleanup_files(pending)
        raise _map_error(e) from e
    except Exception:
        _cleanup_files(pending)
        raise


@router.post(
    "/orders/{order_id}/advances/{payment_id}/cancel",
    response_model=AdvanceListResponse,
)
def cancel_order_advance(
    order_id: int,
    payment_id: int,
    payload: AdvanceCancelBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:cancel")
    reason = (payload.reason or "").strip()
    if not reason:
        raise AppError(
            "Motivo do cancelamento é obrigatório",
            code="validation_error",
            status_code=400,
        )
    try:
        with UnitOfWork(db) as uow:
            payment, executions = treasury_public.advances.cancel_order_advance(
                uow.session,
                order_id=order_id,
                payment_id=payment_id,
                expected_version=payload.expected_version,
                reason=reason,
            )
            _audit_payment_and_fx_void(
                uow.session,
                actor_id=str(user.id),
                payment=payment,
                reason=reason,
                executions=executions,
            )
            uow.commit()
            raw = treasury_public.advances.list_order_advances(uow.session, order_id)
            return AdvanceListResponse(
                order_id=raw["order_id"],
                order_code=raw["order_code"],
                currency=raw["currency"],
                advances=[
                    AdvanceItemResponse(
                        payment_id=a["payment_id"],
                        amount=a["amount"],
                        currency=a["currency"],
                        payment_date=a["payment_date"],
                        external_reference=a.get("external_reference"),
                        status=a["status"],
                        version=int(a.get("version") or 1),
                        fx_execution_id=a.get("fx_execution_id"),
                        foreign_amount=a.get("foreign_amount"),
                        brl_amount=a.get("brl_amount"),
                        rate=a.get("rate"),
                        execution_date=a.get("execution_date"),
                        fx_documents=[
                            DocumentBrief(id=d["id"], original_filename=d["original_filename"])
                            for d in a.get("fx_documents") or []
                        ],
                    )
                    for a in raw["advances"]
                ],
                consolidated=AdvanceConsolidated(**raw["consolidated"]),
            )
    except TreasuryError as e:
        raise _map_error(e) from e
