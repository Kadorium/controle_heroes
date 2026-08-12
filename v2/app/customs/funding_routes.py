"""HTTP Numerário / Funding — payees + funding-requests (I5-3A)."""

from __future__ import annotations

from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.customs import public as customs_public
from app.customs.errors import CustomsError
from app.customs.models import CustomsFundingRequest, CustomsPayee
from app.customs.queries import dec_str
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork

router = APIRouter(tags=["customs-funding"])


def _map_error(exc: CustomsError) -> AppError:
    code = getattr(exc, "code", "customs_error")
    status = 400
    if code in ("process_not_found", "payee_not_found", "funding_not_found"):
        status = 404
    elif code in (
        "conflict",
        "funding_immutable",
        "process_immutable",
        "process_not_draft",
    ):
        status = 409
    elif code in (
        "validation_error",
        "invalid_decimal",
        "invalid_date",
        "invalid_currency",
        "document_not_found",
        "payee_name_required",
        "invalid_position",
        "text_too_long",
    ):
        status = 422
    return AppError(exc.message, code=code, status_code=status)

# —— Schemas ——


class PayeeIn(BaseModel):
    name: str
    tax_id: str | None = None
    bank_name: str | None = None
    agency: str | None = None
    account: str | None = None
    pix_key: str | None = None
    notes: str | None = None


class PayeeUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    bank_name: str | None = None
    agency: str | None = None
    account: str | None = None
    pix_key: str | None = None
    notes: str | None = None


class PayeeOut(BaseModel):
    id: int
    name: str
    tax_id: str | None
    bank_name: str | None
    agency: str | None
    account: str | None
    pix_key: str | None
    notes: str | None
    created_at: datetime | None


class FundingLineIn(BaseModel):
    position: int | None = None
    label: str | None = None
    code: str | None = None
    amount: str | None = None
    currency: str | None = None
    notes: str | None = None


class FundingLineOut(BaseModel):
    id: int
    position: int
    label: str | None
    code: str | None
    amount: str | None
    currency: str | None
    notes: str | None


class FundingCreate(BaseModel):
    payee_id: int
    currency: str
    declared_total: str
    reference: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    document_id: int | None = None
    notes: str | None = None
    idempotency_key: str | None = None


class FundingUpdate(BaseModel):
    expected_version: int
    payee_id: int | None = None
    reference: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    currency: str | None = None
    declared_total: str | None = None
    document_id: int | None = None
    clear_document: bool = False
    notes: str | None = None


class FundingReplaceLinesBody(BaseModel):
    expected_version: int
    lines: list[FundingLineIn]


class FundingVersionLockBody(BaseModel):
    expected_version: int


class FundingPayableLinkOut(BaseModel):
    id: int
    payable_id: int
    sequence: int
    amount: str
    currency: str


class FundingOut(BaseModel):
    id: int
    process_id: int
    payee_id: int
    payee: PayeeOut | None
    reference: str | None
    issue_date: date | None
    due_date: date | None
    currency: str
    declared_total: str
    structured_total: str
    divergence: str
    document_id: int | None
    version: int
    status: str
    notes: str | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime | None
    value_bases: list[FundingLineOut]
    tax_lines: list[FundingLineOut]
    expense_lines: list[FundingLineOut]
    payable_links: list[FundingPayableLinkOut] = []


def _payee_out(p: CustomsPayee) -> PayeeOut:
    return PayeeOut(
        id=p.id,
        name=p.name,
        tax_id=p.tax_id,
        bank_name=p.bank_name,
        agency=p.agency,
        account=p.account,
        pix_key=p.pix_key,
        notes=p.notes,
        created_at=p.created_at,
    )


def _line_out(line) -> FundingLineOut:
    return FundingLineOut(
        id=line.id,
        position=line.position,
        label=line.label,
        code=line.code,
        amount=dec_str(line.amount),
        currency=line.currency,
        notes=line.notes,
    )


def _funding_out(fr: CustomsFundingRequest) -> FundingOut:
    st = customs_public.structured_total(fr)
    div = customs_public.funding_divergence(fr)
    links = sorted(fr.payable_links or [], key=lambda l: l.sequence)
    return FundingOut(
        id=fr.id,
        process_id=fr.process_id,
        payee_id=fr.payee_id,
        payee=_payee_out(fr.payee) if fr.payee else None,
        reference=fr.reference,
        issue_date=fr.issue_date,
        due_date=fr.due_date,
        currency=fr.currency,
        declared_total=dec_str(fr.declared_total) or "0",
        structured_total=str(st),
        divergence=str(div),
        document_id=fr.document_id,
        version=fr.version,
        status=fr.status,
        notes=fr.notes,
        confirmed_at=fr.confirmed_at,
        cancelled_at=fr.cancelled_at,
        created_at=fr.created_at,
        value_bases=[_line_out(x) for x in sorted(fr.value_bases or [], key=lambda l: l.position)],
        tax_lines=[_line_out(x) for x in sorted(fr.tax_lines or [], key=lambda l: l.position)],
        expense_lines=[
            _line_out(x) for x in sorted(fr.expense_lines or [], key=lambda l: l.position)
        ],
        payable_links=[
            FundingPayableLinkOut(
                id=lnk.id,
                payable_id=lnk.payable_id,
                sequence=lnk.sequence,
                amount=dec_str(lnk.amount) or "0",
                currency=lnk.currency,
            )
            for lnk in links
        ],
    )


# —— Payees ——


@router.get("/customs/payees", response_model=list[PayeeOut])
def api_list_payees(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    return [_payee_out(p) for p in customs_public.list_payees(db, limit=limit, offset=offset)]


@router.post("/customs/payees", response_model=PayeeOut, status_code=201)
def api_create_payee(
    body: PayeeIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            row = customs_public.create_payee(
                uow.session,
                name=body.name,
                tax_id=body.tax_id,
                bank_name=body.bank_name,
                agency=body.agency,
                account=body.account,
                pix_key=body.pix_key,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_payee",
                entity_id=str(row.id),
                action="payee.create",
            )
            uow.commit()
            return _payee_out(row)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get("/customs/payees/{payee_id}", response_model=PayeeOut)
def api_get_payee(
    payee_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return _payee_out(customs_public.get_payee(db, payee_id))
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.patch("/customs/payees/{payee_id}", response_model=PayeeOut)
def api_update_payee(
    payee_id: int,
    body: PayeeUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            row = customs_public.update_payee(
                uow.session,
                payee_id,
                name=body.name,
                tax_id=body.tax_id,
                bank_name=body.bank_name,
                agency=body.agency,
                account=body.account,
                pix_key=body.pix_key,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_payee",
                entity_id=str(payee_id),
                action="payee.update",
            )
            uow.commit()
            return _payee_out(row)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/customs/funding-requests/{funding_id}",
    response_model=FundingOut,
)
def api_get_funding_by_id(
    funding_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Lookup público por id — resolve process_id sem exigir path do processo (J5-C1 Opção B)."""
    enforce_permission(user, "customs:read")
    try:
        fr = customs_public.get_funding_request(db, funding_id)
        return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


# —— Funding requests ——


@router.get(
    "/import-processes/{process_id}/funding-requests",
    response_model=list[FundingOut],
)
def api_list_fundings(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return [_funding_out(fr) for fr in customs_public.list_funding_requests(db, process_id)]
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/funding-requests",
    response_model=FundingOut,
    status_code=201,
)
def api_create_funding(
    process_id: int,
    body: FundingCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.create_funding_request(
                uow.session,
                process_id,
                payee_id=body.payee_id,
                currency=body.currency,
                declared_total=body.declared_total,
                reference=body.reference,
                issue_date=body.issue_date,
                due_date=body.due_date,
                document_id=body.document_id,
                notes=body.notes,
                idempotency_key=body.idempotency_key,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(fr.id),
                action="funding.create",
            )
            uow.commit()
            full = customs_public.get_funding_request(uow.session, fr.id)
            return _funding_out(full)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/funding-requests/{funding_id}",
    response_model=FundingOut,
)
def api_get_funding(
    process_id: int,
    funding_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        fr = customs_public.get_funding_request(db, funding_id)
        if fr.process_id != process_id:
            raise AppError("Funding não pertence ao processo", code="funding_mismatch", status_code=404)
        return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/import-processes/{process_id}/funding-requests/{funding_id}",
    response_model=FundingOut,
)
def api_update_funding(
    process_id: int,
    funding_id: int,
    body: FundingUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.update_funding_request(
                uow.session,
                funding_id,
                expected_version=body.expected_version,
                payee_id=body.payee_id,
                reference=body.reference,
                issue_date=body.issue_date,
                due_date=body.due_date,
                currency=body.currency,
                declared_total=body.declared_total,
                document_id=body.document_id,
                clear_document=body.clear_document,
                notes=body.notes,
            )
            if fr.process_id != process_id:
                raise AppError(
                    "Funding não pertence ao processo", code="funding_mismatch", status_code=404
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                action="funding.update",
            )
            uow.commit()
            return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.put(
    "/import-processes/{process_id}/funding-requests/{funding_id}/value-bases",
    response_model=FundingOut,
)
def api_replace_value_bases(
    process_id: int,
    funding_id: int,
    body: FundingReplaceLinesBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.replace_value_bases(
                uow.session,
                funding_id,
                expected_version=body.expected_version,
                lines=[line.model_dump() for line in body.lines],
            )
            if fr.process_id != process_id:
                raise AppError(
                    "Funding não pertence ao processo", code="funding_mismatch", status_code=404
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                action="funding.value_bases.replace",
            )
            uow.commit()
            return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.put(
    "/import-processes/{process_id}/funding-requests/{funding_id}/tax-lines",
    response_model=FundingOut,
)
def api_replace_tax_lines(
    process_id: int,
    funding_id: int,
    body: FundingReplaceLinesBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.replace_tax_lines(
                uow.session,
                funding_id,
                expected_version=body.expected_version,
                lines=[line.model_dump() for line in body.lines],
            )
            if fr.process_id != process_id:
                raise AppError(
                    "Funding não pertence ao processo", code="funding_mismatch", status_code=404
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                action="funding.tax_lines.replace",
            )
            uow.commit()
            return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.put(
    "/import-processes/{process_id}/funding-requests/{funding_id}/expense-lines",
    response_model=FundingOut,
)
def api_replace_expense_lines(
    process_id: int,
    funding_id: int,
    body: FundingReplaceLinesBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.replace_expense_lines(
                uow.session,
                funding_id,
                expected_version=body.expected_version,
                lines=[line.model_dump() for line in body.lines],
            )
            if fr.process_id != process_id:
                raise AppError(
                    "Funding não pertence ao processo", code="funding_mismatch", status_code=404
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                action="funding.expense_lines.replace",
            )
            uow.commit()
            return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/funding-requests/{funding_id}/confirm",
    response_model=FundingOut,
)
def api_confirm_funding(
    process_id: int,
    funding_id: int,
    body: FundingVersionLockBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.confirm_funding_request(
                uow.session, funding_id, expected_version=body.expected_version
            )
            if fr.process_id != process_id:
                raise AppError(
                    "Funding não pertence ao processo", code="funding_mismatch", status_code=404
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                action="funding.confirm",
                details="payable_created_i5_3b",
            )
            uow.commit()
            return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/funding-requests/{funding_id}/cancel",
    response_model=FundingOut,
)
def api_cancel_funding(
    process_id: int,
    funding_id: int,
    body: FundingVersionLockBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            fr = customs_public.cancel_funding_request(
                uow.session, funding_id, expected_version=body.expected_version
            )
            if fr.process_id != process_id:
                raise AppError(
                    "Funding não pertence ao processo", code="funding_mismatch", status_code=404
                )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                action="funding.cancel",
            )
            uow.commit()
            return _funding_out(fr)
    except CustomsError as exc:
        raise _map_error(exc) from exc
