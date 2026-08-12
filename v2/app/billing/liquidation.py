"""Liquidação de Payables — ownership Billing (Inc-3)."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import repository as repo
from app.billing.errors import PayableConflict, PayableNotFound, PayableValidationError
from app.billing.models import Invoice, Payable
from app.billing.money import money2, parse_decimal


def _status_for_balance(amount: Decimal, balance: Decimal) -> str:
    if balance <= 0:
        return "PAID"
    if balance < amount:
        return "PARTIALLY_PAID"
    return "OPEN"


def apply_payable_allocations(
    db: Session,
    applications: list[dict],
) -> list[Payable]:
    """Aplica valores aos Payables (ordem determinística por payable_id).

    Cada item: {payable_id, amount, expected_version}.
    Não cria PaymentAllocation. Locks FOR UPDATE + optimistic version → conflict.
    """
    if not applications:
        raise PayableValidationError("Informe ao menos uma aplicação")

    # Aggregate same payable in one batch call is forbidden — require unique ids
    ids = [int(a["payable_id"]) for a in applications]
    if len(ids) != len(set(ids)):
        raise PayableValidationError("Payable duplicado no mesmo lote")

    # Deterministic lock order
    ordered = sorted(applications, key=lambda a: int(a["payable_id"]))
    updated: list[Payable] = []
    for raw in ordered:
        payable_id = int(raw["payable_id"])
        expected_version = int(raw["expected_version"])
        amount = parse_decimal(raw["amount"])
        if amount is None or amount <= 0:
            raise PayableValidationError("Valor de alocação deve ser > 0")
        amount = money2(amount)

        row = repo.get_payable_for_update(db, payable_id)
        if not row:
            raise PayableNotFound(payable_id)
        if row.invoice_id is None:
            raise PayableValidationError(
                f"Payable #{payable_id} sem fatura (origem {row.source_type}) "
                "não é elegível para alocação via Payment atual"
            )
        if row.status in ("PAID", "CANCELLED"):
            raise PayableValidationError(
                f"Payable #{payable_id} não aceita liquidação (status {row.status})"
            )

        if amount > row.balance:
            raise PayableValidationError(
                f"Valor {amount} excede saldo {row.balance} do payable #{payable_id}"
            )
        if not repo.bump_payable_version_if_match(db, payable_id, expected_version):
            raise PayableConflict(payable_id)

        row = repo.get_payable(db, payable_id)
        assert row is not None
        row.balance = money2(row.balance - amount)
        row.status = _status_for_balance(row.amount, row.balance)
        db.flush()
        updated.append(row)
    return updated


def list_eligible_payables(
    db: Session,
    *,
    supplier_id: int,
    currency: str,
    order_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Payable]:
    """Payables liquidáveis: mesmo supplier/moeda; exclui PAID e CANCELLED.

    I5-3B: INNER JOIN Invoice — payables CUSTOMS_FUNDING (invoice_id NULL)
    ficam visíveis na AP mas NÃO elegíveis para alocação Payment (gap intencional).
    Se order_id informado (crédito do pedido), restringe à Invoice desse Order.
    """
    cur = (currency or "").strip().upper()
    q = (
        db.query(Payable)
        .join(Invoice, Invoice.id == Payable.invoice_id)
        .filter(
            Invoice.supplier_id == supplier_id,
            Payable.currency == cur,
            Payable.status.in_(("OPEN", "PARTIALLY_PAID")),
            Payable.balance > 0,
        )
    )
    if order_id is not None:
        q = q.filter(Invoice.order_id == order_id)
    q = q.order_by(Payable.due_date.asc(), Payable.id.asc()).offset(offset).limit(limit)
    return list(q.all())
