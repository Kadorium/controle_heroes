from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import repository as repo
from app.billing.errors import BillingError, InvoiceNotFound, PayableNotFound
from app.billing.models import Invoice, InvoiceItem, Payable
from app.billing.money import decimal_str, invoice_net, line_derived, money2, split_scadenze_percent
from app.documents import public as documents_public
from app.orders import public as orders_public


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    inv = repo.get_invoice(db, invoice_id)
    if not inv:
        raise InvoiceNotFound(invoice_id)
    return inv


def list_invoices(
    db: Session,
    *,
    order_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Invoice]:
    return repo.list_invoices(db, order_id=order_id, status=status, limit=limit, offset=offset)


def list_payables(
    db: Session,
    *,
    order_id: int | None = None,
    invoice_id: int | None = None,
    status: str | None = None,
    due_before=None,
    due_after=None,
    limit: int = 100,
    offset: int = 0,
) -> list[Payable]:
    return repo.list_payables(
        db,
        order_id=order_id,
        invoice_id=invoice_id,
        status=status,
        due_before=due_before,
        due_after=due_after,
        limit=limit,
        offset=offset,
    )


def payables_queue(
    db: Session,
    *,
    due_before=None,
    due_after=None,
    supplier_id: int | None = None,
    order_id: int | None = None,
    invoice_id: int | None = None,
    currency: str | None = None,
    status: str | None = None,
    pending: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Fila AP server-side: filtros, sort operacional, paginação, KPIs do conjunto filtrado."""
    from datetime import date as date_cls

    from sqlalchemy import case, func

    from app.billing.models import Invoice, Payable

    today = date_cls.today()
    q = db.query(Payable).join(Invoice)
    if order_id is not None:
        q = q.filter(Invoice.order_id == order_id)
    if invoice_id is not None:
        q = q.filter(Payable.invoice_id == invoice_id)
    if supplier_id is not None:
        q = q.filter(Invoice.supplier_id == supplier_id)
    if status:
        q = q.filter(Payable.status == status)
    else:
        q = q.filter(Payable.status != "CANCELLED")
    if currency:
        q = q.filter(Payable.currency == currency.upper())
    if due_before is not None:
        q = q.filter(Payable.due_date <= due_before)
    if due_after is not None:
        q = q.filter(Payable.due_date >= due_after)
    if pending == "OVERDUE":
        q = q.filter(
            Payable.due_date < today,
            Payable.status.in_(("OPEN", "PARTIALLY_PAID")),
        )
    elif pending == "OPEN_BALANCE":
        q = q.filter(Payable.balance > 0, Payable.status.in_(("OPEN", "PARTIALLY_PAID")))

    from datetime import timedelta

    from sqlalchemy.orm import joinedload

    day7 = today + timedelta(days=7)
    q = q.options(joinedload(Payable.invoice))
    kpi_row = (
        q.with_entities(
            func.count(Payable.id),
            func.coalesce(func.sum(Payable.balance), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Payable.due_date < today)
                            & (Payable.status.in_(("OPEN", "PARTIALLY_PAID"))),
                            Payable.balance,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Payable.due_date < today)
                            & (Payable.status.in_(("OPEN", "PARTIALLY_PAID"))),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Payable.due_date == today)
                            & (Payable.status.in_(("OPEN", "PARTIALLY_PAID"))),
                            Payable.balance,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Payable.due_date > today)
                            & (Payable.due_date <= day7)
                            & (Payable.status.in_(("OPEN", "PARTIALLY_PAID"))),
                            Payable.balance,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        ).one()
    )
    total = int(kpi_row[0] or 0)
    kpis = {
        "total_count": total,
        "open_balance": money2(Decimal(str(kpi_row[1]))),
        "overdue_balance": money2(Decimal(str(kpi_row[2]))),
        "overdue_count": int(kpi_row[3] or 0),
        "due_today_balance": money2(Decimal(str(kpi_row[4]))),
        "next_7d_balance": money2(Decimal(str(kpi_row[5]))),
    }
    # stringify money
    kpis = {
        "total_count": kpis["total_count"],
        "open_balance": f"{kpis['open_balance']:.2f}",
        "overdue_balance": f"{kpis['overdue_balance']:.2f}",
        "overdue_count": kpis["overdue_count"],
        "due_today_balance": f"{kpis['due_today_balance']:.2f}",
        "next_7d_balance": f"{kpis['next_7d_balance']:.2f}",
    }

    overdue_rank = case(
        (
            (Payable.due_date < today) & (Payable.status.in_(("OPEN", "PARTIALLY_PAID"))),
            0,
        ),
        else_=1,
    )
    rows = (
        q.order_by(overdue_rank.asc(), Payable.due_date.asc(), Payable.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for p in rows:
        inv = p.invoice
        allocated = money2(p.amount - p.balance)
        items.append(
            {
                "id": p.id,
                "invoice_id": p.invoice_id,
                "order_id": inv.order_id if inv else None,
                "supplier_id": inv.supplier_id if inv else None,
                "sequence": p.sequence,
                "due_date": p.due_date.isoformat(),
                "amount": decimal_str(p.amount) or "0",
                "allocated": decimal_str(allocated) or "0",
                "balance": decimal_str(p.balance) or "0",
                "currency": p.currency,
                "status": p.status,
                "version": p.version,
                "invoice_number": inv.invoice_number if inv else None,
                "invoice_type": inv.invoice_type if inv else None,
                "days_overdue": (today - p.due_date).days
                if p.due_date < today and p.status in ("OPEN", "PARTIALLY_PAID")
                else 0,
            }
        )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "kpis": kpis,
    }


def get_payable(db: Session, payable_id: int) -> Payable:
    row = repo.get_payable(db, payable_id)
    if not row:
        raise PayableNotFound(payable_id)
    return row


def get_payable_for_update(db: Session, payable_id: int) -> Payable:
    """Lock FOR UPDATE no Payable — serializa FX plan / liquidação."""
    row = repo.get_payable_for_update(db, payable_id)
    if not row:
        raise PayableNotFound(payable_id)
    return row


def item_amounts_as_strings(item: InvoiceItem) -> dict[str, str | None]:
    gross, disc, net = line_derived(item)
    return {
        "line_gross_amount": decimal_str(gross),
        "line_discount_amount": decimal_str(disc),
        "line_net_amount": decimal_str(net),
    }


def invoice_totals_as_strings(inv: Invoice) -> dict[str, str | int | None]:
    net = invoice_net(list(inv.items))
    incomplete = 0
    for item in inv.items:
        g, d, n = line_derived(item)
        if item.unit_price_gross is None or item.discount_type is None or n is None:
            incomplete += 1
    balance = None
    if inv.status == "ISSUED" and inv.payables:
        balance = money2(sum((p.balance for p in inv.payables), Decimal("0")))
    elif net is not None:
        balance = net
    return {
        "net_amount": decimal_str(net),
        "incomplete_line_count": incomplete,
        "balance": decimal_str(balance),
        "payables_sum": decimal_str(
            money2(sum((p.amount for p in inv.payables), Decimal("0"))) if inv.payables else None
        ),
    }


def preview_payables(inv: Invoice) -> list[dict[str, str]]:
    """Prévia dos payables a partir dos terms (DRAFT)."""
    net = invoice_net(list(inv.items))
    if net is None or not inv.terms or not inv.terms_mode:
        return []
    if inv.terms_mode == "PERCENT":
        amounts = split_scadenze_percent(net, [t.percent for t in inv.terms])  # type: ignore[list-item]
    else:
        amounts = [money2(t.amount) for t in inv.terms]  # type: ignore[arg-type]
    out = []
    for term, amount in zip(inv.terms, amounts, strict=True):
        out.append(
            {
                "sequence": str(term.sequence),
                "due_date": term.due_date.isoformat(),
                "amount": decimal_str(amount) or "0",
            }
        )
    return out


def issue_blockers(db: Session, inv: Invoice) -> list[str]:
    """Mensagens de bloqueio de emissão (read-model; espelha pré-condições de issue)."""
    if inv.status != "DRAFT":
        return []
    out: list[str] = []
    totals = invoice_totals_as_strings(inv)
    if int(totals["incomplete_line_count"] or 0) > 0:
        out.append("Há linhas com preço ou desconto incompletos")
    if not inv.terms or not inv.terms_mode:
        out.append("Defina scadenze (PERCENT ou AMOUNT)")
    docs = documents_public.list_by_entity(db, "invoice", str(inv.id))
    if not docs:
        out.append("Anexe o documento oficial da fatura (ou use override autorizado na emissão)")
    return out


def order_invoiced_quantities(db: Session, order_id: int) -> dict[int, str]:
    raw = repo.issued_qty_by_order_item(db, order_id)
    return {k: decimal_str(v) or "0" for k, v in raw.items()}


def order_qty_availability(db: Session, order_id: int) -> list[dict[str, str | int]]:
    """Pedida / emitida (ISSUED) / disponível por OrderItem."""
    try:
        order = orders_public.get_order(db, order_id)
    except orders_public.OrdersError as e:
        code = getattr(e, "code", "validation_error")
        raise BillingError(getattr(e, "message", str(e)), code=code) from e
    issued = repo.issued_qty_by_order_item(db, order_id)
    rows: list[dict[str, str | int]] = []
    for oi in order.items:
        iss = issued.get(oi.id, Decimal("0"))
        avail = oi.quantity - iss
        rows.append(
            {
                "order_item_id": oi.id,
                "ordered_qty": decimal_str(oi.quantity) or "0",
                "issued_qty": decimal_str(iss) or "0",
                "available_qty": decimal_str(avail) or "0",
            }
        )
    return rows
