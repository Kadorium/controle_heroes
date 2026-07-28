"""Rotas HTTP FX Inc-4."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.billing import public as billing_public
from app.documents import public as documents_public
from app.foundation.deps import enforce_permission, get_current_user, get_db
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
from app.treasury import fx_commands as fx
from app.treasury import fx_queries
from app.treasury.errors import TreasuryError
from app.treasury.fx_queries import decimal_str

router = APIRouter(tags=["treasury-fx"])


def _map_error(exc: TreasuryError | billing_public.BillingError) -> AppError:
    code = getattr(exc, "code", "treasury_error")
    status = 400
    if str(code).endswith("not_found"):
        status = 404
    elif code in ("conflict", "invalid_transition"):
        status = 409
    return AppError(getattr(exc, "message", str(exc)), code=code, status_code=status)


def _cleanup_pending_files(paths: list[Path]) -> None:
    """Mesmo padrão Inc-3 (`treasury.routes._cleanup_files`): unlink dos paths pendentes."""
    for p in paths:
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


class PlanBody(BaseModel):
    kind: str = "INITIAL"
    rate: str
    effective_from: date
    reason_code: str | None = None
    idempotency_key: str | None = None
    supersedes_id: int | None = None


class ExecutionBody(BaseModel):
    foreign_amount: str
    brl_amount: str | None = None
    rate: str | None = None
    execution_date: date
    external_reference: str | None = None
    register_without_document: bool = False
    reason_code: str | None = None
    idempotency_key: str | None = None


class LinkBody(BaseModel):
    fx_execution_id: int
    payment_allocation_id: int
    foreign_amount: str | None = None


class QuoteBody(BaseModel):
    foreign_currency: str = "EUR"
    rate: str
    source: str = "MANUAL"
    stale_minutes: int = 15


class RebindBody(BaseModel):
    planned_rate_id: int
    reason_code: str


class CompleteValuationBody(BaseModel):
    payment_allocation_id: int


@router.post("/payables/{payable_id}/fx-plan")
def post_plan(
    payable_id: int,
    payload: PlanBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:fx_write")
    try:
        with UnitOfWork(db) as uow:
            row = fx.register_plan_rate(
                uow.session,
                payable_id=payable_id,
                kind=payload.kind,
                rate=payload.rate,
                effective_from=payload.effective_from,
                created_by_actor_id=str(user.id),
                reason_code=payload.reason_code,
                idempotency_key=payload.idempotency_key,
                supersedes_id=payload.supersedes_id,
            )
            action = {
                "INITIAL": "fx.planned.register",
                "REFORECAST": "fx.planned.register",
                "CORRECTION": "fx.supersede",
            }.get(payload.kind.upper(), "fx.planned.register")
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_plan_rate",
                entity_id=str(row.id),
                action=action,
                reason_code=payload.reason_code,
                details=f"{payload.kind}:{payload.rate}",
            )
            uow.commit()
            return {
                "id": row.id,
                "payable_id": row.payable_id,
                "kind": row.kind,
                "rate": decimal_str(row.rate),
                "version": row.version,
                "is_current": row.is_current,
            }
    except (TreasuryError, billing_public.BillingError) as e:
        raise _map_error(e) from e


@router.get("/payables/{payable_id}/fx-plan")
def get_plan(payable_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:fx_read")
    try:
        billing_public.get_payable(db, payable_id)
    except billing_public.BillingError as e:
        raise _map_error(e) from e
    initial = fx.get_initial_plan(db, payable_id)
    current = fx.get_current_plan(db, payable_id)
    return {
        "initial_planned_rate": decimal_str(initial.rate) if initial else None,
        "current_forecast_rate": decimal_str(current.rate) if current else None,
        "history": [
            {
                "id": h.id,
                "kind": h.kind,
                "rate": decimal_str(h.rate),
                "version": h.version,
                "is_current": h.is_current,
            }
            for h in fx.list_plan_history(db, payable_id)
        ],
    }


@router.get("/payables/{payable_id}/fx-view")
def get_payable_fx_view(payable_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:fx_read")
    try:
        return fx_queries.payable_fx_view(db, payable_id)
    except (TreasuryError, billing_public.BillingError) as e:
        raise _map_error(e) from e


@router.post("/payments/{payment_id}/fx-executions")
def post_execution(
    payment_id: int,
    payload: ExecutionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:fx_write")
    if payload.register_without_document:
        enforce_permission(user, "treasury:fx_without_document")
    try:
        with UnitOfWork(db) as uow:
            row = fx.register_execution(
                uow.session,
                payment_id=payment_id,
                foreign_amount=payload.foreign_amount,
                brl_amount=payload.brl_amount,
                rate=payload.rate,
                execution_date=payload.execution_date,
                created_by_actor_id=str(user.id),
                external_reference=payload.external_reference,
                register_without_document=payload.register_without_document,
                idempotency_key=payload.idempotency_key,
            )
            if payload.register_without_document:
                audit_public.record_event(
                    uow.session,
                    actor_id=str(user.id),
                    entity_type="fx_execution",
                    entity_id=str(row.id),
                    action="fx.without_document",
                    reason_code=payload.reason_code or "FX_NO_DOC",
                )
            else:
                fx.assert_execution_has_document(uow.session, row)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_execution",
                entity_id=str(row.id),
                action="fx.realized.register",
                details=f"rate={row.rate}",
            )
            uow.commit()
            return {
                "id": row.id,
                "payment_id": row.payment_id,
                "foreign_amount": decimal_str(row.foreign_amount),
                "brl_amount": decimal_str(row.brl_amount),
                "rate": decimal_str(row.rate),
            }
    except (TreasuryError, billing_public.BillingError) as e:
        raise _map_error(e) from e


@router.post("/payments/{payment_id}/fx-executions/with-document")
async def post_execution_with_doc(
    payment_id: int,
    foreign_amount: str = Form(...),
    execution_date: date = Form(...),
    rate: str | None = Form(None),
    brl_amount: str | None = Form(None),
    external_reference: str | None = Form(None),
    idempotency_key: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:fx_write")
    pending: list[Path] = []
    settings = get_settings()
    try:
        with UnitOfWork(db) as uow:
            row = fx.register_execution(
                uow.session,
                payment_id=payment_id,
                foreign_amount=foreign_amount,
                brl_amount=brl_amount,
                rate=rate,
                execution_date=execution_date,
                created_by_actor_id=str(user.id),
                external_reference=external_reference,
                register_without_document=False,
                idempotency_key=idempotency_key,
            )
            content = await file.read()
            doc = documents_public.store_document_tracked(
                uow.session,
                attachments_path=settings.attachments_path,
                actor_id=str(user.id),
                filename=file.filename or "fx.pdf",
                content=content,
                mime_type=file.content_type,
                pending_files=pending,
            )
            documents_public.link_document(
                uow.session,
                document_id=doc.id,
                entity_type="fx_execution",
                entity_id=str(row.id),
                role="fx_evidence",
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_execution",
                entity_id=str(row.id),
                action="fx.realized.register",
                details=f"rate={row.rate}",
            )
            uow.commit()
            return {"id": row.id, "rate": decimal_str(row.rate), "brl_amount": decimal_str(row.brl_amount)}
    except (TreasuryError, billing_public.BillingError) as e:
        _cleanup_pending_files(pending)
        raise _map_error(e) from e
    except Exception:
        _cleanup_pending_files(pending)
        raise


@router.get("/payments/{payment_id}/fx-executions")
def get_executions(payment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:fx_read")
    rows = fx.list_executions(db, payment_id)
    return [
        {
            "id": r.id,
            "foreign_amount": decimal_str(r.foreign_amount),
            "brl_amount": decimal_str(r.brl_amount),
            "rate": decimal_str(r.rate),
            "execution_date": r.execution_date.isoformat(),
        }
        for r in rows
    ]


@router.get("/payments/{payment_id}/fx-view")
def get_payment_fx_view(payment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:fx_read")
    try:
        return fx_queries.payment_fx_view(db, payment_id)
    except TreasuryError as e:
        raise _map_error(e) from e


@router.post("/fx/execution-allocations")
def post_link(payload: LinkBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:fx_write")
    try:
        with UnitOfWork(db) as uow:
            link = fx.link_execution_allocation(
                uow.session,
                fx_execution_id=payload.fx_execution_id,
                payment_allocation_id=payload.payment_allocation_id,
                foreign_amount=payload.foreign_amount,
                created_by_actor_id=str(user.id),
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_execution_allocation",
                entity_id=str(link.id),
                action="fx.link",
            )
            uow.commit()
            return {
                "id": link.id,
                "fx_execution_id": link.fx_execution_id,
                "payment_allocation_id": link.payment_allocation_id,
                "foreign_amount": decimal_str(link.foreign_amount),
                "brl_amount": decimal_str(link.brl_amount),
            }
    except TreasuryError as e:
        raise _map_error(e) from e


@router.post("/fx/valuations/complete")
def post_complete_valuation(
    payload: CompleteValuationBody, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    enforce_permission(user, "treasury:fx_write")
    try:
        with UnitOfWork(db) as uow:
            val = fx.complete_allocation_valuation(
                uow.session,
                payment_allocation_id=payload.payment_allocation_id,
                created_by_actor_id=str(user.id),
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_allocation_valuation",
                entity_id=str(val.id),
                action="fx.valuation.complete",
                details=f"vs_ref={val.realized_result_vs_reference}",
            )
            uow.commit()
            return {
                "id": val.id,
                "realized_result_vs_reference": decimal_str(val.realized_result_vs_reference),
                "planned_rate_snapshot": decimal_str(val.planned_rate_snapshot),
                "benchmark": "frozen_reference",
            }
    except TreasuryError as e:
        raise _map_error(e) from e


@router.post("/fx/valuations/{valuation_id}/rebind")
def post_rebind(
    valuation_id: int,
    payload: RebindBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:fx_supersede")
    try:
        with UnitOfWork(db) as uow:
            val = fx.rebind_valuation(
                uow.session,
                valuation_id=valuation_id,
                planned_rate_id=payload.planned_rate_id,
                created_by_actor_id=str(user.id),
                reason_code=payload.reason_code,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_allocation_valuation",
                entity_id=str(val.id),
                action="fx.valuation.rebind",
                reason_code=payload.reason_code,
            )
            uow.commit()
            return {"id": val.id, "realized_result_vs_reference": decimal_str(val.realized_result_vs_reference)}
    except TreasuryError as e:
        raise _map_error(e) from e


@router.post("/fx/quotes")
def post_quote(payload: QuoteBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "treasury:fx_write")
    try:
        with UnitOfWork(db) as uow:
            row = fx.persist_market_quote(
                uow.session,
                foreign_currency=payload.foreign_currency,
                rate=payload.rate,
                source=payload.source,
                stale_minutes=payload.stale_minutes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_market_quote",
                entity_id=str(row.id),
                action="fx.quote.manual",
                details=f"{payload.rate}@{payload.source}",
            )
            uow.commit()
            return {
                "id": row.id,
                "rate": decimal_str(row.rate),
                "source": row.source,
                "status": fx.quote_status(row),
            }
    except TreasuryError as e:
        raise _map_error(e) from e


@router.get("/fx/quotes/latest")
def get_latest_quote(
    foreign: str = "EUR",
    base: str = "BRL",
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:fx_read")
    try:
        row = fx.get_latest_quote(db, foreign, base)
    except TreasuryError as e:
        raise _map_error(e) from e
    if not row:
        return {"rate": None, "status": "missing", "stale": False, "source": None}
    status = fx.quote_status(row)
    return {
        "id": row.id,
        "rate": decimal_str(row.rate),
        "status": status,
        "stale": status == "stale",
        "source": row.source,
        "observed_at": row.observed_at.isoformat(),
        "retrieved_at": row.retrieved_at.isoformat(),
    }


@router.post("/fx/quotes/refresh")
def post_refresh_quote(
    foreign: str = "EUR",
    base: str = "BRL",
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "treasury:fx_quote_refresh")
    from app.treasury.fx_provider import get_quote_provider
    from app.treasury.fx_provider_http import HttpFxQuoteProvider

    provider = get_quote_provider() or HttpFxQuoteProvider()
    try:
        with UnitOfWork(db) as uow:
            row = fx.refresh_market_quote(
                uow.session, foreign=foreign, base=base, provider=provider
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="fx_market_quote",
                entity_id=str(row.id),
                action="fx.quote.refresh",
                details=row.source,
            )
            uow.commit()
            return {
                "id": row.id,
                "rate": decimal_str(row.rate),
                "source": row.source,
                "status": fx.quote_status(row),
                "stale": False,
                "observed_at": row.observed_at.isoformat(),
                "retrieved_at": row.retrieved_at.isoformat(),
            }
    except TreasuryError as e:
        raise _map_error(e) from e
