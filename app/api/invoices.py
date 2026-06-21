from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ExchangeRateType
from app.core.permissions import PERM_FINANCE_READ, PERM_FINANCE_WRITE, PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import ImportationOrder, Invoice, InvoiceItem, User
from app.schemas_import import CancelRequest, InvoiceCreate, InvoiceItemResponse, InvoiceResponse, InvoiceUpdate
from app.services.auth import write_audit_log
from app.services.finance import invoice_balance, invoice_paid_total, register_exchange_rate

router = APIRouter(prefix="/invoices", tags=["invoices"])

AUDITED_FIELDS = ("invoice_type", "invoice_number", "invoice_date", "amount", "discount_amount", "expected_exchange_rate")


def _invoice_response(db: Session, inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=inv.id,
        importation_id=inv.importation_id,
        invoice_type=inv.invoice_type,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        amount=inv.amount,
        currency=inv.currency,
        discount_amount=inv.discount_amount,
        expected_exchange_rate=inv.expected_exchange_rate,
        payment_status=inv.payment_status,
        is_active=inv.is_active,
        balance=invoice_balance(db, inv),
        paid_total=invoice_paid_total(db, inv),
    )


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    importation_id: int | None = None,
    include_inactive: bool = False,
):
    q = db.query(Invoice)
    if importation_id is not None:
        q = q.filter(Invoice.importation_id == importation_id)
    if not include_inactive:
        q = q.filter(Invoice.is_active.is_(True))
    invoices = q.order_by(Invoice.created_at).all()
    return [_invoice_response(db, inv) for inv in invoices]


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == payload.importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")

    inv = Invoice(
        importation_id=payload.importation_id,
        invoice_type=payload.invoice_type,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        amount=payload.amount,
        currency=payload.currency,
        discount_amount=payload.discount_amount,
        expected_exchange_rate=payload.expected_exchange_rate,
        notes=payload.notes,
        payment_status="OPEN",
    )
    db.add(inv)
    db.flush()

    for item_data in payload.items:
        db.add(InvoiceItem(invoice_id=inv.id, **item_data.model_dump()))

    if payload.expected_exchange_rate is not None:
        register_exchange_rate(
            db,
            currency_from=payload.currency,
            rate_type=ExchangeRateType.ESTIMATED.value,
            rate_value=payload.expected_exchange_rate,
            user_id=current_user.id,
            importation_id=payload.importation_id,
            invoice_id=inv.id,
            comment="Câmbio previsto na criação da invoice",
        )

    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=str(inv.id),
        action="create",
        new_value=payload.invoice_type,
    )
    db.commit()
    db.refresh(inv)
    return _invoice_response(db, inv)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice não encontrada")
    return _invoice_response(db, inv)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_active.is_(True)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice não encontrada")

    updates = payload.model_dump(exclude_unset=True)
    for field in AUDITED_FIELDS:
        if field not in updates:
            continue
        old_val = getattr(inv, field)
        new_val = updates[field]
        if old_val != new_val:
            write_audit_log(
                db,
                user_id=current_user.id,
                entity_type="invoice",
                entity_id=str(inv.id),
                action="update",
                field_changed=field,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
            )

    if "expected_exchange_rate" in updates and updates["expected_exchange_rate"] is not None:
        register_exchange_rate(
            db,
            currency_from=inv.currency,
            rate_type=ExchangeRateType.REVISED.value,
            rate_value=updates["expected_exchange_rate"],
            user_id=current_user.id,
            importation_id=inv.importation_id,
            invoice_id=inv.id,
            comment="Revisão de câmbio previsto",
        )

    for field, value in updates.items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return _invoice_response(db, inv)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_active.is_(True)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice não encontrada")
    inv.is_active = False
    inv.cancelled_at = datetime.now(timezone.utc)
    inv.cancelled_by_id = current_user.id
    inv.cancellation_reason = payload.reason
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=str(inv.id),
        action="cancel",
        field_changed="is_active",
        old_value="True",
        new_value="False",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(inv)
    return _invoice_response(db, inv)


@router.get("/{invoice_id}/items", response_model=list[InvoiceItemResponse])
def list_invoice_items(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return (
        db.query(InvoiceItem)
        .filter(InvoiceItem.invoice_id == invoice_id, InvoiceItem.is_active.is_(True))
        .all()
    )
