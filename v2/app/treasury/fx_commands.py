"""Comandos FX Inc-4."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.documents import public as documents_public
from app.treasury.errors import PaymentNotFound, PaymentValidationError, TreasuryError
from app.treasury.fx_models import (
    FxAllocationValuation,
    FxExecution,
    FxExecutionAllocation,
    FxMarketQuote,
    FxPlanRate,
)
from app.treasury.fx_money import (
    money2,
    parse_decimal,
    rate6,
    realized_result_vs_reference,
    to_brl,
    weighted_rate,
)
from app.treasury.fx_provider import FxQuoteUnavailable, get_quote_provider
from app.treasury.models import Payment, PaymentAllocation

ALLOWED_FOREIGN = frozenset({"EUR", "USD"})
STALE_MINUTES_DEFAULT = 15
# Inc-4A app limit (schema allows N)
MAX_EXECUTIONS_PER_PAYMENT_APP = 1


class FxNotFound(TreasuryError):
    code = "fx_not_found"


class FxConflict(TreasuryError):
    code = "conflict"

    def __init__(self, message: str = "Conflito FX"):
        super().__init__(message, code="conflict")


def _validate_pair(foreign: str, base: str = "BRL") -> tuple[str, str]:
    foreign = foreign.strip().upper()
    base = base.strip().upper()
    if base != "BRL":
        raise PaymentValidationError("base_currency deve ser BRL")
    if foreign not in ALLOWED_FOREIGN:
        raise PaymentValidationError(f"Moeda estrangeira não permitida no Inc-4: {foreign}")
    if foreign == "BRL":
        raise PaymentValidationError("FX não se aplica a BRL")
    return foreign, base


def get_current_plan(db: Session, payable_id: int) -> FxPlanRate | None:
    return (
        db.query(FxPlanRate)
        .filter(FxPlanRate.payable_id == payable_id, FxPlanRate.is_current.is_(True))
        .first()
    )


def get_current_plans_bulk(db: Session, payable_ids: list[int]) -> dict[int, FxPlanRate]:
    if not payable_ids:
        return {}
    rows = (
        db.query(FxPlanRate)
        .filter(FxPlanRate.payable_id.in_(payable_ids), FxPlanRate.is_current.is_(True))
        .all()
    )
    return {r.payable_id: r for r in rows}


def get_initial_plan(db: Session, payable_id: int) -> FxPlanRate | None:
    return (
        db.query(FxPlanRate)
        .filter(FxPlanRate.payable_id == payable_id, FxPlanRate.kind == "INITIAL")
        .order_by(FxPlanRate.id.asc())
        .first()
    )


def list_plan_history(db: Session, payable_id: int) -> list[FxPlanRate]:
    return (
        db.query(FxPlanRate)
        .filter(FxPlanRate.payable_id == payable_id)
        .order_by(FxPlanRate.version.asc(), FxPlanRate.id.asc())
        .all()
    )


def register_plan_rate(
    db: Session,
    *,
    payable_id: int,
    kind: str,
    rate: str | Decimal,
    effective_from: date,
    created_by_actor_id: str,
    reason_code: str | None = None,
    idempotency_key: str | None = None,
    supersedes_id: int | None = None,
) -> FxPlanRate:
    kind = kind.strip().upper()
    if kind not in ("INITIAL", "REFORECAST", "CORRECTION"):
        raise PaymentValidationError("kind deve ser INITIAL, REFORECAST ou CORRECTION")
    if kind in ("REFORECAST", "CORRECTION") and not (reason_code or "").strip():
        raise PaymentValidationError("reason_code obrigatório para REFORECAST/CORRECTION")
    if idempotency_key:
        existing = (
            db.query(FxPlanRate)
            .filter(
                FxPlanRate.payable_id == payable_id,
                FxPlanRate.idempotency_key == idempotency_key.strip(),
            )
            .first()
        )
        if existing:
            return existing

    try:
        # Serializa mutações de current por Payable (Billing public API)
        payable = billing_public.get_payable_for_update(db, payable_id)
    except billing_public.BillingError as e:
        raise PaymentValidationError(getattr(e, "message", str(e))) from e

    foreign, base = _validate_pair(payable.currency)
    rate_d = rate6(parse_decimal(rate) or Decimal("0"))
    if rate_d <= 0:
        raise PaymentValidationError("Taxa deve ser > 0")

    current = (
        db.query(FxPlanRate)
        .filter(FxPlanRate.payable_id == payable_id, FxPlanRate.is_current.is_(True))
        .with_for_update()
        .first()
    )
    if kind == "INITIAL" and current is not None:
        raise PaymentValidationError("Payable já possui taxa projetada INITIAL/current")
    if kind == "CORRECTION" and supersedes_id is None and current is None:
        raise PaymentValidationError("CORRECTION exige versão a corrigir")

    next_version = (current.version + 1) if current else 1
    if current:
        current.is_current = False
        db.flush()

    target_supersede = supersedes_id or (current.id if current and kind == "CORRECTION" else None)
    row = FxPlanRate(
        payable_id=payable_id,
        kind=kind,
        foreign_currency=foreign,
        base_currency=base,
        rate=rate_d,
        effective_from=effective_from,
        version=next_version,
        is_current=True,
        supersedes_id=target_supersede,
        reason_code=(reason_code or "").strip() or None,
        idempotency_key=idempotency_key.strip() if idempotency_key else None,
        created_by_actor_id=str(created_by_actor_id).strip(),
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        raise FxConflict("Já existe uma projeção current para este Payable") from exc
    return row


def list_executions(db: Session, payment_id: int) -> list[FxExecution]:
    return (
        db.query(FxExecution)
        .filter(FxExecution.payment_id == payment_id)
        .order_by(FxExecution.id.asc())
        .all()
    )


def register_execution(
    db: Session,
    *,
    payment_id: int,
    foreign_amount: str | Decimal,
    brl_amount: str | Decimal | None = None,
    rate: str | Decimal | None = None,
    execution_date: date,
    created_by_actor_id: str,
    external_reference: str | None = None,
    register_without_document: bool = False,
    idempotency_key: str | None = None,
    enforce_single_app_limit: bool = True,
) -> FxExecution:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise PaymentNotFound(payment_id)
    if payment.status != "REGISTERED":
        raise PaymentValidationError("Somente pagamento REGISTERED aceita execução FX")
    _validate_pair(payment.currency)

    if idempotency_key:
        existing = (
            db.query(FxExecution)
            .filter(
                FxExecution.payment_id == payment_id,
                FxExecution.idempotency_key == idempotency_key.strip(),
            )
            .first()
        )
        if existing:
            return existing

    if enforce_single_app_limit:
        n = db.query(FxExecution).filter(FxExecution.payment_id == payment_id).count()
        if n >= MAX_EXECUTIONS_PER_PAYMENT_APP:
            raise PaymentValidationError(
                "Inc-4A: no máximo uma FxExecution por Payment (schema permite N)"
            )

    fa = money2(parse_decimal(foreign_amount) or Decimal("0"))
    if fa <= 0:
        raise PaymentValidationError("foreign_amount deve ser > 0")
    # FIN-1: se o operador informa EUR + BRL, ambos são fonte da verdade;
    # a taxa é sempre derivada (nunca recalcular BRL a partir da taxa).
    # Se informa EUR + taxa (sem BRL), o BRL é derivado.
    if brl_amount is not None:
        ba = money2(parse_decimal(brl_amount) or Decimal("0"))
        rd = rate6(ba / fa)
    elif rate is not None:
        rd = rate6(parse_decimal(rate) or Decimal("0"))
        ba = money2(fa * rd)
    else:
        raise PaymentValidationError("Informe rate ou brl_amount")
    if ba <= 0 or rd <= 0:
        raise PaymentValidationError("Valores de execução inválidos")

    row = FxExecution(
        payment_id=payment_id,
        foreign_amount=fa,
        brl_amount=ba,
        rate=rd,
        execution_date=execution_date,
        external_reference=(external_reference or "").strip() or None,
        register_without_document=bool(register_without_document),
        idempotency_key=idempotency_key.strip() if idempotency_key else None,
        created_by_actor_id=str(created_by_actor_id).strip(),
    )
    db.add(row)
    db.flush()
    return row


def assert_execution_has_document(db: Session, execution: FxExecution) -> None:
    if execution.register_without_document:
        return
    docs = documents_public.list_by_entity(db, "fx_execution", str(execution.id))
    if not docs:
        raise PaymentValidationError("Documento obrigatório para execução FX (ou override)")


def link_execution_allocation(
    db: Session,
    *,
    fx_execution_id: int,
    payment_allocation_id: int,
    foreign_amount: str | Decimal | None = None,
    created_by_actor_id: str,
) -> FxExecutionAllocation:
    execution = (
        db.query(FxExecution).filter(FxExecution.id == fx_execution_id).with_for_update().first()
    )
    if not execution:
        raise FxNotFound(f"Execução FX #{fx_execution_id} não encontrada")
    alloc = (
        db.query(PaymentAllocation)
        .filter(PaymentAllocation.id == payment_allocation_id)
        .with_for_update()
        .first()
    )
    if not alloc:
        raise FxNotFound(f"Allocation #{payment_allocation_id} não encontrada")
    if alloc.payment_id != execution.payment_id:
        raise PaymentValidationError("Execution e Allocation devem pertencer ao mesmo Payment")

    # Inc-4A: one link per allocation (schema N:M permanece aberto)
    existing_link = (
        db.query(FxExecutionAllocation)
        .filter(FxExecutionAllocation.payment_allocation_id == payment_allocation_id)
        .first()
    )
    if existing_link:
        raise PaymentValidationError("Allocation já possui link FX (Inc-4A 1:1)")

    fa = money2(parse_decimal(foreign_amount) or alloc.amount)
    if fa <= 0 or fa > alloc.amount:
        raise PaymentValidationError("foreign_amount do link inválido")

    used_exec = (
        db.query(func.coalesce(func.sum(FxExecutionAllocation.foreign_amount), 0))
        .filter(FxExecutionAllocation.fx_execution_id == fx_execution_id)
        .scalar()
    )
    used = money2(Decimal(str(used_exec)))
    if used + fa > execution.foreign_amount:
        raise PaymentValidationError("Soma dos links excede foreign_amount da execução")

    used_alloc = (
        db.query(func.coalesce(func.sum(FxExecutionAllocation.foreign_amount), 0))
        .filter(FxExecutionAllocation.payment_allocation_id == payment_allocation_id)
        .scalar()
    )
    used_a = money2(Decimal(str(used_alloc)))
    if used_a + fa > alloc.amount:
        raise PaymentValidationError("Soma dos links excede amount da allocation")

    # pro-rata BRL
    ba = money2(execution.brl_amount * (fa / execution.foreign_amount))
    link = FxExecutionAllocation(
        fx_execution_id=fx_execution_id,
        payment_allocation_id=payment_allocation_id,
        foreign_amount=fa,
        brl_amount=ba,
    )
    db.add(link)
    db.flush()
    _ = created_by_actor_id
    return link


def complete_allocation_valuation(
    db: Session,
    *,
    payment_allocation_id: int,
    created_by_actor_id: str,
) -> FxAllocationValuation:
    existing = (
        db.query(FxAllocationValuation)
        .filter(FxAllocationValuation.payment_allocation_id == payment_allocation_id)
        .first()
    )
    if existing:
        return existing

    alloc = db.query(PaymentAllocation).filter(PaymentAllocation.id == payment_allocation_id).first()
    if not alloc:
        raise FxNotFound(f"Allocation #{payment_allocation_id} não encontrada")

    links = (
        db.query(FxExecutionAllocation)
        .filter(FxExecutionAllocation.payment_allocation_id == payment_allocation_id)
        .all()
    )
    if not links:
        raise PaymentValidationError("Sem FxExecutionAllocation para valuation")

    foreign_sum = money2(sum((l.foreign_amount for l in links), Decimal("0")))
    brl_sum = money2(sum((l.brl_amount for l in links), Decimal("0")))
    realized_rate = weighted_rate(foreign_sum, brl_sum)
    if realized_rate is None:
        raise PaymentValidationError("Não foi possível derivar taxa realizada")

    plan = get_current_plan(db, alloc.payable_id)
    if not plan:
        raise PaymentValidationError("Payable sem taxa projetada current para freeze")

    planned_brl = to_brl(foreign_sum, plan.rate)
    realized_brl = brl_sum
    result = realized_result_vs_reference(foreign_sum, plan.rate, realized_rate)

    row = FxAllocationValuation(
        payment_allocation_id=payment_allocation_id,
        planned_rate_id=plan.id,
        planned_rate_snapshot=plan.rate,
        realized_rate_snapshot=realized_rate,
        foreign_amount_snapshot=foreign_sum,
        planned_brl=planned_brl,
        realized_brl=realized_brl,
        realized_result_vs_reference=result,
        reference_kind="CURRENT_AT_FREEZE",
        created_by_actor_id=str(created_by_actor_id).strip(),
    )
    db.add(row)
    db.flush()
    return row


def rebind_valuation(
    db: Session,
    *,
    valuation_id: int,
    planned_rate_id: int,
    created_by_actor_id: str,
    reason_code: str,
) -> FxAllocationValuation:
    if not (reason_code or "").strip():
        raise PaymentValidationError("reason_code obrigatório no rebind")
    val = db.query(FxAllocationValuation).filter(FxAllocationValuation.id == valuation_id).first()
    if not val:
        raise FxNotFound(f"Valuation #{valuation_id} não encontrada")
    plan = db.query(FxPlanRate).filter(FxPlanRate.id == planned_rate_id).first()
    if not plan:
        raise FxNotFound(f"Plan rate #{planned_rate_id} não encontrada")
    foreign = val.foreign_amount_snapshot
    realized_rate = val.realized_rate_snapshot
    val.planned_rate_id = plan.id
    val.planned_rate_snapshot = plan.rate
    val.planned_brl = to_brl(foreign, plan.rate)
    val.realized_result_vs_reference = realized_result_vs_reference(foreign, plan.rate, realized_rate)
    val.reference_kind = "REBIND"
    val.calculated_at = datetime.now(timezone.utc)
    val.created_by_actor_id = str(created_by_actor_id).strip()
    db.flush()
    return val


def persist_market_quote(
    db: Session,
    *,
    foreign_currency: str,
    rate: str | Decimal,
    source: str,
    observed_at: datetime | None = None,
    stale_minutes: int = STALE_MINUTES_DEFAULT,
) -> FxMarketQuote:
    foreign, base = _validate_pair(foreign_currency)
    rd = rate6(parse_decimal(rate) or Decimal("0"))
    if rd <= 0:
        raise PaymentValidationError("Taxa de mercado deve ser > 0")
    now = datetime.now(timezone.utc)
    obs = observed_at or now
    row = FxMarketQuote(
        foreign_currency=foreign,
        base_currency=base,
        rate=rd,
        source=(source or "MANUAL").strip(),
        observed_at=obs,
        retrieved_at=now,
        stale_after=now + timedelta(minutes=stale_minutes),
    )
    db.add(row)
    db.flush()
    return row


def get_latest_quote(db: Session, foreign: str, base: str = "BRL") -> FxMarketQuote | None:
    foreign, base = _validate_pair(foreign, base)
    return (
        db.query(FxMarketQuote)
        .filter(
            FxMarketQuote.foreign_currency == foreign,
            FxMarketQuote.base_currency == base,
        )
        .order_by(FxMarketQuote.retrieved_at.desc(), FxMarketQuote.id.desc())
        .first()
    )


def get_quote_for_date(
    db: Session,
    *,
    as_of: date,
    foreign: str = "EUR",
    base: str = "BRL",
) -> FxMarketQuote | None:
    """Cotação cuja observed_at cai no dia `as_of`. Não inventa vizinho."""
    foreign, base = _validate_pair(foreign, base)
    return (
        db.query(FxMarketQuote)
        .filter(
            FxMarketQuote.foreign_currency == foreign,
            FxMarketQuote.base_currency == base,
            func.date(FxMarketQuote.observed_at) == as_of,
        )
        .order_by(FxMarketQuote.retrieved_at.desc(), FxMarketQuote.id.desc())
        .first()
    )


def refresh_market_quote(
    db: Session,
    *,
    foreign: str = "EUR",
    base: str = "BRL",
    stale_minutes: int = STALE_MINUTES_DEFAULT,
    provider=None,
) -> FxMarketQuote:
    """Persiste cotação via FxQuoteProvider (HTTP só injetado na borda Inc-4B)."""
    active = provider if provider is not None else get_quote_provider()
    if active is None:
        raise PaymentValidationError("Nenhum FxQuoteProvider configurado")
    try:
        dto = active.get_latest_quote(foreign, base)
    except FxQuoteUnavailable as e:
        raise PaymentValidationError(e.message) from e
    return persist_market_quote(
        db,
        foreign_currency=dto.foreign_currency,
        rate=dto.rate,
        source=dto.source,
        observed_at=dto.observed_at,
        stale_minutes=stale_minutes,
    )


def quote_status(quote: FxMarketQuote | None, now: datetime | None = None) -> str:
    if quote is None:
        return "missing"
    now = now or datetime.now(timezone.utc)
    stale_after = quote.stale_after
    if stale_after.tzinfo is None:
        stale_after = stale_after.replace(tzinfo=timezone.utc)
    if now < stale_after:
        return "fresh"
    return "stale"
