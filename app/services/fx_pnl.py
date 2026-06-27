"""PnL Cambial operacional — variação BRL vs câmbio provisionado na abertura (não contábil)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.currency import normalize_import_currency
from app.models import ExchangeRate, ImportationOrder, Invoice, Payment
from app.services.finance import _payment_is_settled, importation_financial_summary

_D0 = Decimal("0")


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else _D0


def _get_provision_rate(db: Session, importation_id: int) -> Decimal | None:
    row = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.importation_id == importation_id,
            ExchangeRate.rate_type == "OPENING_PROVISION",
            ExchangeRate.rate_value.isnot(None),
        )
        .order_by(ExchangeRate.created_at.asc())
        .first()
    )
    if row and row.rate_value is not None:
        return row.rate_value
    inv = (
        db.query(Invoice)
        .filter(
            Invoice.importation_id == importation_id,
            Invoice.is_active.is_(True),
            Invoice.expected_exchange_rate.isnot(None),
        )
        .order_by(Invoice.created_at.asc())
        .first()
    )
    if inv and inv.expected_exchange_rate is not None:
        return inv.expected_exchange_rate
    return None


def _eur_from_brl_payment(pay: Payment, fallback_rate: Decimal | None) -> Decimal | None:
    if pay.amount_foreign is None:
        return None
    brl = pay.amount_foreign
    rate = pay.exchange_rate or fallback_rate
    if rate is None or rate == 0:
        return None
    return brl / rate


def compute_fx_pnl(
    db: Session,
    importation_id: int,
    *,
    mark_rate: Decimal | None = None,
) -> dict:
    """
    PnL Cambial operacional (BRL).
    Positivo = economia vs provisão; negativo = custo cambial extra.
    Não é resultado contábil oficial.
    """
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ValueError("Importação não encontrada")

    provision = _get_provision_rate(db, importation_id)
    if provision is None:
        return _empty_pnl()

    financial = importation_financial_summary(db, imp)
    open_bal_raw = financial.get("consolidated_balance")
    open_eur = Decimal(open_bal_raw) if open_bal_raw is not None else None

    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True))
        .all()
    )

    pnl_realized = _D0
    pnl_planned = _D0
    has_realized = False
    has_planned = False

    for inv in invoices:
        inv_rate = inv.expected_exchange_rate or provision
        for pay in inv.payments:
            if not pay.is_active or pay.amount_foreign is None:
                continue
            pay_cur = normalize_import_currency(pay.currency_foreign or inv.currency)
            if pay_cur != "BRL":
                continue
            brl = pay.amount_foreign
            rate_for_eur = pay.exchange_rate if _payment_is_settled(pay) else inv_rate
            eur = _eur_from_brl_payment(pay, rate_for_eur)
            if eur is None:
                continue
            brl_at_provision = eur * provision
            delta = brl_at_provision - brl
            if _payment_is_settled(pay):
                pnl_realized += delta
                has_realized = True
            elif pay.due_date is not None:
                pnl_planned += delta
                has_planned = True

    pnl_unrealized = None
    if open_eur is not None and open_eur != 0 and mark_rate is not None:
        pnl_unrealized = open_eur * (provision - mark_rate)

    parts = []
    if has_realized:
        parts.append(pnl_realized)
    if has_planned:
        parts.append(pnl_planned)
    if pnl_unrealized is not None:
        parts.append(pnl_unrealized)
    pnl_total = sum(parts) if parts else None

    return {
        "label": "PnL Cambial",
        "disclaimer": "Variação cambial operacional vs provisão de abertura — não é resultado contábil.",
        "provision_rate": str(provision),
        "mark_rate": str(mark_rate) if mark_rate is not None else None,
        "pnl_realized_brl": str(pnl_realized) if has_realized else None,
        "pnl_planned_brl": str(pnl_planned) if has_planned else None,
        "pnl_unrealized_brl": str(pnl_unrealized) if pnl_unrealized is not None else None,
        "pnl_total_brl": str(pnl_total) if pnl_total is not None else None,
    }


def _empty_pnl() -> dict:
    return {
        "label": "PnL Cambial",
        "disclaimer": "Variação cambial operacional vs provisão de abertura — não é resultado contábil.",
        "provision_rate": None,
        "mark_rate": None,
        "pnl_realized_brl": None,
        "pnl_planned_brl": None,
        "pnl_unrealized_brl": None,
        "pnl_total_brl": None,
    }


def aggregate_fx_pnl(db: Session, importation_ids: list[int], *, mark_rate: Decimal | None = None) -> dict:
    total_realized = _D0
    total_planned = _D0
    total_unrealized = _D0
    has_r = has_p = has_u = False
    count = 0
    for iid in importation_ids:
        row = compute_fx_pnl(db, iid, mark_rate=mark_rate)
        if row["pnl_total_brl"] is None and row["provision_rate"] is None:
            continue
        count += 1
        if row["pnl_realized_brl"] is not None:
            total_realized += Decimal(row["pnl_realized_brl"])
            has_r = True
        if row["pnl_planned_brl"] is not None:
            total_planned += Decimal(row["pnl_planned_brl"])
            has_p = True
        if row["pnl_unrealized_brl"] is not None:
            total_unrealized += Decimal(row["pnl_unrealized_brl"])
            has_u = True
    total_parts = []
    if has_r:
        total_parts.append(total_realized)
    if has_p:
        total_parts.append(total_planned)
    if has_u:
        total_parts.append(total_unrealized)
    return {
        "label": "PnL Cambial",
        "disclaimer": "Variação cambial operacional consolidada — não é resultado contábil.",
        "orders_with_pnl": count,
        "pnl_realized_brl": str(total_realized) if has_r else None,
        "pnl_planned_brl": str(total_planned) if has_p else None,
        "pnl_unrealized_brl": str(total_unrealized) if has_u else None,
        "pnl_total_brl": str(sum(total_parts)) if total_parts else None,
    }
