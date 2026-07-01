"""Fila global de contas a pagar — agregado por ordem para /financeiro."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.core.currency import normalize_import_currency
from app.models import ImportationOrder, Invoice, Payment, Supplier
from app.services.finance import (
    _payment_is_settled,
    importation_financial_summary,
    invoice_balance,
    invoice_effective_amount,
    payments_due_summary,
)
from app.services.finance_display import compute_open_fx_exposure_brl, compute_payment_display
from app.services.fx_pnl import _get_provision_rate, aggregate_fx_pnl, compute_fx_pnl
from app.services.order_central import _build_finance_operational

_D0 = Decimal("0")


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else _D0


def _payment_status_label(payment: Payment) -> str:
    if _payment_is_settled(payment):
        return "Liquidado"
    if payment.due_date is not None:
        return "Planejado"
    return "Pendente"


def build_payables_queue(
    db: Session,
    *,
    supplier_id: int | None = None,
    importation_id: int | None = None,
    status_filter: str | None = None,
    invoice_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    mark_rate: Decimal | None = None,
) -> dict:
    q = db.query(ImportationOrder).filter(ImportationOrder.is_active.is_(True))
    if importation_id is not None:
        q = q.filter(ImportationOrder.id == importation_id)
    if supplier_id is not None:
        q = q.filter(ImportationOrder.supplier_id == supplier_id)
    orders = q.order_by(ImportationOrder.created_at.desc()).all()

    supplier_map = {s.id: s.name for s in db.query(Supplier).filter(Supplier.is_active.is_(True)).all()}

    order_blocks: list[dict] = []
    kpi_settled = _D0
    kpi_pending = _D0
    kpi_due7 = _D0
    kpi_due7_count = 0
    kpi_overdue = 0
    kpi_exposure = _D0
    imp_ids: list[int] = []

    today = date.today()
    in7 = today + timedelta(days=7)

    for imp in orders:
        provision = _get_provision_rate(db, imp.id)
        financial = importation_financial_summary(db, imp)
        finance_ops = _build_finance_operational(db, imp, financial, mark_rate=mark_rate)
        fx_pnl = compute_fx_pnl(db, imp.id, mark_rate=mark_rate)

        invoices = (
            db.query(Invoice)
            .options(joinedload(Invoice.payments))
            .filter(Invoice.importation_id == imp.id, Invoice.is_active.is_(True))
            .order_by(Invoice.invoice_date, Invoice.id)
            .all()
        )

        settled_brl_real = _D0
        invoice_rows: list[dict] = []
        order_has_visible = False

        for inv in invoices:
            if invoice_type and inv.invoice_type != invoice_type:
                continue
            eff = invoice_effective_amount(db, inv)
            bal = invoice_balance(db, inv)
            pay_rows: list[dict] = []

            for pay in sorted(inv.payments, key=lambda p: p.id):
                if not pay.is_active:
                    continue
                display = compute_payment_display(pay, inv, provision)
                settled = display["is_settled"]
                brl_val = display.get("display_brl")
                brl_dec = Decimal(brl_val) if brl_val else None

                if status_filter == "planned" and settled:
                    continue
                if status_filter == "settled" and not settled:
                    continue
                if status_filter == "overdue":
                    if not pay.due_date or pay.due_date >= today or settled:
                        continue
                if status_filter == "due7":
                    if not pay.due_date or pay.due_date < today or pay.due_date > in7 or settled:
                        continue
                if date_from and pay.due_date and pay.due_date < date_from:
                    continue
                if date_to and pay.due_date and pay.due_date > date_to:
                    continue

                order_has_visible = True
                if settled and brl_dec is not None:
                    kpi_settled += brl_dec
                    if pay.exchange_rate is not None and pay.amount_local is not None:
                        settled_brl_real += pay.amount_local
                    elif normalize_import_currency(pay.currency_foreign or inv.currency) == "BRL":
                        settled_brl_real += _d(pay.amount_foreign)
                elif brl_dec is not None:
                    kpi_pending += brl_dec
                    if pay.due_date and today <= pay.due_date <= in7:
                        kpi_due7 += brl_dec
                        kpi_due7_count += 1
                    if pay.due_date and pay.due_date < today:
                        kpi_overdue += 1

                pay_rows.append(
                    {
                        "id": pay.id,
                        "payment_type": pay.payment_type,
                        "due_date": pay.due_date.isoformat() if pay.due_date else None,
                        "payment_date": pay.payment_date.isoformat() if pay.payment_date else None,
                        "amount_foreign": str(pay.amount_foreign) if pay.amount_foreign is not None else None,
                        "currency_foreign": normalize_import_currency(pay.currency_foreign or inv.currency),
                        "exchange_rate": str(pay.exchange_rate) if pay.exchange_rate is not None else None,
                        "amount_local": str(pay.amount_local) if pay.amount_local is not None else None,
                        "receipt_reference": pay.receipt_reference,
                        "status_label": _payment_status_label(pay),
                        **display,
                    }
                )

            if not pay_rows and status_filter in ("planned", "settled", "overdue", "due7"):
                continue

            if pay_rows or not status_filter:
                order_has_visible = order_has_visible or bool(pay_rows) or not status_filter
                invoice_rows.append(
                    {
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "invoice_type": inv.invoice_type,
                        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                        "expected_exchange_rate": str(inv.expected_exchange_rate)
                        if inv.expected_exchange_rate is not None
                        else None,
                        "amount_eur": str(eff) if eff is not None else None,
                        "balance": str(bal) if bal is not None else None,
                        "currency": normalize_import_currency(inv.currency),
                        "payments": pay_rows,
                    }
                )

        if status_filter and not order_has_visible:
            continue

        exposure_raw = compute_open_fx_exposure_brl(
            db, imp.id, provision=provision, settled_brl_real=settled_brl_real
        )
        exposure_dec = Decimal(exposure_raw) if exposure_raw is not None else _D0
        if exposure_dec > _D0:
            kpi_exposure += exposure_dec

        imp_ids.append(imp.id)
        order_blocks.append(
            {
                "importation_id": imp.id,
                "po_number": imp.po_number,
                "supplier_name": supplier_map.get(imp.supplier_id, "—"),
                "status": imp.current_status,
                "opening_exchange_rate": str(provision) if provision is not None else None,
                "finance_operational": finance_ops,
                "fx_pnl": fx_pnl,
                "open_fx_exposure_brl": exposure_raw,
                "invoices": invoice_rows,
            }
        )

    due_summary = payments_due_summary(db, window_days=7)
    agg_pnl = aggregate_fx_pnl(db, imp_ids, mark_rate=mark_rate) if imp_ids else {}

    pnl_display = agg_pnl.get("pnl_total_brl")
    if agg_pnl.get("pnl_realized_brl") is None and kpi_exposure > _D0:
        pnl_display = None

    return {
        "kpis": {
            "total_settled_brl": str(kpi_settled) if kpi_settled > _D0 else None,
            "total_pending_brl": str(kpi_pending) if kpi_pending > _D0 else None,
            "due_7d_count": kpi_due7_count or due_summary.get("due_count", 0),
            "due_7d_brl": str(kpi_due7) if kpi_due7 > _D0 else None,
            "overdue_count": kpi_overdue or due_summary.get("overdue_count", 0),
            "fx_pnl_total_brl": pnl_display,
            "open_fx_exposure_brl": str(kpi_exposure) if kpi_exposure > _D0 else None,
            "orders_with_provision": sum(1 for o in order_blocks if o.get("opening_exchange_rate")),
        },
        "fx_pnl_summary": agg_pnl,
        "orders": order_blocks,
    }
