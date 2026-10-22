"""HTTP Costing — /api/costing."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.costing import public as costing_public
from app.costing.errors import CostingError
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork

router = APIRouter(tags=["costing"])


def _map(exc: CostingError) -> AppError:
    code = getattr(exc, "code", "costing_error")
    status = 400
    if code == "not_found":
        status = 404
    elif code in ("conflict", "not_draft"):
        status = 409
    elif code == "publish_blocked":
        status = 409
    elif code in (
        "validation_error",
        "qty_invalid",
        "missing_basis",
        "zero_basis",
        "manual_sum",
        "no_costing_lines",
    ):
        status = 422
    details = getattr(exc, "details", None)
    return AppError(exc.message, code=code, status_code=status, details=details)


class EnsureBody(BaseModel):
    process_id: int


class RecalcBody(BaseModel):
    kind: str = "ESTIMATED"
    line_links: list[dict] | None = None
    methods: dict | None = None
    manuals: dict | None = None


class PublishBody(BaseModel):
    reason: str | None = None
    allow_partial: bool = False


class FreightBody(BaseModel):
    choice: str
    reason: str


class ExpenseBody(BaseModel):
    category: str
    description: str
    amount: str
    currency: str = "BRL"
    expense_date: date | None = None
    payee_snapshot: str | None = None
    document_id: int | None = None
    allocation_method: str = "VALUE"


class ReviseBody(BaseModel):
    kind: str = "REVISED"


@router.get("/costing/queue")
def get_queue(user=Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_permission(user, "costing:read")
    return costing_public.queue(db)


@router.post("/costing/cases", status_code=201)
def create_case(body: EnsureBody, user=Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_permission(user, "costing:write")
    try:
        with UnitOfWork(db) as uow:
            case = costing_public.ensure_case(uow.session, body.process_id, actor_id=str(user.id))
            uow.commit()
            return costing_public.case_to_dict(uow.session, case)
    except CostingError as exc:
        raise _map(exc) from exc


@router.get("/costing/cases/{case_id}")
def get_case(case_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_permission(user, "costing:read")
    try:
        case = costing_public.get_case(db, case_id)
        data = costing_public.case_to_dict(db, case)
        data["versions"] = [
            costing_public.version_to_dict(db, v, include_children=False)
            for v in case.versions
        ]
        return data
    except CostingError as exc:
        raise _map(exc) from exc


@router.post("/costing/cases/{case_id}/recalculate")
def recalc(
    case_id: int,
    body: RecalcBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "costing:write")
    try:
        with UnitOfWork(db) as uow:
            version = costing_public.recalculate(
                uow.session,
                case_id,
                actor_id=str(user.id),
                kind=body.kind,
                line_links=body.line_links,
                methods=body.methods,
                manuals=body.manuals,
            )
            uow.commit()
            return costing_public.version_to_dict(uow.session, version)
    except CostingError as exc:
        raise _map(exc) from exc


@router.post("/costing/cases/{case_id}/freight-choice")
def freight_choice(
    case_id: int,
    body: FreightBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "costing:write")
    try:
        with UnitOfWork(db) as uow:
            case = costing_public.set_freight_choice(
                uow.session,
                case_id,
                actor_id=str(user.id),
                choice=body.choice,
                reason=body.reason,
            )
            uow.commit()
            return costing_public.case_to_dict(uow.session, case)
    except CostingError as exc:
        raise _map(exc) from exc


@router.post("/costing/cases/{case_id}/expenses", status_code=201)
def create_expense(
    case_id: int,
    body: ExpenseBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "costing:write")
    try:
        with UnitOfWork(db) as uow:
            row = costing_public.add_expense(
                uow.session,
                case_id,
                actor_id=str(user.id),
                category=body.category,
                description=body.description,
                amount=body.amount,
                currency=body.currency,
                expense_date=body.expense_date,
                payee_snapshot=body.payee_snapshot,
                document_id=body.document_id,
                allocation_method=body.allocation_method,
            )
            uow.commit()
            return {"id": row.id, "status": row.status, "amount": str(row.amount)}
    except CostingError as exc:
        raise _map(exc) from exc


@router.get("/costing/versions/{version_id}")
def get_version(version_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_permission(user, "costing:read")
    try:
        version = costing_public.get_version(db, version_id)
        return costing_public.version_to_dict(db, version)
    except CostingError as exc:
        raise _map(exc) from exc


@router.post("/costing/versions/{version_id}/publish")
def publish(
    version_id: int,
    body: PublishBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "costing:publish")
    try:
        with UnitOfWork(db) as uow:
            version = costing_public.publish_version(
                uow.session,
                version_id,
                actor_id=str(user.id),
                reason=body.reason,
                allow_partial=body.allow_partial,
            )
            uow.commit()
            return costing_public.version_to_dict(uow.session, version)
    except CostingError as exc:
        raise _map(exc) from exc


@router.post("/costing/versions/{version_id}/revise")
def revise(
    version_id: int,
    body: ReviseBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "costing:write")
    try:
        with UnitOfWork(db) as uow:
            version = costing_public.revise_from_published(
                uow.session, version_id, actor_id=str(user.id), kind=body.kind
            )
            uow.commit()
            return costing_public.version_to_dict(uow.session, version)
    except CostingError as exc:
        raise _map(exc) from exc


@router.get("/costing/versions/{version_id}/compare/{other_id}")
def compare(
    version_id: int,
    other_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "costing:read")
    try:
        return costing_public.compare_versions(db, version_id, other_id)
    except CostingError as exc:
        raise _map(exc) from exc
