from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ExchangeRateType
from app.core.permissions import (
    PERM_APPROVE_PAYMENT_WITHOUT_RECEIPT,
    PERM_FINANCE_READ,
    PERM_FINANCE_WRITE,
    PERM_IMPORTATION_READ,
)
from app.core.permissions import role_has_permission
from app.database import get_db
from app.dependencies import require_permission
from app.models import (
    BrazilCurrentAccount,
    Credit,
    Discount,
    ExchangeRate,
    Expense,
    ImportationOrder,
    Invoice,
    Payment,
    User,
)
from app.schemas_import import (
    BrazilAccountCreate,
    BrazilAccountResponse,
    CancelRequest,
    CreditApplyRequest,
    CreditCreate,
    CreditResponse,
    DiscountCreate,
    DiscountResponse,
    ExchangeRateCreate,
    ExchangeRateResponse,
    ExpenseCreate,
    ExpenseResponse,
    FinancialSummaryResponse,
    FxReferenceResponse,
    FxPnlSummaryResponse,
    PaymentCreate,
    PaymentResponse,
    PaymentUpdate,
)
from app.services.auth import write_audit_log
from app.services.customs import CustomsValidationError, validate_customs_agent_expense
from app.services.finance import (
    apply_credit,
    ensure_settlement_exchange_rate,
    importation_financial_summary,
    invoice_balance,
    register_exchange_rate,
)
from app.services.fx_pnl import aggregate_fx_pnl, compute_fx_pnl
from app.services.fx_reference import fetch_fx_reference

router = APIRouter(prefix="/finance", tags=["finance"])


def _check_payment_receipt(payload: PaymentCreate, user: User) -> None:
    # Pagamento planejado (sem data de pagamento) pode ter só vencimento — sem comprovante ainda.
    if payload.payment_date is None and payload.due_date is not None:
        return
    if payload.receipt_reference or payload.approved_without_receipt:
        if payload.approved_without_receipt:
            perms = user.role.permissions or []
            if not role_has_permission(perms, PERM_APPROVE_PAYMENT_WITHOUT_RECEIPT):
                raise HTTPException(
                    status_code=403,
                    detail="Aprovação sem comprovante requer permissão finance:approve_payment_without_receipt",
                )
        return
    raise HTTPException(status_code=400, detail="Pagamento exige comprovante ou aprovação excepcional")


@router.get("/fx-reference", response_model=FxReferenceResponse)
def fx_reference(
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    currency_from: str = "EUR",
    currency_to: str = "BRL",
):
    """Cotação de referência EUR/BRL (fonte externa; não é cotação contratada)."""
    return fetch_fx_reference(currency_from, currency_to)


@router.get("/fx-pnl/summary", response_model=FxPnlSummaryResponse)
def fx_pnl_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
):
    """PnL Cambial consolidado — variação operacional vs provisão (não contábil)."""
    imps = db.query(ImportationOrder).filter(ImportationOrder.is_active.is_(True)).all()
    mark_rate = None
    ref = fetch_fx_reference()
    if ref.get("rate") is not None:
        mark_rate = Decimal(str(ref["rate"]))
    return aggregate_fx_pnl(db, [i.id for i in imps], mark_rate=mark_rate)


@router.get("/importations/{importation_id}/fx-pnl", response_model=FxPnlSummaryResponse)
def fx_pnl_for_importation(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
):
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    mark_rate = None
    ref = fetch_fx_reference()
    if ref.get("rate") is not None:
        mark_rate = Decimal(str(ref["rate"]))
    return compute_fx_pnl(db, importation_id, mark_rate=mark_rate)


@router.get("/importations/{importation_id}/summary", response_model=FinancialSummaryResponse)
def financial_summary(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
):
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    return importation_financial_summary(db, imp)


@router.get("/payments", response_model=list[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
    invoice_id: int | None = None,
):
    q = db.query(Payment).filter(Payment.is_active.is_(True))
    if invoice_id is not None:
        q = q.filter(Payment.invoice_id == invoice_id)
    return q.order_by(Payment.created_at).all()


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    _check_payment_receipt(payload, current_user)

    inv = db.query(Invoice).filter(Invoice.id == payload.invoice_id, Invoice.is_active.is_(True)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice não encontrada")

    payment = Payment(
        invoice_id=payload.invoice_id,
        payment_type=payload.payment_type,
        payment_date=payload.payment_date,
        due_date=payload.due_date,
        amount_foreign=payload.amount_foreign,
        amount_local=payload.amount_local,
        currency_foreign=payload.currency_foreign or inv.currency,
        exchange_rate=payload.exchange_rate,
        exchange_contract_number=payload.exchange_contract_number,
        settlement_date=payload.settlement_date,
        bank_name=payload.bank_name,
        receipt_reference=payload.receipt_reference,
        approved_without_receipt=payload.approved_without_receipt,
        created_by_id=current_user.id,
    )
    db.add(payment)
    db.flush()
    ensure_settlement_exchange_rate(db, payment)

    if payload.exchange_rate is not None:
        register_exchange_rate(
            db,
            currency_from=payment.currency_foreign or inv.currency,
            rate_type=ExchangeRateType.SETTLED.value,
            rate_value=payload.exchange_rate,
            user_id=current_user.id,
            importation_id=inv.importation_id,
            invoice_id=inv.id,
            payment_id=payment.id,
            comment="Câmbio efetivo do pagamento",
        )
        if inv.expected_exchange_rate and payload.exchange_rate != inv.expected_exchange_rate:
            write_audit_log(
                db,
                user_id=current_user.id,
                entity_type="payment",
                entity_id=str(payment.id),
                action="exchange_variance",
                field_changed="exchange_rate",
                old_value=str(inv.expected_exchange_rate),
                new_value=str(payload.exchange_rate),
            )

    bal = invoice_balance(db, inv)
    settled = (
        payment.payment_date is not None
        or payload.receipt_reference
        or payload.approved_without_receipt
    )
    if settled and bal is not None:
        if bal <= Decimal("0"):
            inv.payment_status = "PAID"
        elif inv.amount and bal < inv.amount:
            inv.payment_status = "PARTIAL"

    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="payment",
        entity_id=str(payment.id),
        action="create",
        new_value=str(payload.amount_foreign),
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/payments/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.is_active.is_(True)).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "receipt_reference" in data or "approved_without_receipt" in data:
        merged = PaymentCreate(
            invoice_id=payment.invoice_id,
            payment_type=payment.payment_type,
            payment_date=data.get("payment_date", payment.payment_date),
            due_date=data.get("due_date", payment.due_date),
            receipt_reference=data.get("receipt_reference", payment.receipt_reference),
            approved_without_receipt=data.get(
                "approved_without_receipt", payment.approved_without_receipt
            ),
        )
        _check_payment_receipt(merged, current_user)

    for key, value in data.items():
        setattr(payment, key, value)

    ensure_settlement_exchange_rate(db, payment)

    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="payment",
        entity_id=str(payment.id),
        action="update",
        new_value=str(data),
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/payments/{payment_id}/cancel", response_model=PaymentResponse)
def cancel_payment(
    payment_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.is_active.is_(True)).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    payment.is_active = False
    payment.cancelled_at = datetime.now(timezone.utc)
    payment.cancelled_by_id = current_user.id
    payment.cancellation_reason = payload.reason
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="payment",
        entity_id=str(payment.id),
        action="cancel",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/exchange-rates", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    payload: ExchangeRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    rate = register_exchange_rate(
        db,
        currency_from=payload.currency_from,
        rate_type=payload.rate_type,
        rate_value=payload.rate_value,
        user_id=current_user.id,
        importation_id=payload.importation_id,
        invoice_id=payload.invoice_id,
        payment_id=payload.payment_id,
        comment=payload.comment,
    )
    return rate


@router.get("/exchange-rates", response_model=list[ExchangeRateResponse])
def list_exchange_rates(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
    importation_id: int | None = None,
    invoice_id: int | None = None,
):
    q = db.query(ExchangeRate)
    if importation_id is not None:
        q = q.filter(ExchangeRate.importation_id == importation_id)
    if invoice_id is not None:
        q = q.filter(ExchangeRate.invoice_id == invoice_id)
    return q.order_by(ExchangeRate.created_at).all()


@router.post("/discounts", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
def create_discount(
    payload: DiscountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    inv = db.query(Invoice).filter(Invoice.id == payload.invoice_id, Invoice.is_active.is_(True)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice não encontrada")
    discount = Discount(**payload.model_dump(), created_by_id=current_user.id)
    db.add(discount)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="discount",
        entity_id=str(payload.invoice_id),
        action="create",
        new_value=str(payload.amount),
    )
    db.commit()
    db.refresh(discount)
    return discount


@router.get("/discounts", response_model=list[DiscountResponse])
def list_discounts(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
    invoice_id: int | None = None,
    importation_id: int | None = None,
):
    q = db.query(Discount).filter(Discount.is_active.is_(True))
    if invoice_id is not None:
        q = q.filter(Discount.invoice_id == invoice_id)
    elif importation_id is not None:
        inv_ids = [
            i.id
            for i in db.query(Invoice)
            .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True))
            .all()
        ]
        if not inv_ids:
            return []
        q = q.filter(Discount.invoice_id.in_(inv_ids))
    return q.order_by(Discount.created_at.desc()).all()


@router.post("/credits", response_model=CreditResponse, status_code=status.HTTP_201_CREATED)
def create_credit(
    payload: CreditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    credit = Credit(
        supplier_id=payload.supplier_id,
        amount=payload.amount,
        currency=payload.currency,
        amount_available=payload.amount,
        credit_type=payload.credit_type,
        origin_importation_id=payload.origin_importation_id,
        source_document_ref=payload.source_document_ref,
        created_by_id=current_user.id,
    )
    db.add(credit)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="credit",
        entity_id="new",
        action="create",
        new_value=str(payload.amount),
    )
    db.commit()
    db.refresh(credit)
    return credit


@router.get("/credits", response_model=list[CreditResponse])
def list_credits(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
    supplier_id: int | None = None,
):
    q = db.query(Credit).filter(Credit.is_active.is_(True))
    if supplier_id is not None:
        q = q.filter(Credit.supplier_id == supplier_id)
    return q.all()


@router.post("/credits/{credit_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_credit_to_importation(
    credit_id: int,
    payload: CreditApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    credit = db.query(Credit).filter(Credit.id == credit_id, Credit.is_active.is_(True)).first()
    if not credit:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")
    try:
        usage = apply_credit(
            db,
            credit,
            importation_id=payload.importation_id,
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"credit_usage_id": usage.id, "amount_used": str(usage.amount_used)}


@router.post("/brazil-accounts", response_model=BrazilAccountResponse, status_code=status.HTTP_201_CREATED)
def create_brazil_account(
    payload: BrazilAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    account = BrazilCurrentAccount(
        supplier_id=payload.supplier_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        amount_available=payload.amount,
        financial_impact_estimated=payload.financial_impact_estimated,
        fiscal_impact_estimated=payload.fiscal_impact_estimated,
        origin_credit_id=payload.origin_credit_id,
        origin_importation_id=payload.origin_importation_id,
        source_document_ref=payload.source_document_ref,
        created_by_id=current_user.id,
    )
    db.add(account)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="brazil_current_account",
        entity_id="new",
        action="create",
        impact_estimate=str(payload.financial_impact_estimated),
    )
    db.commit()
    db.refresh(account)
    return account


@router.get("/brazil-accounts", response_model=list[BrazilAccountResponse])
def list_brazil_accounts(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_FINANCE_READ)),
    supplier_id: int | None = None,
):
    q = db.query(BrazilCurrentAccount).filter(BrazilCurrentAccount.is_active.is_(True))
    if supplier_id is not None:
        q = q.filter(BrazilCurrentAccount.supplier_id == supplier_id)
    return q.all()


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == payload.importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    expense = Expense(**payload.model_dump(), created_by_id=current_user.id)
    try:
        validate_customs_agent_expense(expense)
    except CustomsValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    db.add(expense)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="expense",
        entity_id=str(payload.importation_id),
        action="create",
    )
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    importation_id: int | None = None,
):
    q = db.query(Expense).filter(Expense.is_active.is_(True))
    if importation_id is not None:
        q = q.filter(Expense.importation_id == importation_id)
    return q.all()
