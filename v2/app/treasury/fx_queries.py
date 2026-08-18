"""Consultas / views FX com benchmarks nomeados."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.treasury.fx_commands import (
    get_current_plan,
    get_initial_plan,
    get_latest_quote,
    list_executions,
    list_plan_history,
    quote_status,
)
from app.treasury.fx_models import FxAllocationValuation, FxExecution, FxExecutionAllocation
from app.treasury.fx_money import (
    money2,
    online_result_vs_current,
    online_result_vs_initial,
    realized_result_vs_initial,
    to_brl,
    weighted_rate,
)
from app.treasury.models import Payment, PaymentAllocation


def decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def payable_cost_brl(db: Session, payable_id: int) -> Decimal:
    """Custo em BRL da obrigação = soma dos câmbios rateados nas alocações (não P&L)."""
    alloc_ids = [
        a.id
        for a in db.query(PaymentAllocation).filter(PaymentAllocation.payable_id == payable_id).all()
    ]
    if not alloc_ids:
        return money2(Decimal("0"))
    raw = (
        db.query(func.coalesce(func.sum(FxExecutionAllocation.brl_amount), 0))
        .filter(FxExecutionAllocation.payment_allocation_id.in_(alloc_ids))
        .scalar()
    )
    return money2(Decimal(str(raw)))


def order_fx_cost(db: Session, order_id: int) -> dict:
    """Custo BRL do pedido = soma de todas as FxExecution dos pagamentos REGISTERED."""
    rows = (
        db.query(FxExecution)
        .join(Payment, Payment.id == FxExecution.payment_id)
        .filter(Payment.order_id == order_id, Payment.status == "REGISTERED")
        .all()
    )
    total_eur = money2(sum((r.foreign_amount for r in rows), Decimal("0")))
    total_brl = money2(sum((r.brl_amount for r in rows), Decimal("0")))
    avg = weighted_rate(total_eur, total_brl)
    return {
        "cost_eur": decimal_str(total_eur) or "0",
        "cost_brl": decimal_str(total_brl) or "0",
        "weighted_avg_rate": decimal_str(avg) if avg is not None else None,
        "execution_count": len(rows),
    }


def payable_fx_view(db: Session, payable_id: int) -> dict:
    payable = billing_public.get_payable(db, payable_id)
    initial = get_initial_plan(db, payable_id)
    current = get_current_plan(db, payable_id)
    history = list_plan_history(db, payable_id)
    quote = get_latest_quote(db, payable.currency)
    status = quote_status(quote)
    open_foreign = money2(payable.balance)

    market_rate = quote.rate if quote else None
    projected_open = to_brl(open_foreign, current.rate) if current else None
    market_open = to_brl(open_foreign, market_rate) if market_rate is not None else None
    online_cur = (
        online_result_vs_current(open_foreign, current.rate, market_rate)
        if current and market_rate is not None
        else None
    )
    online_ini = (
        online_result_vs_initial(open_foreign, initial.rate, market_rate)
        if initial and market_rate is not None
        else None
    )

    # Sum realized valuations for this payable's allocations
    alloc_ids = [
        a.id
        for a in db.query(PaymentAllocation).filter(PaymentAllocation.payable_id == payable_id).all()
    ]
    vals = []
    if alloc_ids:
        vals = (
            db.query(FxAllocationValuation)
            .filter(FxAllocationValuation.payment_allocation_id.in_(alloc_ids))
            .all()
        )
    realized_vs_ref = money2(sum((v.realized_result_vs_reference for v in vals), Decimal("0"))) if vals else None
    realized_brl_sum = money2(sum((v.realized_brl for v in vals), Decimal("0"))) if vals else None
    cost_brl = payable_cost_brl(db, payable_id)
    settled = money2(sum((v.foreign_amount_snapshot for v in vals), Decimal("0"))) if vals else Decimal("0")
    realized_vs_ini = None
    if vals and initial:
        realized_vs_ini = money2(
            sum(
                (
                    realized_result_vs_initial(
                        v.foreign_amount_snapshot, initial.rate, v.realized_rate_snapshot
                    )
                    for v in vals
                ),
                Decimal("0"),
            )
        )

    total_cur = None
    if realized_vs_ref is not None and online_cur is not None:
        total_cur = money2(realized_vs_ref + online_cur)
    total_ini = None
    if realized_vs_ini is not None and online_ini is not None:
        total_ini = money2(realized_vs_ini + online_ini)

    return {
        "payable_id": payable_id,
        "currency": payable.currency,
        "open_foreign": decimal_str(open_foreign),
        "initial_planned_rate": decimal_str(initial.rate) if initial else None,
        "current_forecast_rate": decimal_str(current.rate) if current else None,
        "plan_history": [
            {
                "id": h.id,
                "kind": h.kind,
                "rate": decimal_str(h.rate),
                "version": h.version,
                "is_current": h.is_current,
                "effective_from": h.effective_from.isoformat(),
            }
            for h in history
        ],
        "market": {
            "rate": decimal_str(market_rate) if market_rate is not None else None,
            "status": status,
            "stale": status == "stale",
            "source": quote.source if quote else None,
            "observed_at": quote.observed_at.isoformat() if quote else None,
            "retrieved_at": quote.retrieved_at.isoformat() if quote else None,
        },
        "projected_open_brl": decimal_str(projected_open),
        "market_open_brl": decimal_str(market_open),
        "online_result_vs_current": decimal_str(online_cur),
        "online_result_vs_initial": decimal_str(online_ini),
        "settled_foreign": decimal_str(settled) if vals else "0",
        "cost_brl": decimal_str(cost_brl) or "0",
        "realized_brl": decimal_str(realized_brl_sum),
        "realized_result_vs_reference": decimal_str(realized_vs_ref) if vals else None,
        "realized_result_vs_initial": decimal_str(realized_vs_ini),
        "total_vs_current": decimal_str(total_cur),
        "total_vs_initial": decimal_str(total_ini),
        "benchmarks": {
            "realized_result_vs_reference": "frozen_reference",
            "realized_result_vs_initial": "initial",
            "online_result_vs_current": "current",
            "online_result_vs_initial": "initial",
            "total_vs_current": "current",
            "total_vs_initial": "initial",
        },
    }


def payment_fx_view(db: Session, payment_id: int) -> dict:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        from app.treasury.errors import PaymentNotFound

        raise PaymentNotFound(payment_id)
    executions = list_executions(db, payment_id)
    allocs = (
        db.query(PaymentAllocation).filter(PaymentAllocation.payment_id == payment_id).all()
    )
    lines = []
    for a in allocs:
        val = (
            db.query(FxAllocationValuation)
            .filter(FxAllocationValuation.payment_allocation_id == a.id)
            .first()
        )
        links = (
            db.query(FxExecutionAllocation)
            .filter(FxExecutionAllocation.payment_allocation_id == a.id)
            .all()
        )
        initial = get_initial_plan(db, a.payable_id)
        vs_ini = None
        if val and initial:
            vs_ini = realized_result_vs_initial(
                val.foreign_amount_snapshot, initial.rate, val.realized_rate_snapshot
            )
        lines.append(
            {
                "allocation_id": a.id,
                "payable_id": a.payable_id,
                "foreign_amount": decimal_str(a.amount),
                "valuation": None
                if not val
                else {
                    "id": val.id,
                    "planned_rate_used_at_realization": decimal_str(val.planned_rate_snapshot),
                    "realized_rate": decimal_str(val.realized_rate_snapshot),
                    "realized_brl": decimal_str(val.realized_brl),
                    "realized_result_vs_reference": decimal_str(val.realized_result_vs_reference),
                    "realized_result_vs_initial": decimal_str(vs_ini),
                    "reference_kind": val.reference_kind,
                    "benchmark_reference": "frozen_reference",
                },
                "execution_links": [
                    {
                        "id": l.id,
                        "fx_execution_id": l.fx_execution_id,
                        "foreign_amount": decimal_str(l.foreign_amount),
                        "brl_amount": decimal_str(l.brl_amount),
                    }
                    for l in links
                ],
            }
        )
    return {
        "payment_id": payment_id,
        "currency": payment.currency,
        "amount": decimal_str(payment.amount),
        "executions": [
            {
                "id": e.id,
                "foreign_amount": decimal_str(e.foreign_amount),
                "brl_amount": decimal_str(e.brl_amount),
                "rate": decimal_str(e.rate),
                "execution_date": e.execution_date.isoformat(),
            }
            for e in executions
        ],
        "allocations": lines,
    }
