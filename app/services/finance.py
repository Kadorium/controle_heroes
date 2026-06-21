from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import DEFAULT_IMPORT_CURRENCY
from app.core.enums import CreditStatus, ExchangeRateType
from app.models import (
    BrazilCurrentAccount,
    Credit,
    CreditUsage,
    Discount,
    ExchangeRate,
    ImportationOrder,
    Invoice,
    Payment,
)
from app.services.auth import write_audit_log


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _payment_is_settled(p: Payment) -> bool:
    """Pagamento efetivado — distinto de planejado (só due_date, sem liquidação)."""
    return (
        p.payment_date is not None
        or bool(p.receipt_reference)
        or p.approved_without_receipt
    )


def invoice_discount_total(db: Session, invoice: Invoice) -> Decimal:
    total = _d(invoice.discount_amount)
    discounts = (
        db.query(Discount)
        .filter(Discount.invoice_id == invoice.id, Discount.is_active.is_(True))
        .all()
    )
    for d in discounts:
        total += _d(d.amount)
    return total


def invoice_paid_total(db: Session, invoice: Invoice) -> Decimal:
    payments = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice.id, Payment.is_active.is_(True))
        .all()
    )
    # Planejados não liquidados não reduzem saldo.
    return sum(_d(p.amount_foreign) for p in payments if _payment_is_settled(p))


def invoice_balance(db: Session, invoice: Invoice) -> Decimal | None:
    if invoice.amount is None:
        return None
    gross = invoice.amount
    discounts = invoice_discount_total(db, invoice)
    paid = invoice_paid_total(db, invoice)
    return gross - discounts - paid


def importation_financial_summary(db: Session, importation: ImportationOrder) -> dict:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == importation.id, Invoice.is_active.is_(True))
        .all()
    )
    total_invoiced = Decimal("0")
    total_paid = Decimal("0")
    total_discounts = Decimal("0")
    total_balance = Decimal("0")
    has_null_amount = False
    invoice_summaries = []

    for inv in invoices:
        paid = invoice_paid_total(db, inv)
        disc = invoice_discount_total(db, inv)
        bal = invoice_balance(db, inv)
        if inv.amount is not None:
            total_invoiced += inv.amount
            total_balance += bal if bal is not None else Decimal("0")
        else:
            has_null_amount = True
        total_paid += paid
        total_discounts += disc
        invoice_summaries.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_type": inv.invoice_type,
                "amount": str(inv.amount) if inv.amount is not None else None,
                "paid": str(paid),
                "discounts": str(disc),
                "balance": str(bal) if bal is not None else None,
            }
        )

    consolidated_balance = None if has_null_amount else total_invoiced - total_discounts - total_paid

    return {
        "importation_id": importation.id,
        "currency": importation.currency,
        "total_invoiced": str(total_invoiced),
        "total_paid": str(total_paid),
        "total_discounts": str(total_discounts),
        "consolidated_balance": str(consolidated_balance) if consolidated_balance is not None else None,
        "invoices": invoice_summaries,
    }


def register_exchange_rate(
    db: Session,
    *,
    currency_from: str,
    rate_type: str,
    rate_value: Decimal | None,
    user_id: int | None,
    importation_id: int | None = None,
    invoice_id: int | None = None,
    payment_id: int | None = None,
    comment: str | None = None,
) -> ExchangeRate:
    rate = ExchangeRate(
        currency_from=currency_from,
        currency_to="BRL",
        rate_type=rate_type,
        rate_value=rate_value,
        importation_id=importation_id,
        invoice_id=invoice_id,
        payment_id=payment_id,
        registered_by_id=user_id,
        comment=comment,
    )
    db.add(rate)
    db.flush()
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="exchange_rate",
        entity_id=str(rate.id),
        action="create",
        field_changed="rate_value",
        new_value=str(rate_value) if rate_value is not None else None,
        justification=comment,
    )
    db.commit()
    db.refresh(rate)
    return rate


def apply_credit(
    db: Session,
    credit: Credit,
    *,
    importation_id: int,
    invoice_id: int | None,
    amount: Decimal,
    user_id: int | None,
) -> CreditUsage:
    if credit.status in (CreditStatus.USED.value, CreditStatus.CANCELLED.value):
        raise ValueError("Crédito indisponível")
    if amount <= 0:
        raise ValueError("Valor deve ser positivo")
    if amount > credit.amount_available:
        raise ValueError("Valor excede saldo disponível do crédito")

    existing = (
        db.query(CreditUsage)
        .filter(
            CreditUsage.credit_id == credit.id,
            CreditUsage.importation_id == importation_id,
            CreditUsage.invoice_id == invoice_id,
        )
        .first()
    )
    if existing:
        raise ValueError("Crédito já utilizado nesta importação/invoice")

    usage = CreditUsage(
        credit_id=credit.id,
        importation_id=importation_id,
        invoice_id=invoice_id,
        amount_used=amount,
        used_by_id=user_id,
    )
    credit.amount_used += amount
    credit.amount_available -= amount
    if credit.amount_available == 0:
        credit.status = CreditStatus.USED.value
    elif credit.amount_used > 0:
        credit.status = CreditStatus.PARTIAL.value
    credit.used_in_importation_id = importation_id

    db.add(usage)
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="credit",
        entity_id=str(credit.id),
        action="apply",
        field_changed="amount_used",
        new_value=str(amount),
    )
    db.commit()
    db.refresh(usage)
    return usage


def payments_due_summary(db: Session, *, window_days: int = 7) -> dict:
    """Pagamentos planejados (payment_date null) com due_date; exige invoice com saldo aberto."""
    today = date.today()
    window_end = today + timedelta(days=window_days)

    planned = (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(
            Payment.is_active.is_(True),
            Invoice.is_active.is_(True),
            Payment.payment_date.is_(None),
            Payment.due_date.isnot(None),
            Payment.receipt_reference.is_(None),
            Payment.approved_without_receipt.is_(False),
        )
        .all()
    )

    due_soon: list[Payment] = []
    overdue: list[Payment] = []
    amount_by_currency: dict[str, Decimal] = {}

    for p in planned:
        bal = invoice_balance(db, p.invoice)
        if bal is not None and bal <= Decimal("0"):
            continue
        if p.due_date < today:
            overdue.append(p)
        elif p.due_date <= window_end:
            due_soon.append(p)
            if p.amount_foreign is not None:
                cur = p.currency_foreign or p.invoice.currency or DEFAULT_IMPORT_CURRENCY
                amount_by_currency[cur] = amount_by_currency.get(cur, Decimal("0")) + p.amount_foreign

    return {
        "window_days": window_days,
        "due_count": len(due_soon),
        "overdue_count": len(overdue),
        "due_amount_by_currency": {k: str(v) for k, v in sorted(amount_by_currency.items())},
        "has_data": (
            db.query(Payment)
            .filter(Payment.is_active.is_(True), Payment.due_date.isnot(None))
            .count()
            > 0
        ),
    }
