from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import repository as repo
from app.billing.errors import (
    InvalidTransition,
    InvoiceConflict,
    InvoiceNotDraft,
    InvoiceNotFound,
    InvoiceValidationError,
)
from app.billing.models import Invoice, InvoiceItem, Payable, PaymentTerm
from app.billing.money import (
    compute_line,
    invoice_net,
    line_derived,
    money2,
    parse_decimal,
    require_positive_qty,
    split_scadenze_percent,
    validate_amount_terms,
)
from app.documents import public as documents_public
from app.orders import public as orders_public


def _get_order(db: Session, order_id: int):
    try:
        return orders_public.get_order(db, order_id)
    except orders_public.OrdersError as e:
        raise InvoiceValidationError(getattr(e, "message", str(e))) from e


def _get_order_locked(db: Session, order_id: int):
    try:
        return orders_public.get_order_locked(db, order_id)
    except orders_public.OrdersError as e:
        raise InvoiceValidationError(getattr(e, "message", str(e))) from e


def _require_draft(inv: Invoice) -> None:
    if inv.status != "DRAFT":
        raise InvoiceNotDraft()


def _lock(db: Session, inv: Invoice, expected_version: int) -> Invoice:
    if not repo.bump_version_if_match(db, inv.id, expected_version):
        raise InvoiceConflict()
    refreshed = repo.get_invoice(db, inv.id)
    assert refreshed is not None
    return refreshed


def _normalize_discount_fields(
    discount_type: str | None,
    discount_unit_amount: Decimal | None,
    discount_percent: Decimal | None,
) -> tuple[str | None, Decimal | None, Decimal | None]:
    if discount_type is None or discount_type == "":
        return None, None, None
    dt = discount_type.strip().upper()
    if dt == "NONE":
        return "NONE", None, None
    if dt == "UNIT_AMOUNT":
        if discount_unit_amount is None:
            raise InvoiceValidationError("Informe discount_unit_amount para UNIT_AMOUNT")
        return "UNIT_AMOUNT", discount_unit_amount, None
    if dt == "PERCENT":
        if discount_percent is None:
            raise InvoiceValidationError("Informe discount_percent para PERCENT")
        return "PERCENT", None, discount_percent
    raise InvoiceValidationError(f"discount_type inválido: {discount_type}")


def create_invoice(
    db: Session,
    *,
    order_id: int,
    invoice_number: str,
    created_by_actor_id: str,
    invoice_type: str = "FINAL",
    invoice_date: date | None = None,
    notes: str | None = None,
    order_item_ids: list[int] | None = None,
) -> Invoice:
    order = _get_order(db, order_id)
    if order.status != "CONFIRMED":
        raise InvoiceValidationError("Só é possível faturar ordem CONFIRMED")
    number = (invoice_number or "").strip()
    if not number:
        raise InvoiceValidationError("Número da fatura é obrigatório")
    if not created_by_actor_id or not str(created_by_actor_id).strip():
        raise InvoiceValidationError("Ator da criação é obrigatório")
    itype = (invoice_type or "FINAL").strip().upper()
    if itype not in ("FINAL", "PROFORMA"):
        raise InvoiceValidationError("Tipo de fatura Inc-2: FINAL ou PROFORMA")
    if repo.get_by_supplier_number(db, order.supplier_id, number):
        raise InvoiceValidationError(f"Número de fatura duplicado para o fornecedor: {number}")

    inv = Invoice(
        order_id=order.id,
        supplier_id=order.supplier_id,
        invoice_number=number,
        invoice_type=itype,
        status="DRAFT",
        invoice_date=invoice_date or date.today(),
        currency=order.currency,
        created_by_actor_id=str(created_by_actor_id).strip(),
        notes=notes.strip() if notes and notes.strip() else None,
        version=1,
    )
    repo.add_invoice(db, inv)

    items_src = list(order.items)
    if order_item_ids is not None:
        wanted = set(order_item_ids)
        items_src = [i for i in items_src if i.id in wanted]
        if len(items_src) != len(wanted):
            raise InvoiceValidationError("Um ou mais order_item_ids não pertencem à ordem")
    if not items_src:
        raise InvoiceValidationError("Selecione ao menos um item da ordem")

    for pos, oi in enumerate(items_src, start=1):
        db.add(
            InvoiceItem(
                invoice_id=inv.id,
                order_item_id=oi.id,
                product_id=oi.product_id,
                sku_snapshot=oi.sku_snapshot,
                description_snapshot=oi.description_snapshot,
                quantity=oi.quantity,
                unit_price_gross=oi.unit_price,
                discount_type=None,
                position=pos,
            )
        )
    db.flush()
    return repo.get_invoice(db, inv.id)  # type: ignore[return-value]


def update_invoice_header(
    db: Session,
    invoice_id: int,
    *,
    expected_version: int,
    invoice_number: str | None = None,
    invoice_type: str | None = None,
    invoice_date: date | None = None,
    notes: str | None = ...,  # type: ignore[assignment]
) -> Invoice:
    inv = repo.get_invoice(db, invoice_id)
    if not inv:
        raise InvoiceNotFound(invoice_id)
    _require_draft(inv)
    if invoice_number is not None:
        number = invoice_number.strip()
        if not number:
            raise InvoiceValidationError("Número da fatura é obrigatório")
        other = repo.get_by_supplier_number(db, inv.supplier_id, number)
        if other and other.id != inv.id:
            raise InvoiceValidationError(f"Número de fatura duplicado: {number}")
        inv.invoice_number = number
    if invoice_type is not None:
        itype = invoice_type.strip().upper()
        if itype not in ("FINAL", "PROFORMA"):
            raise InvoiceValidationError("Tipo de fatura Inc-2: FINAL ou PROFORMA")
        inv.invoice_type = itype
    if invoice_date is not None:
        inv.invoice_date = invoice_date
    if notes is not ...:
        inv.notes = notes.strip() if notes and notes.strip() else None
    return _lock(db, inv, expected_version)


def replace_items(
    db: Session,
    invoice_id: int,
    *,
    expected_version: int,
    items: list[dict],
) -> Invoice:
    inv = repo.get_invoice(db, invoice_id)
    if not inv:
        raise InvoiceNotFound(invoice_id)
    _require_draft(inv)
    order = _get_order(db, inv.order_id)
    order_items = {oi.id: oi for oi in order.items}
    if not items:
        raise InvoiceValidationError("Informe ao menos um item")

    repo.clear_items(db, inv)
    for pos, raw in enumerate(items, start=1):
        oid = int(raw["order_item_id"])
        oi = order_items.get(oid)
        if not oi:
            raise InvoiceValidationError(f"order_item_id {oid} não pertence à ordem")
        qty = require_positive_qty(raw["quantity"])
        price = parse_decimal(raw.get("unit_price_gross"))
        dt, dua, dp = _normalize_discount_fields(
            raw.get("discount_type"),
            parse_decimal(raw.get("discount_unit_amount")),
            parse_decimal(raw.get("discount_percent")),
        )
        if dt is not None and price is not None:
            compute_line(
                quantity=qty,
                unit_price_gross=price,
                discount_type=dt,
                discount_unit_amount=dua,
                discount_percent=dp,
            )
        db.add(
            InvoiceItem(
                invoice_id=inv.id,
                order_item_id=oi.id,
                product_id=oi.product_id,
                sku_snapshot=oi.sku_snapshot,
                description_snapshot=oi.description_snapshot,
                quantity=qty,
                unit_price_gross=price,
                discount_type=dt,
                discount_unit_amount=dua,
                discount_percent=dp,
                position=pos,
            )
        )
    db.flush()
    return _lock(db, inv, expected_version)


def set_terms(
    db: Session,
    invoice_id: int,
    *,
    expected_version: int,
    mode: str,
    terms: list[dict],
) -> Invoice:
    inv = repo.get_invoice(db, invoice_id)
    if not inv:
        raise InvoiceNotFound(invoice_id)
    _require_draft(inv)
    mode_u = (mode or "").strip().upper()
    if mode_u not in ("PERCENT", "AMOUNT"):
        raise InvoiceValidationError("Modo de scadenze: PERCENT ou AMOUNT")
    if not terms:
        raise InvoiceValidationError("Informe ao menos uma scadenza")

    net = invoice_net(list(inv.items))
    # Allow setting terms before lines complete in DRAFT — validate shapes only;
    # full sum check deferred to issue if net unknown. Still forbid mixed fields.
    repo.clear_terms(db, inv)
    percents: list[Decimal] = []
    amounts: list[Decimal] = []
    for seq, raw in enumerate(terms, start=1):
        due = raw.get("due_date")
        if due is None:
            raise InvoiceValidationError("Data de vencimento obrigatória")
        if isinstance(due, str):
            due = date.fromisoformat(due)
        pct = parse_decimal(raw.get("percent"))
        amt = parse_decimal(raw.get("amount"))
        if mode_u == "PERCENT":
            if pct is None or amt is not None:
                raise InvoiceValidationError("No modo PERCENT use apenas percent (sem amount)")
            percents.append(pct)
            db.add(
                PaymentTerm(
                    invoice_id=inv.id,
                    sequence=seq,
                    due_date=due,
                    percent=pct,
                    amount=None,
                )
            )
        else:
            if amt is None or pct is not None:
                raise InvoiceValidationError("No modo AMOUNT use apenas amount (sem percent)")
            amounts.append(amt)
            db.add(
                PaymentTerm(
                    invoice_id=inv.id,
                    sequence=seq,
                    due_date=due,
                    percent=None,
                    amount=money2(amt),
                )
            )
    if mode_u == "PERCENT":
        if sum(percents) != Decimal("100"):
            raise InvoiceValidationError("Percentuais das scadenze devem somar 100%")
        if any(p <= 0 for p in percents):
            raise InvoiceValidationError("Percentual de scadenza deve ser > 0")
    elif net is not None:
        validate_amount_terms(net, amounts)

    inv.terms_mode = mode_u
    db.flush()
    return _lock(db, inv, expected_version)


def _assert_ready_to_issue(db: Session, inv: Invoice, *, allow_without_doc: bool) -> Decimal:
    if not inv.items:
        raise InvoiceValidationError("Fatura sem itens")
    for item in inv.items:
        if item.unit_price_gross is None:
            raise InvoiceValidationError(
                f"Preço bruto incompleto na linha {item.position} (SKU {item.sku_snapshot})"
            )
        if item.discount_type is None:
            raise InvoiceValidationError(
                f"Desconto indefinido na linha {item.position} (SKU {item.sku_snapshot}). "
                "Defina NONE, UNIT_AMOUNT ou PERCENT."
            )
        compute_line(
            quantity=item.quantity,
            unit_price_gross=item.unit_price_gross,
            discount_type=item.discount_type,
            discount_unit_amount=item.discount_unit_amount,
            discount_percent=item.discount_percent,
        )
    net = invoice_net(list(inv.items))
    assert net is not None
    if not inv.terms or inv.terms_mode is None:
        raise InvoiceValidationError("Defina scadenze antes de emitir")
    if inv.terms_mode == "PERCENT":
        split_scadenze_percent(net, [t.percent for t in inv.terms])  # type: ignore[list-item]
    else:
        validate_amount_terms(net, [t.amount for t in inv.terms])  # type: ignore[list-item]

    docs = documents_public.list_by_entity(db, "invoice", str(inv.id))
    if not docs and not allow_without_doc:
        raise InvoiceValidationError(
            "Documento oficial obrigatório para emitir. Anexe a fatura ou use override autorizado."
        )
    return net


def _assert_qty_against_order(db: Session, inv: Invoice) -> None:
    order = _get_order_locked(db, inv.order_id)
    issued = repo.issued_qty_by_order_item(db, inv.order_id)
    order_qty = {oi.id: oi.quantity for oi in order.items}
    this_qty: dict[int, Decimal] = {}
    for item in inv.items:
        this_qty[item.order_item_id] = this_qty.get(item.order_item_id, Decimal("0")) + item.quantity
    for oid, qty in this_qty.items():
        ordered = order_qty.get(oid)
        if ordered is None:
            raise InvoiceValidationError(f"order_item {oid} inválido")
        already = issued.get(oid, Decimal("0"))
        if already + qty > ordered:
            raise InvoiceValidationError(
                f"Quantidade faturada excede a pedida no item #{oid}: "
                f"pedida={ordered}, já emitida={already}, nesta fatura={qty}"
            )


def _generate_payables(db: Session, inv: Invoice, net: Decimal) -> None:
    if inv.payables:
        # idempotent: already generated
        return
    if inv.terms_mode == "PERCENT":
        amounts = split_scadenze_percent(net, [t.percent for t in inv.terms])  # type: ignore[list-item]
    else:
        amounts = validate_amount_terms(net, [t.amount for t in inv.terms])  # type: ignore[list-item]
    for term, amount in zip(inv.terms, amounts, strict=True):
        db.add(
            Payable(
                invoice_id=inv.id,
                payment_term_id=term.id,
                sequence=term.sequence,
                due_date=term.due_date,
                amount=amount,
                balance=amount,
                currency=inv.currency,
                status="OPEN",
            )
        )
    db.flush()


def issue_invoice(
    db: Session,
    invoice_id: int,
    *,
    expected_version: int,
    allow_without_document: bool = False,
) -> Invoice:
    inv = repo.get_invoice_for_update(db, invoice_id)
    if not inv:
        raise InvoiceNotFound(invoice_id)
    if inv.status == "ISSUED":
        # idempotent re-call: ensure payables exist, no duplicate
        net = invoice_net(list(inv.items))
        assert net is not None
        _generate_payables(db, inv, net)
        return inv
    if inv.status != "DRAFT":
        raise InvalidTransition(f"Não é possível emitir fatura em status {inv.status}")

    net = _assert_ready_to_issue(db, inv, allow_without_doc=allow_without_document)
    _assert_qty_against_order(db, inv)
    _generate_payables(db, inv, net)
    inv.status = "ISSUED"
    inv.issued_at = datetime.now(timezone.utc)
    if allow_without_document and not documents_public.list_by_entity(db, "invoice", str(inv.id)):
        inv.issue_without_document = True
    return _lock(db, inv, expected_version)


def cancel_draft(
    db: Session,
    invoice_id: int,
    *,
    expected_version: int,
    reason_code: str | None = None,
) -> Invoice:
    inv = repo.get_invoice(db, invoice_id)
    if not inv:
        raise InvoiceNotFound(invoice_id)
    if inv.status == "CANCELLED":
        return inv
    if inv.status != "DRAFT":
        raise InvalidTransition("Inc-2: só é possível cancelar fatura em DRAFT (ISSUED é imutável)")
    inv.status = "CANCELLED"
    inv.cancelled_at = datetime.now(timezone.utc)
    inv.cancel_reason_code = (reason_code or "INVOICE_CANCEL_DRAFT").strip()
    return _lock(db, inv, expected_version)
