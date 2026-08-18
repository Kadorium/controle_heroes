"""Consultas compostas Reporting — só APIs públicas de outros módulos."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.documents import public as documents_public
from app.orders import public as orders_public
from app.treasury import public as treasury_public

COCKPIT_LIST_LIMIT = 10
COCKPIT_DOC_LIMIT = 5
COCKPIT_AUDIT_LIMIT = 10


def _money2(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return f"{Decimal(v):.2f}"


def ap_queue(
    db: Session,
    *,
    due_before: date | None = None,
    due_after: date | None = None,
    supplier_id: int | None = None,
    order_id: int | None = None,
    invoice_id: int | None = None,
    currency: str | None = None,
    status: str | None = None,
    pending: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Fila AP enriquecida (FX via Treasury public, bulk)."""
    core = billing_public.payables_queue(
        db,
        due_before=due_before,
        due_after=due_after,
        supplier_id=supplier_id,
        order_id=order_id,
        invoice_id=invoice_id,
        currency=currency,
        status=status,
        pending=pending,
        limit=limit,
        offset=offset,
    )
    items = core["items"]
    payable_ids = [int(r["id"]) for r in items]
    supplier_ids = {int(r["supplier_id"]) for r in items if r.get("supplier_id") is not None}
    # Uma operação bulk (não get_supplier por linha / por id)
    suppliers = catalog_public.get_suppliers_bulk(db, supplier_ids)

    order_ids = {int(r["order_id"]) for r in items if r.get("order_id") is not None}
    orders = orders_public.get_orders_bulk(db, order_ids)

    plans = treasury_public.fx.get_current_plans_bulk(db, payable_ids)
    quote = treasury_public.fx.get_latest_quote(db, "EUR", "BRL")
    market = None
    if quote:
        market = {
            "rate": str(quote.rate),
            "source": quote.source,
            "status": treasury_public.fx.quote_status(quote),
            "stale": quote.stale_after < datetime.now(timezone.utc),
        }

    enriched = []
    for row in items:
        pid = int(row["id"])
        plan = plans.get(pid)
        bal = Decimal(str(row["balance"]))
        projected_rate = str(plan.rate) if plan else None
        projected_brl = _money2(bal * plan.rate) if plan else None
        pendencies: list[str] = []
        if row["status"] in ("OPEN", "PARTIALLY_PAID") and row.get("due_date"):
            if date.fromisoformat(row["due_date"]) < date.today():
                pendencies.append("OVERDUE")
        if projected_rate is None and row["status"] != "CANCELLED" and row.get("currency") != "BRL":
            pendencies.append("MISSING_FX")
        sid = int(row["supplier_id"]) if row.get("supplier_id") is not None else None
        supplier = suppliers.get(sid) if sid is not None else None
        oid = int(row["order_id"]) if row.get("order_id") is not None else None
        order = orders.get(oid) if oid is not None else None
        payee_display = row.get("payee_display_name")
        supplier_name = supplier.name if supplier else (payee_display or None)
        enriched.append(
            {
                **row,
                "supplier_name": supplier_name,
                "supplier_resolved": supplier is not None,
                "payee_display_name": payee_display,
                "source_type": row.get("source_type") or "INVOICE",
                "order_code": order.code if order else None,
                "fx_projected_rate": projected_rate,
                "fx_projected_brl": projected_brl,
                "pendencies": pendencies,
            }
        )

    unallocated_candidates = _unallocated_candidates(db, enriched)
    by_cur: dict[str, dict[str, Any]] = {}
    for c in unallocated_candidates:
        cur = str(c.get("currency") or "")
        bucket = by_cur.setdefault(
            cur,
            {
                "currency": cur,
                "unallocated_candidates_count": 0,
                "unallocated_candidates_total": Decimal("0"),
            },
        )
        bucket["unallocated_candidates_count"] += 1
        bucket["unallocated_candidates_total"] += Decimal(str(c["amount_unallocated"]))
    unallocated_by_currency = [
        {
            "currency": b["currency"],
            "unallocated_candidates_count": b["unallocated_candidates_count"],
            "unallocated_candidates_total": _money2(b["unallocated_candidates_total"]),
        }
        for b in sorted(by_cur.values(), key=lambda x: x["currency"])
    ]
    core_kpis = dict(core["kpis"])
    core_kpis["unallocated_by_currency"] = unallocated_by_currency
    return {
        "items": enriched,
        "total": core["total"],
        "limit": core["limit"],
        "offset": core["offset"],
        "kpis": core_kpis,
        "market_quote": market,
        "unallocated_candidates": unallocated_candidates,
        "sort": "overdue_first,due_date_asc,id_asc",
        "note": "unallocated_candidates are NOT payment↔payable relations; paid uses allocations only",
    }


def _unallocated_candidates(db: Session, rows: list[dict]) -> list[dict[str, Any]]:
    pairs = {(int(r["supplier_id"]), r["currency"]) for r in rows if r.get("supplier_id")}
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for supplier_id, currency in pairs:
        payments = treasury_public.list_payments(
            db, supplier_id=supplier_id, currency=currency, limit=50, offset=0
        )
        for p in payments:
            if p.id in seen or p.status != "REGISTERED":
                continue
            residual = treasury_public.amount_unallocated(db, p)
            if residual <= 0:
                continue
            seen.add(p.id)
            out.append(
                {
                    "payment_id": p.id,
                    "supplier_id": p.supplier_id,
                    "currency": p.currency,
                    "amount": str(p.amount),
                    "amount_unallocated": f"{residual:.2f}",
                    "relation": False,
                    "role": "candidate_by_supplier_currency",
                }
            )
    return out[:20]


def order_cockpit(db: Session, order_id: int) -> dict[str, Any]:
    """Read model transversal — payload limitado."""
    order = orders_public.get_order(db, order_id)
    commercial_totals = orders_public.totals_as_strings(order)
    suppliers = catalog_public.get_suppliers_bulk(db, {order.supplier_id})
    supplier = suppliers.get(order.supplier_id)
    supplier_name = supplier.name if supplier else None

    invoices = billing_public.list_invoices(db, order_id=order_id, limit=COCKPIT_LIST_LIMIT, offset=0)
    inv_summaries = [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "status": inv.status,
            "currency": inv.currency,
            "type": inv.invoice_type,
        }
        for inv in invoices
    ]

    payable_rows = billing_public.list_payables(db, order_id=order_id, limit=200, offset=0)
    payable_ids = [p.id for p in payable_rows if p.status != "CANCELLED"]
    plans = treasury_public.fx.get_current_plans_bulk(db, payable_ids)

    invoiced = Decimal("0")
    open_balance = Decimal("0")
    paid_via_alloc = Decimal("0")
    next_due: date | None = None
    pay_summaries = []
    fx_exposure_open = Decimal("0")
    missing_fx = False

    for p in payable_rows:
        if p.status == "CANCELLED":
            continue
        invoiced += p.amount
        open_balance += p.balance
        paid_via_alloc += p.amount - p.balance
        if p.status in ("OPEN", "PARTIALLY_PAID"):
            if next_due is None or p.due_date < next_due:
                next_due = p.due_date
            fx_exposure_open += p.balance
            if p.currency != "BRL" and p.id not in plans:
                missing_fx = True
        pay_summaries.append(
            {
                "id": p.id,
                "invoice_id": p.invoice_id,
                "due_date": p.due_date.isoformat(),
                "amount": str(p.amount),
                "balance": str(p.balance),
                "status": p.status,
                "currency": p.currency,
            }
        )

    fx_cost = treasury_public.fx_queries.order_fx_cost(db, order_id)

    # Lista principal = só deste pedido (FIN-1C-FIX-1 F1). Candidatos = fornecedor+moeda.
    order_payments = treasury_public.list_payments(
        db, order_id=order_id, limit=COCKPIT_LIST_LIMIT, offset=0
    )
    payment_summaries = []
    advanced_credit = Decimal("0")
    for pay in order_payments:
        residual = treasury_public.amount_unallocated(db, pay)
        cancelled = pay.status == "CANCELLED"
        payment_summaries.append(
            {
                "id": pay.id,
                "amount": str(pay.amount),
                "currency": pay.currency,
                "status": pay.status,
                "amount_allocated": None
                if cancelled
                else f"{(pay.amount - residual):.2f}",
                # CANCELLED: residual operacional nulo (UI mostra —); não mentir crédito ativo
                "amount_unallocated": None if cancelled else f"{residual:.2f}",
            }
        )
        if pay.status == "REGISTERED" and residual > 0 and pay.purpose == "ADVANCE":
            advanced_credit += residual

    supplier_payments = treasury_public.list_payments(
        db,
        supplier_id=order.supplier_id,
        currency=order.currency,
        limit=COCKPIT_LIST_LIMIT,
        offset=0,
    )
    unallocated_candidates = []
    for pay in supplier_payments:
        residual = treasury_public.amount_unallocated(db, pay)
        if residual > 0 and pay.status == "REGISTERED":
            unallocated_candidates.append(
                {
                    "payment_id": pay.id,
                    "amount_unallocated": f"{residual:.2f}",
                    "currency": pay.currency,
                    "order_id": pay.order_id,
                    "relation": pay.order_id == order_id,
                    "role": "candidate_by_supplier_currency",
                }
            )

    docs = list(documents_public.list_by_entity(db, "order", str(order_id))[:COCKPIT_DOC_LIMIT])
    for inv in invoices[:3]:
        docs.extend(documents_public.list_by_entity(db, "invoice", str(inv.id))[:2])
    doc_summaries = [
        {
            "id": d.id,
            "filename": d.original_filename,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs[:COCKPIT_DOC_LIMIT]
    ]

    audit_rows = audit_public.history_by_entity(db, "order", str(order_id), limit=COCKPIT_AUDIT_LIMIT)
    audit_summaries = [
        {
            "id": a.id,
            "action": a.action,
            "actor_id": a.actor_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in audit_rows
    ]

    alerts: list[dict[str, str]] = []
    if any(p.status in ("OPEN", "PARTIALLY_PAID") and p.due_date < date.today() for p in payable_rows):
        alerts.append(
            {"code": "OVERDUE", "message": "Há obrigações vencidas", "href": f"/payables?order_id={order_id}"}
        )
    if unallocated_candidates:
        alerts.append(
            {
                "code": "UNALLOCATED_CANDIDATE",
                "message": (
                    "Candidatos a alocação do mesmo fornecedor/moeda "
                    "(podem ser de outros pedidos — não são a lista deste pedido)"
                ),
                "href": "/payments",
            }
        )
    if missing_fx:
        alerts.append(
            {
                "code": "MISSING_FX",
                "message": "Obrigação sem taxa projetada",
                "href": f"/payables?order_id={order_id}",
            }
        )

    return {
        "order_id": order.id,
        "commercial": {
            "code": order.code,
            "status": order.status,
            "supplier_id": order.supplier_id,
            "supplier_name": supplier_name,
            "currency": order.currency,
            "totals": commercial_totals,
            "items_count": len(order.items),
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        },
        "billing": {
            "invoices": inv_summaries,
            "invoices_count": len(inv_summaries),
            "payables": pay_summaries[:COCKPIT_LIST_LIMIT],
            "payables_count": len(pay_summaries),
            "invoiced_amount": f"{invoiced:.2f}",
            "open_balance": f"{open_balance:.2f}",
            "next_due_date": next_due.isoformat() if next_due else None,
        },
        "treasury": {
            "paid_via_allocations": f"{paid_via_alloc:.2f}",
            "advanced_credit": f"{advanced_credit:.2f}",
            "cost_brl": fx_cost["cost_brl"],
            "cost_weighted_avg_rate": fx_cost["weighted_avg_rate"],
            "payments": payment_summaries,
            "unallocated_candidates": unallocated_candidates,
            "note": (
                "paid_via_allocations = Σ(amount−balance) Payables; "
                "advanced_credit = residual REGISTERED com purpose ADVANCE; "
                "cost_brl = soma FxExecution dos pagamentos REGISTERED do pedido "
                "(não é média × EUR; não é resultado vs taxa planejada); "
                "payments = order-scoped; candidates = supplier+currency."
            ),
        },
        "fx": {
            "open_foreign_exposure": f"{fx_exposure_open:.2f}",
            "cost_brl": fx_cost["cost_brl"],
            "cost_eur": fx_cost["cost_eur"],
            "weighted_avg_rate": fx_cost["weighted_avg_rate"],
        },
        "documents": {"items": doc_summaries, "count": len(doc_summaries), "truncated": True},
        "audit": {"items": audit_summaries, "count": len(audit_summaries), "truncated": True},
        "alerts": alerts,
        "schedule": orders_public.payment_schedule_view(db, order),
        "kpis": {
            "ordered": commercial_totals.get("commercial_total"),
            "invoiced": f"{invoiced:.2f}",
            "paid": f"{paid_via_alloc:.2f}",
            "advanced_credit": f"{advanced_credit:.2f}",
            "balance": f"{open_balance:.2f}",
            "next_due": next_due.isoformat() if next_due else None,
            "fx_exposure": f"{fx_exposure_open:.2f}",
            "cost_brl": fx_cost["cost_brl"],
        },
    }


def orders_list(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Fila Pedidos enriquecida (read model Reporting) — ausência financeira = None."""
    rows = orders_public.list_orders(db, status=status, limit=limit, offset=offset)
    ids = [o.id for o in rows]
    suppliers = catalog_public.get_suppliers_bulk(db, {o.supplier_id for o in rows})
    financials = billing_public.order_list_financials(db, ids)
    out: list[dict[str, Any]] = []
    for o in rows:
        t = orders_public.totals_as_strings(o)
        fin = financials.get(o.id, {})
        unpriced = int(t.get("unpriced_item_count") or 0)
        supplier = suppliers.get(o.supplier_id)
        pendencies: str | None = None
        if unpriced > 0:
            pendencies = f"{unpriced} item(ns) sem preço"
        out.append(
            {
                "id": o.id,
                "code": o.code,
                "supplier_id": o.supplier_id,
                "supplier_name": supplier.name if supplier else None,
                "status": o.status,
                "currency": o.currency,
                "order_date": o.order_date.isoformat() if o.order_date else None,
                "created_by_actor_id": o.created_by_actor_id,
                "version": o.version,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
                "commercial_total": t.get("commercial_total"),
                "unpriced_item_count": unpriced,
                "invoiced_amount": fin.get("invoiced_amount"),
                "open_balance": fin.get("open_balance"),
                "next_due_date": fin.get("next_due_date").isoformat()
                if fin.get("next_due_date")
                else None,
                "pendencies": pendencies,
            }
        )
    return out
