from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.billing import public as billing_public
from app.billing.errors import BillingError
from app.billing.models import Invoice
from app.billing.money import decimal_str
from app.documents import public as documents_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork

router = APIRouter(tags=["billing"])


class InvoiceCreate(BaseModel):
    invoice_number: str
    invoice_type: str = "FINAL"
    invoice_date: date | None = None
    notes: str | None = None
    order_item_ids: list[int] | None = None


class InvoiceUpdate(BaseModel):
    expected_version: int
    invoice_number: str | None = None
    invoice_type: str | None = None
    invoice_date: date | None = None
    notes: str | None = None


class InvoiceItemIn(BaseModel):
    order_item_id: int
    quantity: str
    unit_price_gross: str | None = None
    unit: str | None = None
    discount_type: str | None = None
    discount_unit_amount: str | None = None
    discount_percent: str | None = None


class ItemsReplace(BaseModel):
    expected_version: int
    items: list[InvoiceItemIn]


class TermIn(BaseModel):
    due_date: date
    percent: str | None = None
    amount: str | None = None


class TermsReplace(BaseModel):
    expected_version: int
    mode: str
    terms: list[TermIn]


class VersionBody(BaseModel):
    expected_version: int


class IssueBody(BaseModel):
    expected_version: int
    issue_without_document: bool = False
    reason_code: str | None = None


class CancelBody(BaseModel):
    expected_version: int
    reason_code: str | None = None


class InvoiceItemResponse(BaseModel):
    id: int
    order_item_id: int
    product_id: int
    sku_snapshot: str
    description_snapshot: str
    quantity: str
    unit: str | None = None
    unit_price_gross: str | None
    discount_type: str | None
    discount_unit_amount: str | None
    discount_percent: str | None
    line_gross_amount: str | None
    line_discount_amount: str | None
    line_net_amount: str | None
    position: int


class TermResponse(BaseModel):
    id: int
    sequence: int
    due_date: date
    percent: str | None
    amount: str | None


class PayableResponse(BaseModel):
    id: int
    invoice_id: int | None
    payment_term_id: int | None
    sequence: int
    due_date: date
    amount: str
    balance: str
    currency: str
    status: str
    source_type: str = "INVOICE"
    payee_display_name: str | None = None
    destination_iban: str | None = None
    destination_bank: str | None = None
    order_id: int | None = None
    supplier_id: int | None = None
    version: int = 1


class PayablePreview(BaseModel):
    sequence: str
    due_date: str
    amount: str


class DocumentBrief(BaseModel):
    id: int
    original_filename: str
    mime_type: str | None = None


class InvoiceResponse(BaseModel):
    id: int
    order_id: int
    order_code: str | None = None
    supplier_id: int
    supplier_name: str | None = None
    invoice_number: str
    invoice_type: str
    status: str
    invoice_date: date
    currency: str
    terms_mode: str | None
    created_by_actor_id: str
    notes: str | None
    version: int
    issued_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancel_reason_code: str | None = None
    issue_without_document: bool = False
    destination_iban: str | None = None
    destination_bank: str | None = None
    terms_from_document: bool = False
    net_amount: str | None = None
    incomplete_line_count: int = 0
    balance: str | None = None
    payables_sum: str | None = None
    items: list[InvoiceItemResponse] = Field(default_factory=list)
    terms: list[TermResponse] = Field(default_factory=list)
    payables: list[PayableResponse] = Field(default_factory=list)
    payables_preview: list[PayablePreview] = Field(default_factory=list)
    documents: list[DocumentBrief] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class InvoiceListItem(BaseModel):
    id: int
    order_id: int
    order_code: str | None = None
    supplier_id: int
    supplier_name: str | None = None
    invoice_number: str
    invoice_type: str
    status: str
    invoice_date: date
    currency: str
    version: int
    net_amount: str | None = None
    balance: str | None = None
    payable_count: int | None = None


class OrderQtyRow(BaseModel):
    order_item_id: int
    ordered_qty: str
    issued_qty: str
    available_qty: str
    line_kind: str | None = None
    description: str | None = None
    billable: bool = False


def _map_error(exc: BillingError) -> AppError:
    code = getattr(exc, "code", "billing_error")
    status = 400
    if str(code).endswith("not_found"):
        status = 404
    elif code in ("conflict", "invoice_not_draft", "invalid_transition"):
        status = 409
    return AppError(exc.message if hasattr(exc, "message") else str(exc), code=code, status_code=status)


def _invoice_response(db: Session, inv: Invoice) -> InvoiceResponse:
    totals = billing_public.invoice_totals_as_strings(inv)
    items = []
    for i in inv.items:
        am = billing_public.item_amounts_as_strings(i)
        items.append(
            InvoiceItemResponse(
                id=i.id,
                order_item_id=i.order_item_id,
                product_id=i.product_id,
                sku_snapshot=i.sku_snapshot,
                description_snapshot=i.description_snapshot,
                quantity=decimal_str(i.quantity) or "0",
                unit=i.unit,
                unit_price_gross=decimal_str(i.unit_price_gross),
                discount_type=i.discount_type,
                discount_unit_amount=decimal_str(i.discount_unit_amount),
                discount_percent=decimal_str(i.discount_percent),
                line_gross_amount=am["line_gross_amount"],
                line_discount_amount=am["line_discount_amount"],
                line_net_amount=am["line_net_amount"],
                position=i.position,
            )
        )
    terms = [
        TermResponse(
            id=t.id,
            sequence=t.sequence,
            due_date=t.due_date,
            percent=decimal_str(t.percent),
            amount=decimal_str(t.amount),
        )
        for t in inv.terms
    ]
    payables = [
        PayableResponse(
            id=p.id,
            invoice_id=p.invoice_id,
            payment_term_id=p.payment_term_id,
            sequence=p.sequence,
            due_date=p.due_date,
            amount=decimal_str(p.amount) or "0",
            balance=decimal_str(p.balance) or "0",
            currency=p.currency,
            status=p.status,
            source_type=getattr(p, "source_type", None) or "INVOICE",
            payee_display_name=getattr(p, "payee_display_name", None),
            destination_iban=getattr(p, "destination_iban", None),
            destination_bank=getattr(p, "destination_bank", None),
            order_id=inv.order_id,
            supplier_id=inv.supplier_id,
            version=getattr(p, "version", 1),
        )
        for p in inv.payables
    ]
    preview = [PayablePreview(**row) for row in billing_public.preview_payables(inv)]
    docs = [
        DocumentBrief(
            id=d.id,
            original_filename=d.original_filename,
            mime_type=d.mime_type,
        )
        for d in documents_public.list_by_entity(db, "invoice", str(inv.id))
    ]
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public

    order_code = None
    try:
        order = orders_public.get_order(db, inv.order_id)
        order_code = order.code
    except orders_public.OrdersError:
        order_code = None
    suppliers = catalog_public.get_suppliers_bulk(db, {inv.supplier_id})
    supplier_name = suppliers.get(inv.supplier_id)
    return InvoiceResponse(
        id=inv.id,
        order_id=inv.order_id,
        order_code=order_code,
        supplier_id=inv.supplier_id,
        supplier_name=supplier_name.name if supplier_name else None,
        invoice_number=inv.invoice_number,
        invoice_type=inv.invoice_type,
        status=inv.status,
        invoice_date=inv.invoice_date,
        currency=inv.currency,
        terms_mode=inv.terms_mode,
        created_by_actor_id=inv.created_by_actor_id,
        notes=inv.notes,
        version=inv.version,
        issued_at=inv.issued_at,
        cancelled_at=inv.cancelled_at,
        cancel_reason_code=inv.cancel_reason_code,
        issue_without_document=bool(inv.issue_without_document),
        destination_iban=getattr(inv, "destination_iban", None),
        destination_bank=getattr(inv, "destination_bank", None),
        terms_from_document=bool(getattr(inv, "terms_from_document", False)),
        net_amount=totals["net_amount"],  # type: ignore[arg-type]
        incomplete_line_count=int(totals["incomplete_line_count"] or 0),
        balance=totals["balance"],  # type: ignore[arg-type]
        payables_sum=totals["payables_sum"],  # type: ignore[arg-type]
        items=items,
        terms=terms,
        payables=payables,
        payables_preview=preview,
        documents=docs,
        blockers=billing_public.issue_blockers(db, inv),
    )


@router.post("/orders/{order_id}/invoices", response_model=InvoiceResponse)
def create_invoice(
    order_id: int,
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:write")
    try:
        with UnitOfWork(db) as uow:
            inv = billing_public.create_invoice(
                uow.session,
                order_id=order_id,
                invoice_number=payload.invoice_number,
                created_by_actor_id=str(user.id),
                invoice_type=payload.invoice_type,
                invoice_date=payload.invoice_date,
                notes=payload.notes,
                order_item_ids=payload.order_item_ids,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="invoice",
                entity_id=str(inv.id),
                action="create",
                reason_code="INVOICE_CREATE",
            )
            uow.commit()
            inv = billing_public.get_invoice(uow.session, inv.id)
            return _invoice_response(uow.session, inv)
    except BillingError as e:
        raise _map_error(e) from e


@router.get("/orders/{order_id}/invoices", response_model=list[InvoiceListItem])
def list_order_invoices(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:read")
    from app.orders import public as orders_public

    rows = billing_public.list_invoices(db, order_id=order_id, limit=100)
    order = None
    try:
        order = orders_public.get_order(db, order_id)
    except orders_public.OrdersError:
        order = None
    out = []
    for inv in rows:
        full = billing_public.get_invoice(db, inv.id)
        totals = billing_public.invoice_totals_as_strings(full)
        out.append(
            InvoiceListItem(
                id=full.id,
                order_id=full.order_id,
                order_code=order.code if order else None,
                supplier_id=full.supplier_id,
                invoice_number=full.invoice_number,
                invoice_type=full.invoice_type,
                status=full.status,
                invoice_date=full.invoice_date,
                currency=full.currency,
                version=full.version,
                net_amount=totals["net_amount"],  # type: ignore[arg-type]
                balance=totals["balance"],  # type: ignore[arg-type]
            )
        )
    return out


@router.get("/orders/{order_id}/invoiced-quantities", response_model=list[OrderQtyRow])
def order_invoiced_quantities(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:read")
    try:
        rows = billing_public.order_qty_availability(db, order_id)
    except BillingError as e:
        raise _map_error(e) from e
    return [OrderQtyRow(**row) for row in rows]  # type: ignore[arg-type]


@router.get("/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    order_id: int | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:read")
    rows = billing_public.list_invoices(db, order_id=order_id, status=status, limit=limit, offset=offset)
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public

    suppliers = catalog_public.get_suppliers_bulk(db, {inv.supplier_id for inv in rows})
    orders = orders_public.get_orders_bulk(db, {inv.order_id for inv in rows})
    counts = billing_public.payable_counts_by_invoice(db, [inv.id for inv in rows])
    out = []
    for inv in rows:
        full = billing_public.get_invoice(db, inv.id)
        totals = billing_public.invoice_totals_as_strings(full)
        supplier = suppliers.get(full.supplier_id)
        order = orders.get(full.order_id)
        out.append(
            InvoiceListItem(
                id=full.id,
                order_id=full.order_id,
                order_code=order.code if order else None,
                supplier_id=full.supplier_id,
                supplier_name=supplier.name if supplier else None,
                invoice_number=full.invoice_number,
                invoice_type=full.invoice_type,
                status=full.status,
                invoice_date=full.invoice_date,
                currency=full.currency,
                version=full.version,
                net_amount=totals["net_amount"],  # type: ignore[arg-type]
                balance=totals["balance"],  # type: ignore[arg-type]
                payable_count=counts.get(full.id, 0 if full.status == "ISSUED" else None),
            )
        )
    return out


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "billing:read")
    try:
        inv = billing_public.get_invoice(db, invoice_id)
        return _invoice_response(db, inv)
    except BillingError as e:
        raise _map_error(e) from e


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:write")
    try:
        with UnitOfWork(db) as uow:
            inv = billing_public.update_invoice_header(
                uow.session,
                invoice_id,
                expected_version=payload.expected_version,
                invoice_number=payload.invoice_number,
                invoice_type=payload.invoice_type,
                invoice_date=payload.invoice_date,
                notes=payload.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="invoice",
                entity_id=str(inv.id),
                action="update",
                reason_code="INVOICE_UPDATE",
            )
            uow.commit()
            return _invoice_response(uow.session, billing_public.get_invoice(uow.session, inv.id))
    except BillingError as e:
        raise _map_error(e) from e


@router.put("/invoices/{invoice_id}/items", response_model=InvoiceResponse)
def replace_items(
    invoice_id: int,
    payload: ItemsReplace,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:write")
    try:
        with UnitOfWork(db) as uow:
            inv = billing_public.replace_items(
                uow.session,
                invoice_id,
                expected_version=payload.expected_version,
                items=[i.model_dump(exclude_unset=True) for i in payload.items],
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="invoice",
                entity_id=str(inv.id),
                action="replace_items",
                reason_code="INVOICE_ITEMS",
            )
            uow.commit()
            return _invoice_response(uow.session, billing_public.get_invoice(uow.session, inv.id))
    except BillingError as e:
        raise _map_error(e) from e


@router.put("/invoices/{invoice_id}/terms", response_model=InvoiceResponse)
def set_terms(
    invoice_id: int,
    payload: TermsReplace,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:write")
    try:
        with UnitOfWork(db) as uow:
            inv = billing_public.set_terms(
                uow.session,
                invoice_id,
                expected_version=payload.expected_version,
                mode=payload.mode,
                terms=[t.model_dump() for t in payload.terms],
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="invoice",
                entity_id=str(inv.id),
                action="set_terms",
                reason_code="INVOICE_TERMS",
            )
            uow.commit()
            return _invoice_response(uow.session, billing_public.get_invoice(uow.session, inv.id))
    except BillingError as e:
        raise _map_error(e) from e


@router.post("/invoices/{invoice_id}/issue", response_model=InvoiceResponse)
def issue_invoice(
    invoice_id: int,
    payload: IssueBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:issue")
    if payload.issue_without_document:
        enforce_permission(user, "billing:issue_without_doc")
        if not (payload.reason_code or "").strip():
            raise AppError(
                "Override sem documento exige reason_code",
                code="validation_error",
                status_code=400,
            )
    try:
        with UnitOfWork(db) as uow:
            inv = billing_public.issue_invoice(
                uow.session,
                invoice_id,
                expected_version=payload.expected_version,
                allow_without_document=payload.issue_without_document,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="invoice",
                entity_id=str(inv.id),
                action="issue",
                reason_code=payload.reason_code or "INVOICE_ISSUE",
                details="without_doc" if payload.issue_without_document else None,
            )
            uow.commit()
            return _invoice_response(uow.session, billing_public.get_invoice(uow.session, inv.id))
    except BillingError as e:
        raise _map_error(e) from e


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    payload: CancelBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:write")
    try:
        with UnitOfWork(db) as uow:
            inv = billing_public.cancel_draft(
                uow.session,
                invoice_id,
                expected_version=payload.expected_version,
                reason_code=payload.reason_code,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="invoice",
                entity_id=str(inv.id),
                action="cancel_draft",
                reason_code=payload.reason_code or "INVOICE_CANCEL_DRAFT",
            )
            uow.commit()
            return _invoice_response(uow.session, billing_public.get_invoice(uow.session, inv.id))
    except BillingError as e:
        raise _map_error(e) from e


def _payable_response(p) -> PayableResponse:
    inv = getattr(p, "invoice", None)
    return PayableResponse(
        id=p.id,
        invoice_id=p.invoice_id,
        payment_term_id=p.payment_term_id,
        sequence=p.sequence,
        due_date=p.due_date,
        amount=decimal_str(p.amount) or "0",
        balance=decimal_str(p.balance) or "0",
        currency=p.currency,
        status=p.status,
        source_type=getattr(p, "source_type", None) or "INVOICE",
        payee_display_name=getattr(p, "payee_display_name", None),
        destination_iban=getattr(p, "destination_iban", None),
        destination_bank=getattr(p, "destination_bank", None),
        order_id=inv.order_id if inv is not None else None,
        supplier_id=inv.supplier_id if inv is not None else None,
        version=getattr(p, "version", 1),
    )


@router.get("/payables", response_model=list[PayableResponse])
def list_payables(
    order_id: int | None = None,
    invoice_id: int | None = None,
    status: str | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "billing:read")
    rows = billing_public.list_payables(
        db,
        order_id=order_id,
        invoice_id=invoice_id,
        status=status,
        due_before=due_before,
        due_after=due_after,
        limit=limit,
        offset=offset,
    )
    return [_payable_response(p) for p in rows]


@router.get("/payables/{payable_id}", response_model=PayableResponse)
def get_payable(
    payable_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Read-only — contexto SCR-009 sem scan listPayables(limit=100)."""
    enforce_permission(user, "billing:read")
    try:
        p = billing_public.get_payable(db, payable_id)
        return _payable_response(p)
    except BillingError as e:
        raise _map_error(e) from e
