"""Customs-origin Payable helpers — Billing public surface (I5-3B).

Customs chama via billing.public; Billing NÃO importa Customs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing.errors import PayableNotFound, PayableValidationError
from app.billing.models import Payable
from app.billing.money import money2, parse_decimal

SOURCE_CUSTOMS_FUNDING = "CUSTOMS_FUNDING"


def create_customs_payable_from_funding(
    db: Session,
    *,
    funding_request_id: int,
    source_id: int,
    sequence: int,
    due_date: date,
    amount: Decimal | str,
    currency: str,
    payee_display_name: str,
    idempotent: bool = True,
) -> Payable:
    """Cria Payable origem CUSTOMS_FUNDING (invoice_id/payment_term_id nulos).

    Idempotente por (source_type, source_id, sequence) quando idempotent=True.
    """
    cur = (currency or "").strip().upper()
    if not cur:
        raise PayableValidationError("Moeda do payable Customs é obrigatória")
    name = (payee_display_name or "").strip()
    if not name:
        raise PayableValidationError("payee_display_name é obrigatório para payable Customs")
    if len(name) > 256:
        raise PayableValidationError("payee_display_name excede 256 caracteres")

    amt = parse_decimal(amount) if not isinstance(amount, Decimal) else amount
    if amt is None or amt <= 0:
        raise PayableValidationError("Valor do payable Customs deve ser > 0")
    amt = money2(amt)

    src = int(source_id)
    seq = int(sequence)
    if seq < 1:
        raise PayableValidationError("sequence do payable Customs deve ser >= 1")

    existing = (
        db.query(Payable)
        .filter(
            Payable.source_type == SOURCE_CUSTOMS_FUNDING,
            Payable.source_id == src,
            Payable.sequence == seq,
        )
        .first()
    )
    if existing is not None:
        if idempotent:
            return existing
        raise PayableValidationError(
            f"Payable Customs já existe para funding #{funding_request_id} seq={seq}"
        )

    row = Payable(
        invoice_id=None,
        payment_term_id=None,
        sequence=seq,
        due_date=due_date,
        amount=amt,
        balance=amt,
        currency=cur,
        status="OPEN",
        source_type=SOURCE_CUSTOMS_FUNDING,
        source_id=src,
        payee_display_name=name,
        version=1,
    )
    db.add(row)
    db.flush()
    return row


def cancel_customs_payable(db: Session, payable_id: int) -> Payable:
    """Cancela payable Customs somente se OPEN e sem liquidação (balance == amount)."""
    row = db.query(Payable).filter(Payable.id == payable_id).with_for_update().first()
    if not row:
        raise PayableNotFound(payable_id)
    if row.source_type != SOURCE_CUSTOMS_FUNDING:
        raise PayableValidationError(
            f"Payable #{payable_id} não é origem CUSTOMS_FUNDING"
        )
    if row.status == "CANCELLED":
        return row
    if row.status in ("PARTIALLY_PAID", "PAID") or row.balance < row.amount:
        raise PayableValidationError(
            f"Payable Customs #{payable_id} já parcialmente liquidado — cancelamento bloqueado"
        )
    if row.status != "OPEN":
        raise PayableValidationError(
            f"Payable Customs #{payable_id} não pode ser cancelado (status {row.status})"
        )
    if row.balance != row.amount:
        raise PayableValidationError(
            f"Payable Customs #{payable_id} tem saldo diferente do valor — cancelamento bloqueado"
        )
    row.status = "CANCELLED"
    db.flush()
    return row
