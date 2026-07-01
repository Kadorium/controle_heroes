"""Campos derivados de câmbio/BRL para UI — recalculados fresh a cada request (sem cache)."""

from __future__ import annotations

from decimal import Decimal

from app.core.currency import normalize_import_currency
from app.models import Invoice, Payment
from app.services.finance import _payment_is_settled

_D0 = Decimal("0")


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else _D0


def resolve_display_rate(
    payment: Payment,
    invoice: Invoice,
    opening_provision: Decimal | None,
) -> tuple[Decimal | None, str]:
    """
    Retorna (taxa, tipo): effective | provision | none.
    Câmbio efetivo só em pagamento BRL com exchange_rate (liquidação cambial BR).
    """
    pay_cur = normalize_import_currency(payment.currency_foreign or invoice.currency)
    if (
        pay_cur == "BRL"
        and payment.exchange_rate is not None
        and payment.exchange_rate > 0
    ):
        return payment.exchange_rate, "effective"
    if invoice.expected_exchange_rate is not None and invoice.expected_exchange_rate > 0:
        return invoice.expected_exchange_rate, "provision"
    if opening_provision is not None and opening_provision > 0:
        return opening_provision, "provision"
    return None, "none"


def compute_payment_display(
    payment: Payment,
    invoice: Invoice,
    opening_provision: Decimal | None,
) -> dict:
    """display_brl/display_rate derivados — nunca divide por zero."""
    rate, rate_type = resolve_display_rate(payment, invoice, opening_provision)
    pay_cur = normalize_import_currency(payment.currency_foreign or invoice.currency)

    display_brl: Decimal | None = None
    brl_is_estimated = False

    if payment.amount_local is not None:
        display_brl = payment.amount_local
        brl_is_estimated = False
    elif payment.amount_foreign is not None and rate is not None and rate > 0:
        if pay_cur == "BRL":
            display_brl = payment.amount_foreign
            brl_is_estimated = payment.exchange_rate is None
        else:
            display_brl = _d(payment.amount_foreign) * rate
            brl_is_estimated = payment.exchange_rate is None

    brl_str = None
    if display_brl is not None:
        brl_str = str(display_brl.quantize(Decimal("0.01")))

    return {
        "display_rate": str(rate) if rate is not None else None,
        "display_rate_type": rate_type,
        "display_brl": brl_str,
        "brl_is_estimated": brl_is_estimated,
        "is_settled": _payment_is_settled(payment),
    }


def compute_open_fx_exposure_brl(
    db,
    importation_id: int,
    *,
    provision: Decimal | None,
    settled_brl_real: Decimal,
) -> str | None:
    """Exposição cambial aberta: EUR liquidado sem perna BRL efetiva × provisão."""
    if provision is None or provision <= 0:
        return None
    from app.models import Invoice, Payment
    from app.services.finance import invoice_paid_total

    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True))
        .all()
    )
    eur_settled_no_brl = _D0
    for inv in invoices:
        for pay in inv.payments:
            if not pay.is_active or pay.amount_foreign is None:
                continue
            pay_cur = normalize_import_currency(pay.currency_foreign or inv.currency)
            if pay_cur != "EUR" or not _payment_is_settled(pay):
                continue
            if pay.exchange_rate is None and pay.amount_local is None:
                eur_settled_no_brl += _d(pay.amount_foreign)
    if eur_settled_no_brl <= _D0:
        return None
    exposure = eur_settled_no_brl * provision - settled_brl_real
    return str(exposure) if exposure > _D0 else "0"
