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


def find_invoices_by_number(db: Session, invoice_number: str) -> list[Invoice]:
    number = (invoice_number or "").strip()
    if not number:
        return []
    return repo.find_invoices_by_number(db, number)


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


def order_list_financials(db: Session, order_ids: list[int]) -> dict[int, dict]:
    """Agrega faturado / saldo aberto / próximo vencimento por Order (somente leitura).

    Ausência de invoices/payables → campos None (não zero inventado).
    """
    from sqlalchemy import func

    out: dict[int, dict] = {oid: {"invoiced_amount": None, "open_balance": None, "next_due_date": None} for oid in order_ids}
    if not order_ids:
        return out

    # Invoiced = Σ net de invoices ISSUED (via items); sem invoice ISSUED → None
    issued = (
        db.query(Invoice)
        .filter(Invoice.order_id.in_(order_ids), Invoice.status == "ISSUED")
        .all()
    )
    invoiced_acc: dict[int, Decimal] = {}
    for inv in issued:
        net = invoice_net(list(inv.items))
        if net is None:
            continue
        invoiced_acc[inv.order_id] = invoiced_acc.get(inv.order_id, Decimal("0")) + net
    for oid, total in invoiced_acc.items():
        out[oid]["invoiced_amount"] = decimal_str(money2(total))

    # Open balance + next due from OPEN payables with balance > 0
    rows = (
        db.query(
            Invoice.order_id,
            func.sum(Payable.balance),
            func.min(Payable.due_date),
        )
        .join(Payable, Payable.invoice_id == Invoice.id)
        .filter(
            Invoice.order_id.in_(order_ids),
            Payable.status == "OPEN",
            Payable.balance > 0,
        )
        .group_by(Invoice.order_id)
        .all()
    )
    for oid, bal, due in rows:
        if bal is not None:
            out[int(oid)]["open_balance"] = decimal_str(money2(Decimal(bal)))
        out[int(oid)]["next_due_date"] = due
    return out


def payable_counts_by_invoice(db: Session, invoice_ids: list[int]) -> dict[int, int]:
    from sqlalchemy import func

    if not invoice_ids:
        return {}
    rows = (
        db.query(Payable.invoice_id, func.count(Payable.id))
        .filter(Payable.invoice_id.in_(invoice_ids))
        .group_by(Payable.invoice_id)
        .all()
    )
    return {int(iid): int(cnt) for iid, cnt in rows}


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
    # outerjoin: payables Customs (sem Invoice) entram na fila AP
    q = db.query(Payable).outerjoin(Invoice, Invoice.id == Payable.invoice_id)
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
    openish = Payable.status.in_(("OPEN", "PARTIALLY_PAID"))
    kpi_rows = (
        q.with_entities(
            Payable.currency,
            func.count(Payable.id),
            func.coalesce(func.sum(Payable.balance), 0),
            func.coalesce(
                func.sum(
                    case(
                        ((Payable.due_date < today) & openish, Payable.balance),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        ((Payable.due_date < today) & openish, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        ((Payable.due_date == today) & openish, Payable.balance),
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
                            & openish,
                            Payable.balance,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .group_by(Payable.currency)
        .all()
    )
    kpis_by_currency = []
    total = 0
    overdue_count_global = 0
    for row in sorted(kpi_rows, key=lambda r: str(r[0] or "")):
        cur = str(row[0] or "")
        cnt = int(row[1] or 0)
        od_cnt = int(row[4] or 0)
        total += cnt
        overdue_count_global += od_cnt
        kpis_by_currency.append(
            {
                "currency": cur,
                "total_count": cnt,
                "open_balance": f"{money2(Decimal(str(row[2]))):.2f}",
                "overdue_balance": f"{money2(Decimal(str(row[3]))):.2f}",
                "overdue_count": od_cnt,
                "due_today_balance": f"{money2(Decimal(str(row[5]))):.2f}",
                "next_7d_balance": f"{money2(Decimal(str(row[6]))):.2f}",
            }
        )
    kpis = {
        "mixed_currency": len(kpis_by_currency) > 1,
        "total_count": total,
        "overdue_count": overdue_count_global,
        "kpis_by_currency": kpis_by_currency,
    }

    overdue_rank = case(
        (
            (Payable.due_date < today) & (Payable.status.in_(("OPEN", "PARTIALLY_PAID"))),
            0,
        ),
        else_=1,
    )
    rows = (
        q.options(joinedload(Payable.invoice))
        .order_by(overdue_rank.asc(), Payable.due_date.asc(), Payable.id.asc())
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
                "source_type": p.source_type,
                "source_id": p.source_id,
                "payee_display_name": p.payee_display_name,
                "destination_iban": getattr(p, "destination_iban", None),
                "destination_bank": getattr(p, "destination_bank", None),
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
    if inv.order_id:
        issued = repo.issued_qty_by_order_item(db, inv.order_id)
        try:
            order = orders_public.get_order(db, inv.order_id)
        except orders_public.OrdersError:
            order = None
        if order is not None:
            ordered_by_id = {oi.id: oi.quantity for oi in order.items}
            this_qty: dict[int, Decimal] = {}
            for item in inv.items:
                this_qty[item.order_item_id] = this_qty.get(item.order_item_id, Decimal("0")) + item.quantity
            for oid, qty in this_qty.items():
                ordered = ordered_by_id.get(oid)
                if ordered is None:
                    continue
                already = issued.get(oid, Decimal("0"))
                if already + qty > ordered:
                    out.append(
                        f"Quantidade faturada excede a pedida no item #{oid}: "
                        f"pedida={ordered}, já emitida={already}, nesta fatura={qty}"
                    )
    return out


def order_invoiced_quantities(db: Session, order_id: int) -> dict[int, str]:
    raw = repo.issued_qty_by_order_item(db, order_id)
    return {k: decimal_str(v) or "0" for k, v in raw.items()}


def issued_qty_for_order_item(db: Session, order_id: int, order_item_id: int) -> Decimal:
    """Quantidade ISSUED da linha; 0 se não houver fatura emitida."""
    return repo.issued_qty_by_order_item(db, order_id).get(order_item_id, Decimal("0"))


def order_qty_availability(db: Session, order_id: int) -> list[dict[str, str | int | bool | None]]:
    """Pedida / emitida (ISSUED) / disponível por OrderItem (+ kind/descrição/billable)."""
    try:
        order = orders_public.get_order(db, order_id)
    except orders_public.OrdersError as e:
        code = getattr(e, "code", "validation_error")
        raise BillingError(getattr(e, "message", str(e)), code=code) from e
    issued = repo.issued_qty_by_order_item(db, order_id)
    rows: list[dict[str, str | int | bool | None]] = []
    for oi in order.items:
        iss = issued.get(oi.id, Decimal("0"))
        avail = oi.quantity - iss
        billable = oi.product_id is not None
        rows.append(
            {
                "order_item_id": oi.id,
                "ordered_qty": decimal_str(oi.quantity) or "0",
                "issued_qty": decimal_str(iss) or "0",
                # Disponível faturável: 0 se COMMITMENT (product_id NULL)
                "available_qty": (decimal_str(avail) or "0") if billable else "0",
                "line_kind": getattr(oi, "line_kind", None) or ("PRODUCT" if billable else "COMMITMENT"),
                "description": oi.description_snapshot or None,
                "billable": billable,
            }
        )
    return rows
