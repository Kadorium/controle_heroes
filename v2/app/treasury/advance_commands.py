"""J4-FIN FIN-1 — adiantamento (Payment + order_id + FxExecution).

Crédito: NÃO cria Payable. N Payments por Order; consolidado = soma EUR,
soma BRL (brl_amount) e câmbio médio ponderado.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.documents import public as documents_public
from app.orders import public as orders_public
from app.orders.public import OrdersError
from app.treasury import fx_commands as fx
from app.treasury.commands import (
    amount_unallocated,
    cancel_payment,
    get_payment,
    list_payments,
    money2,
    parse_decimal,
    register_payment,
)
from app.treasury.errors import PaymentValidationError
from app.treasury.fx_money import rate6, weighted_rate
from app.treasury.fx_models import FxExecution
from app.treasury.models import PURPOSE_ADVANCE, Payment


def register_order_advance(
    db: Session,
    *,
    order_id: int,
    amount: str | Decimal,
    payment_date: date,
    execution_date: date,
    created_by_actor_id: str,
    rate: str | Decimal | None = None,
    brl_amount: str | Decimal | None = None,
    currency: str | None = None,
    external_reference: str | None = None,
    idempotency_key: str | None = None,
    register_without_fx_document: bool = True,
) -> tuple[Payment, FxExecution]:
    """Registra 1 Payment (crédito no pedido) + 1 FxExecution.

    Arredondamento: se EUR+BRL → ambos SoT, taxa derivada;
    se EUR+taxa → BRL derivado (operador pode sobrescrever enviando BRL).
    """
    try:
        order = orders_public.get_order(db, order_id)
    except OrdersError as e:
        raise PaymentValidationError(getattr(e, "message", str(e))) from e

    if order.status == "CANCELLED":
        raise PaymentValidationError("Pedido cancelado não aceita adiantamento")

    cur = (currency or order.currency or "EUR").strip().upper()
    if cur != order.currency.upper():
        raise PaymentValidationError(
            f"Moeda do adiantamento ({cur}) deve ser a do pedido ({order.currency})"
        )

    amt = money2(parse_decimal(amount) or Decimal("0"))
    if amt <= 0:
        raise PaymentValidationError("Valor do adiantamento deve ser > 0")
    if rate is None and brl_amount is None:
        raise PaymentValidationError("Informe rate ou brl_amount (câmbio)")

    payment = register_payment(
        db,
        supplier_id=order.supplier_id,
        amount=amt,
        currency=cur,
        payment_date=payment_date,
        created_by_actor_id=created_by_actor_id,
        external_reference=external_reference,
        idempotency_key=idempotency_key,
        allow_without_document=True,
        order_id=order.id,
        purpose=PURPOSE_ADVANCE,
    )

    execution = fx.register_execution(
        db,
        payment_id=payment.id,
        foreign_amount=amt,
        brl_amount=brl_amount,
        rate=rate,
        execution_date=execution_date,
        created_by_actor_id=created_by_actor_id,
        external_reference=external_reference,
        register_without_document=register_without_fx_document,
        idempotency_key=f"adv-fx-{idempotency_key}" if idempotency_key else None,
        enforce_single_app_limit=True,
    )
    return get_payment(db, payment.id), execution


def _payment_row(db: Session, pay: Payment) -> dict:
    executions = fx.list_executions(db, pay.id)
    ex = executions[0] if executions else None
    fx_docs = []
    if ex:
        fx_docs = [
            {"id": d.id, "original_filename": d.original_filename}
            for d in documents_public.list_by_entity(db, "fx_execution", str(ex.id))
        ]
    return {
        "payment_id": pay.id,
        "purpose": pay.purpose,
        "amount": format(money2(pay.amount), "f"),
        "currency": pay.currency,
        "payment_date": pay.payment_date.isoformat(),
        "external_reference": pay.external_reference,
        "status": pay.status,
        "version": pay.version,
        "fx_execution_id": ex.id if ex else None,
        "foreign_amount": format(money2(ex.foreign_amount), "f") if ex else None,
        "brl_amount": format(money2(ex.brl_amount), "f") if ex else None,
        "rate": format(rate6(ex.rate), "f") if ex else None,
        "execution_date": ex.execution_date.isoformat() if ex else None,
        "amount_unallocated": format(amount_unallocated(db, pay), "f"),
        "fx_documents": fx_docs,
        "_fx": ex,
    }


def list_order_advances(db: Session, order_id: int) -> dict:
    """Adiantamentos (crédito) vs pagamentos de saldo do mesmo pedido.

    Adiantamento = Payment.purpose ADVANCE (nasce no painel de adiantamento).
    Continua adiantamento depois de aplicado. Pagamento de saldo = SETTLEMENT.
    """
    try:
        order = orders_public.get_order(db, order_id)
    except OrdersError as e:
        raise PaymentValidationError(getattr(e, "message", str(e))) from e

    payments = list_payments(
        db, order_id=order_id, status="REGISTERED", limit=200, offset=0
    )
    advances: list[dict] = []
    settlements: list[dict] = []
    total_eur = Decimal("0")
    total_brl = Decimal("0")

    for pay in payments:
        if pay.order_id != order_id:
            continue
        row = _payment_row(db, pay)
        ex = row.pop("_fx")
        if pay.purpose == PURPOSE_ADVANCE:
            if ex:
                total_eur += money2(ex.foreign_amount)
                total_brl += money2(ex.brl_amount)
            else:
                total_eur += money2(pay.amount)
            advances.append(row)
        else:
            settlements.append(row)

    avg = weighted_rate(total_eur, total_brl)
    return {
        "order_id": order.id,
        "order_code": order.code,
        "currency": order.currency,
        "advances": advances,
        "settlements": settlements,
        "consolidated": {
            "total_eur": format(money2(total_eur), "f"),
            "total_brl": format(money2(total_brl), "f"),
            "weighted_avg_rate": format(avg, "f") if avg is not None else None,
            "count": len(advances),
        },
    }


def cancel_order_advance(
    db: Session,
    *,
    order_id: int,
    payment_id: int,
    expected_version: int,
    reason: str,
) -> tuple[Payment, list[FxExecution]]:
    """Cancela adiantamento (Payment CANCELLED). FxExecution preservada; ativa só se Payment REGISTERED."""
    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise PaymentValidationError("Motivo do cancelamento é obrigatório")

    try:
        orders_public.get_order(db, order_id)
    except OrdersError as e:
        raise PaymentValidationError(getattr(e, "message", str(e))) from e

    payment = get_payment(db, payment_id)
    if payment.order_id != order_id:
        raise PaymentValidationError("Pagamento não pertence a este pedido")
    if payment.purpose != PURPOSE_ADVANCE:
        raise PaymentValidationError("Pagamento não é adiantamento de pedido")

    payment = cancel_payment(
        db,
        payment_id,
        expected_version=expected_version,
        reason_code=reason_clean[:64],
    )
    executions = fx.list_executions(db, payment_id)
    return get_payment(db, payment_id), executions


def fx_void_audit_payloads(payment: Payment, executions: list[FxExecution], *, reason: str) -> list[dict]:
    """Snapshots para Audit — FX não é apagada; void por cancel do Payment."""
    out: list[dict] = []
    for ex in executions:
        out.append(
            {
                "fx_execution_id": ex.id,
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "eur": format(money2(ex.foreign_amount), "f"),
                "brl": format(money2(ex.brl_amount), "f"),
                "rate": format(rate6(ex.rate), "f"),
                "execution_date": ex.execution_date.isoformat(),
                "motivo": reason.strip(),
            }
        )
    return out
