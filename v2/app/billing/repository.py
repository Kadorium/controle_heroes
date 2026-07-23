from decimal import Decimal

from sqlalchemy import func, update
from sqlalchemy.orm import Session, joinedload

from app.billing.models import Invoice, InvoiceItem, Payable, PaymentTerm


def get_invoice(db: Session, invoice_id: int) -> Invoice | None:
    return (
        db.query(Invoice)
        .options(
            joinedload(Invoice.items),
            joinedload(Invoice.terms),
            joinedload(Invoice.payables),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )


def get_invoice_for_update(db: Session, invoice_id: int) -> Invoice | None:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).with_for_update().first()
    if not inv:
        return None
    return get_invoice(db, invoice_id)


def get_by_supplier_number(db: Session, supplier_id: int, invoice_number: str) -> Invoice | None:
    return (
        db.query(Invoice)
        .filter(
            Invoice.supplier_id == supplier_id,
            Invoice.invoice_number == invoice_number,
        )
        .first()
    )


def list_invoices(
    db: Session,
    *,
    order_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Invoice]:
    q = db.query(Invoice).options(joinedload(Invoice.items))
    if order_id is not None:
        q = q.filter(Invoice.order_id == order_id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.updated_at.desc()).offset(offset).limit(limit).all()


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
    q = db.query(Payable).join(Invoice)
    if order_id is not None:
        q = q.filter(Invoice.order_id == order_id)
    if invoice_id is not None:
        q = q.filter(Payable.invoice_id == invoice_id)
    if status:
        q = q.filter(Payable.status == status)
    if due_before is not None:
        q = q.filter(Payable.due_date <= due_before)
    if due_after is not None:
        q = q.filter(Payable.due_date >= due_after)
    return q.order_by(Payable.due_date.asc(), Payable.id.asc()).offset(offset).limit(limit).all()


def add_invoice(db: Session, invoice: Invoice) -> Invoice:
    db.add(invoice)
    db.flush()
    return invoice


def bump_version_if_match(db: Session, invoice_id: int, expected_version: int) -> bool:
    result = db.execute(
        update(Invoice)
        .where(Invoice.id == invoice_id, Invoice.version == expected_version)
        .values(version=expected_version + 1)
    )
    db.flush()
    return result.rowcount == 1  # type: ignore[attr-defined]


def bump_payable_version_if_match(db: Session, payable_id: int, expected_version: int) -> bool:
    result = db.execute(
        update(Payable)
        .where(Payable.id == payable_id, Payable.version == expected_version)
        .values(version=expected_version + 1)
    )
    db.flush()
    return result.rowcount == 1  # type: ignore[attr-defined]


def get_payable_for_update(db: Session, payable_id: int) -> Payable | None:
    return db.query(Payable).filter(Payable.id == payable_id).with_for_update().first()


def get_payable(db: Session, payable_id: int) -> Payable | None:
    return db.query(Payable).filter(Payable.id == payable_id).first()



def issued_qty_by_order_item(
    db: Session, order_id: int, *, exclude_invoice_id: int | None = None
) -> dict[int, Decimal]:
    q = (
        db.query(InvoiceItem.order_item_id, func.coalesce(func.sum(InvoiceItem.quantity), 0))
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .filter(Invoice.order_id == order_id, Invoice.status == "ISSUED")
    )
    if exclude_invoice_id is not None:
        q = q.filter(Invoice.id != exclude_invoice_id)
    q = q.group_by(InvoiceItem.order_item_id)
    return {row[0]: Decimal(str(row[1])) for row in q.all()}


def clear_items(db: Session, invoice: Invoice) -> None:
    for item in list(invoice.items):
        db.delete(item)
    db.flush()


def clear_terms(db: Session, invoice: Invoice) -> None:
    for term in list(invoice.terms):
        db.delete(term)
    db.flush()


def delete_payables(db: Session, invoice: Invoice) -> None:
    for p in list(invoice.payables):
        db.delete(p)
    db.flush()
