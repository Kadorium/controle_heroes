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


def get_payable(db: Session, payable_id: int) -> Payable:
    row = repo.get_payable(db, payable_id)
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
