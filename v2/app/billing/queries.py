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
    day30 = today + timedelta(days=30)
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
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Payable.due_date > today)
                            & (Payable.due_date <= day30)
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
                "next_30d_balance": f"{money2(Decimal(str(row[7]))):.2f}",
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

    from app.catalog.public import get_suppliers_bulk

    supplier_ids = {int(p.invoice.supplier_id) for p in rows if p.invoice and p.invoice.supplier_id}
    suppliers = get_suppliers_bulk(db, supplier_ids) if supplier_ids else {}

    items = []
    for p in rows:
        inv = p.invoice
        allocated = money2(p.amount - p.balance)
        sid = inv.supplier_id if inv else None
        supplier_name = suppliers[sid].name if sid is not None and sid in suppliers else None
        items.append(
            {
                "id": p.id,
                "invoice_id": p.invoice_id,
                "order_id": inv.order_id if inv else None,
                "supplier_id": sid,
                "supplier_name": supplier_name,
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
                "payee_tax_id": getattr(p, "payee_tax_id", None),
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


def costable_invoice_items(db: Session, invoice_item_ids: list[int]) -> list[dict]:
    """Fatos costáveis da InvoiceItem (líquido, qty, snapshots). Vazio ≠ 0."""
    if not invoice_item_ids:
        return []
    items = db.query(InvoiceItem).filter(InvoiceItem.id.in_(invoice_item_ids)).all()
    by_id = {i.id: i for i in items}
    out: list[dict] = []
    for iid in invoice_item_ids:
        item = by_id.get(iid)
        if not item:
            continue
        inv = get_invoice(db, item.invoice_id)
        amounts = item_amounts_as_strings(item)
        out.append(
            {
                "invoice_item_id": item.id,
                "invoice_id": item.invoice_id,
                "invoice_number": inv.invoice_number,
                "invoice_status": inv.status,
                "order_item_id": item.order_item_id,
                "product_id": item.product_id,
                "sku_snapshot": item.sku_snapshot,
                "description_snapshot": item.description_snapshot,
                "quantity": decimal_str(item.quantity),
                "currency": inv.currency,
                "line_net_amount": amounts["line_net_amount"],
                "line_gross_amount": amounts["line_gross_amount"],
            }
        )
    return out


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


def invoice_status_counts(db: Session) -> dict[str, int]:
    from sqlalchemy import func

    rows = db.query(Invoice.status, func.count(Invoice.id)).group_by(Invoice.status).all()
    out = {"DRAFT": 0, "ISSUED": 0, "CANCELLED": 0}
    for status, cnt in rows:
        out[str(status)] = int(cnt or 0)
    return out


def qty_to_invoice_residual(db: Session) -> dict[str, str | int]:
    """Residual de quantidade a faturar em pedidos CONFIRMED (SQL agregado)."""
    from sqlalchemy import text

    row = db.execute(
        text(
            """
            WITH issued AS (
              SELECT invoice_items.order_item_id AS order_item_id,
                     coalesce(sum(invoice_items.quantity), 0) AS issued_qty
              FROM invoice_items
              JOIN invoices ON invoices.id = invoice_items.invoice_id
              WHERE invoices.status = 'ISSUED'
              GROUP BY invoice_items.order_item_id
            )
            SELECT coalesce(sum(order_items.quantity - coalesce(issued.issued_qty, 0)), 0) AS residual_qty,
                   count(*) FILTER (
                     WHERE order_items.quantity - coalesce(issued.issued_qty, 0) > 0
                   ) AS line_count
            FROM order_items
            JOIN orders ON orders.id = order_items.order_id
            LEFT JOIN issued ON issued.order_item_id = order_items.id
            WHERE orders.status = 'CONFIRMED'
            """
        )
    ).one()
    qty = Decimal(str(row[0] or 0))
    return {"residual_qty": f"{qty:.4f}".rstrip("0").rstrip(".") or "0", "line_count": int(row[1] or 0)}


_MONTHS_PT = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def _add_months(day, months: int):
    from datetime import date as date_cls

    y = day.year + (day.month - 1 + months) // 12
    m = (day.month - 1 + months) % 12 + 1
    return date_cls(y, m, 1)


def cash_committed_by_month(
    db: Session,
    *,
    due_before=None,
    currency: str | None = None,
    supplier_id: int | None = None,
) -> dict:
    """Caixa comprometido: M0/M1/M2 civis + já vencido, por moeda. Não esconde overdue."""
    from datetime import date as date_cls

    from sqlalchemy import and_, case, func

    from app.billing.models import Invoice, Payable

    today = date_cls.today()
    m0 = today.replace(day=1)
    m1 = _add_months(m0, 1)
    m2 = _add_months(m0, 2)
    m3 = _add_months(m0, 3)

    openish = Payable.status.in_(("OPEN", "PARTIALLY_PAID"))
    q = db.query(Payable).outerjoin(Invoice, Invoice.id == Payable.invoice_id)
    q = q.filter(openish, Payable.balance > 0)
    if currency:
        q = q.filter(Payable.currency == currency.upper())
    if supplier_id is not None:
        q = q.filter(Invoice.supplier_id == supplier_id)

    def upcoming(lo, hi):
        conds = [Payable.due_date >= lo, Payable.due_date < hi]
        if due_before is not None:
            conds.append(Payable.due_date <= due_before)
        return and_(*conds)

    rows = (
        q.with_entities(
            Payable.currency,
            func.coalesce(func.sum(case((Payable.due_date < m0, Payable.balance), else_=0)), 0),
            func.coalesce(func.sum(case((upcoming(m0, m1), Payable.balance), else_=0)), 0),
            func.coalesce(func.sum(case((upcoming(m1, m2), Payable.balance), else_=0)), 0),
            func.coalesce(func.sum(case((upcoming(m2, m3), Payable.balance), else_=0)), 0),
            func.coalesce(func.sum(case((Payable.due_date < m0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((upcoming(m0, m1), 1), else_=0)), 0),
            func.coalesce(func.sum(case((upcoming(m1, m2), 1), else_=0)), 0),
            func.coalesce(func.sum(case((upcoming(m2, m3), 1), else_=0)), 0),
        )
        .group_by(Payable.currency)
        .all()
    )
    labels = {
        "overdue": "Já vencido",
        "m0": _MONTHS_PT[m0.month - 1],
        "m1": _MONTHS_PT[m1.month - 1],
        "m2": _MONTHS_PT[m2.month - 1],
    }
    by_currency = []
    for row in sorted(rows, key=lambda r: str(r[0] or "")):
        buckets = {
            "overdue": f"{money2(Decimal(str(row[1]))):.2f}",
            "m0": f"{money2(Decimal(str(row[2]))):.2f}",
            "m1": f"{money2(Decimal(str(row[3]))):.2f}",
            "m2": f"{money2(Decimal(str(row[4]))):.2f}",
        }
        counts = {
            "overdue": int(row[5] or 0),
            "m0": int(row[6] or 0),
            "m1": int(row[7] or 0),
            "m2": int(row[8] or 0),
        }
        by_currency.append(
            {
                "currency": str(row[0] or ""),
                "buckets": buckets,
                "counts": counts,
            }
        )
    return {
        "as_of_month": m0.isoformat(),
        "labels": labels,
        "includes_overdue": True,
        "by_currency": by_currency,
        "mixed_currency": len(by_currency) > 1,
    }


def order_billing_progress_by_currency(db: Session) -> dict:
    """Valor confirmado / faturado / residual por moeda (SQL agregado; não lista IDs)."""
    from sqlalchemy import text

    confirmed_rows = db.execute(
        text(
            """
            SELECT orders.currency,
                   coalesce(sum(order_items.quantity * order_items.unit_price), 0) AS confirmed_amount,
                   count(distinct orders.id) AS order_count
            FROM orders
            JOIN order_items ON order_items.order_id = orders.id
            WHERE orders.status = 'CONFIRMED'
              AND order_items.unit_price IS NOT NULL
            GROUP BY orders.currency
            """
        )
    ).all()
    issued_rows = db.execute(
        text(
            """
            SELECT invoices.currency,
                   coalesce(sum(payables.amount), 0) AS issued_amount
            FROM payables
            JOIN invoices ON invoices.id = payables.invoice_id
            WHERE invoices.status = 'ISSUED'
              AND payables.status <> 'CANCELLED'
              AND payables.source_type = 'INVOICE'
            GROUP BY invoices.currency
            """
        )
    ).all()
    unpriced = db.execute(
        text(
            """
            SELECT count(*) FROM order_items
            JOIN orders ON orders.id = order_items.order_id
            WHERE orders.status = 'CONFIRMED' AND order_items.unit_price IS NULL
            """
        )
    ).scalar()

    by: dict[str, dict] = {}
    for cur, amt, cnt in confirmed_rows:
        c = str(cur)
        conf = money2(Decimal(str(amt)))
        by[c] = {
            "currency": c,
            "confirmed": f"{conf:.2f}",
            "invoiced": "0.00",
            "to_invoice": f"{conf:.2f}",
            "order_count": int(cnt or 0),
        }
    for cur, amt in issued_rows:
        c = str(cur)
        inv = money2(Decimal(str(amt)))
        row = by.setdefault(
            c,
            {
                "currency": c,
                "confirmed": "0.00",
                "invoiced": "0.00",
                "to_invoice": "0.00",
                "order_count": 0,
            },
        )
        conf = money2(Decimal(row["confirmed"]))
        residual = conf - inv
        if residual < 0:
            residual = Decimal("0.00")
        row["invoiced"] = f"{inv:.2f}"
        row["to_invoice"] = f"{residual:.2f}"
    return {
        "by_currency": [by[k] for k in sorted(by)],
        "mixed_currency": len(by) > 1,
        "unpriced_lines": int(unpriced or 0),
        "empty": len(by) == 0,
    }


def invoice_item_product_ids(db: Session, invoice_item_ids: list[int] | set[int]) -> dict[int, int]:
    ids = sorted({int(i) for i in invoice_item_ids})
    if not ids:
        return {}
    rows = db.query(InvoiceItem.id, InvoiceItem.product_id).filter(InvoiceItem.id.in_(ids)).all()
    return {int(iid): int(pid) for iid, pid in rows if pid is not None}
