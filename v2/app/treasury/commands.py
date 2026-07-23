import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, update
from sqlalchemy.orm import Session, joinedload

from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.documents import public as documents_public
from app.treasury.errors import (
    InvalidTransition,
    PaymentConflict,
    PaymentNotFound,
    PaymentValidationError,
)
from app.treasury.models import Payment, PaymentAllocation, PaymentAllocationBatch


def money2(value: Decimal) -> Decimal:
    from decimal import ROUND_HALF_UP

    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if s == "":
        return None
    return Decimal(s)


def get_payment(db: Session, payment_id: int) -> Payment:
    row = (
        db.query(Payment)
        .options(joinedload(Payment.allocations), joinedload(Payment.batches))
        .filter(Payment.id == payment_id)
        .first()
    )
    if not row:
        raise PaymentNotFound(payment_id)
    return row


def get_payment_for_update(db: Session, payment_id: int) -> Payment:
    row = db.query(Payment).filter(Payment.id == payment_id).with_for_update().first()
    if not row:
        raise PaymentNotFound(payment_id)
    return get_payment(db, payment_id)


def allocated_sum(db: Session, payment_id: int) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .filter(PaymentAllocation.payment_id == payment_id)
        .scalar()
    )
    return money2(Decimal(str(total)))


def amount_unallocated(db: Session, payment: Payment) -> Decimal:
    return money2(payment.amount - allocated_sum(db, payment.id))


def bump_payment_version(db: Session, payment_id: int, expected_version: int) -> bool:
    result = db.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.version == expected_version)
        .values(version=expected_version + 1)
    )
    db.flush()
    return result.rowcount == 1  # type: ignore[attr-defined]


def _payload_hash(allocations: list[dict]) -> str:
    normalized = sorted(
        [
            {
                "payable_id": int(a["payable_id"]),
                "amount": str(money2(parse_decimal(a["amount"]) or Decimal("0"))),
                "expected_version": int(a["expected_version"]),
            }
            for a in allocations
        ],
        key=lambda x: x["payable_id"],
    )
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def register_payment(
    db: Session,
    *,
    supplier_id: int,
    amount: str | Decimal,
    currency: str,
    payment_date: date,
    created_by_actor_id: str,
    external_reference: str | None = None,
    idempotency_key: str | None = None,
    allow_without_document: bool = False,
) -> Payment:
    if idempotency_key:
        key = idempotency_key.strip()
        existing = db.query(Payment).filter(Payment.idempotency_key == key).first()
        if existing:
            return get_payment(db, existing.id)

    catalog_public.get_supplier(db, supplier_id)
    amt = parse_decimal(amount)
    if amt is None or amt <= 0:
        raise PaymentValidationError("Valor do pagamento deve ser > 0")
    amt = money2(amt)
    cur = (currency or "").strip().upper()
    if len(cur) < 3:
        raise PaymentValidationError("Moeda inválida")
    if not created_by_actor_id or not str(created_by_actor_id).strip():
        raise PaymentValidationError("Ator da criação é obrigatório")

    docs = []  # checked by caller after flush with known id — register creates first
    payment = Payment(
        supplier_id=supplier_id,
        amount=amt,
        currency=cur,
        payment_date=payment_date,
        external_reference=external_reference.strip() if external_reference else None,
        status="REGISTERED",
        created_by_actor_id=str(created_by_actor_id).strip(),
        version=1,
        idempotency_key=idempotency_key.strip() if idempotency_key else None,
        register_without_document=allow_without_document,
    )
    db.add(payment)
    db.flush()

    if not allow_without_document:
        docs = documents_public.list_by_entity(db, "payment", str(payment.id))
        if not docs:
            # Caller must link doc in same UoW after create — flag for route validation
            payment.register_without_document = False
    return get_payment(db, payment.id)


def assert_payment_has_document(db: Session, payment: Payment, *, allow_without: bool) -> None:
    docs = documents_public.list_by_entity(db, "payment", str(payment.id))
    if not docs and not allow_without:
        raise PaymentValidationError(
            "Comprovante obrigatório. Anexe o documento ou use override autorizado."
        )
    if allow_without and not docs:
        payment.register_without_document = True


def allocate_payment(
    db: Session,
    payment_id: int,
    *,
    expected_version: int,
    allocations: list[dict],
    created_by_actor_id: str,
    batch_idempotency_key: str,
) -> Payment:
    """Lote atômico. Mesma chave+payload → replay; mesma chave+payload diferente → 409."""
    key = (batch_idempotency_key or "").strip()
    if not key:
        raise PaymentValidationError("idempotency_key do lote é obrigatória")
    if not allocations:
        raise PaymentValidationError("Informe ao menos uma alocação")

    payment = get_payment_for_update(db, payment_id)
    if payment.status != "REGISTERED":
        raise InvalidTransition("Somente pagamentos REGISTERED aceitam alocação")

    payload_hash = _payload_hash(allocations)
    existing_batch = (
        db.query(PaymentAllocationBatch)
        .filter(
            PaymentAllocationBatch.payment_id == payment_id,
            PaymentAllocationBatch.idempotency_key == key,
        )
        .first()
    )
    if existing_batch:
        if existing_batch.payload_hash != payload_hash:
            raise PaymentConflict(
                "Chave de idempotência reutilizada com payload diferente"
            )
        return get_payment(db, payment_id)

    residual = amount_unallocated(db, payment)
    total_new = money2(
        sum((money2(parse_decimal(a["amount"]) or Decimal("0")) for a in allocations), Decimal("0"))
    )
    if total_new > residual:
        raise PaymentValidationError(
            f"Soma das alocações ({total_new}) excede residual do pagamento ({residual})"
        )

    # Validate supplier/currency via eligible set
    for raw in allocations:
        pid = int(raw["payable_id"])
        try:
            payable = billing_public.get_payable(db, pid)
        except billing_public.BillingError as e:
            raise PaymentValidationError(getattr(e, "message", str(e))) from e
        inv = billing_public.get_invoice(db, payable.invoice_id)
        if inv.supplier_id != payment.supplier_id:
            raise PaymentValidationError(
                f"Payable #{pid} pertence a outro fornecedor"
            )
        if payable.currency != payment.currency:
            raise PaymentValidationError(
                f"Payable #{pid} está em moeda diferente ({payable.currency})"
            )

    applications = [
        {
            "payable_id": int(a["payable_id"]),
            "amount": a["amount"],
            "expected_version": int(a["expected_version"]),
        }
        for a in allocations
    ]

    try:
        billing_public.apply_payable_allocations(db, applications)
    except billing_public.BillingError as e:
        # map to treasury conflict/validation
        code = getattr(e, "code", "validation_error")
        if code == "conflict":
            raise PaymentConflict(getattr(e, "message", str(e))) from e
        raise PaymentValidationError(getattr(e, "message", str(e))) from e

    if not bump_payment_version(db, payment_id, expected_version):
        raise PaymentConflict()

    batch = PaymentAllocationBatch(
        payment_id=payment_id,
        idempotency_key=key,
        payload_hash=payload_hash,
        created_by_actor_id=str(created_by_actor_id).strip(),
    )
    db.add(batch)
    db.flush()
    for raw in allocations:
        db.add(
            PaymentAllocation(
                payment_id=payment_id,
                payable_id=int(raw["payable_id"]),
                batch_id=batch.id,
                amount=money2(parse_decimal(raw["amount"]) or Decimal("0")),
                created_by_actor_id=str(created_by_actor_id).strip(),
            )
        )
    db.flush()
    return get_payment(db, payment_id)


def cancel_payment(
    db: Session,
    payment_id: int,
    *,
    expected_version: int,
    reason_code: str | None = None,
) -> Payment:
    payment = get_payment_for_update(db, payment_id)
    if payment.status == "CANCELLED":
        return payment
    if payment.status != "REGISTERED":
        raise InvalidTransition("Status inválido para cancelamento")
    if allocated_sum(db, payment_id) > 0:
        raise InvalidTransition(
            "Pagamento com alocações não pode ser cancelado no Inc-3"
        )
    if not bump_payment_version(db, payment_id, expected_version):
        raise PaymentConflict()
    payment = get_payment(db, payment_id)
    payment.status = "CANCELLED"
    payment.cancelled_at = datetime.now(timezone.utc)
    payment.cancel_reason_code = (reason_code or "PAYMENT_CANCEL").strip()
    db.flush()
    return get_payment(db, payment_id)


def list_payments(
    db: Session,
    *,
    supplier_id: int | None = None,
    status: str | None = None,
    unallocated_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Payment]:
    q = db.query(Payment).options(joinedload(Payment.allocations))
    if supplier_id is not None:
        q = q.filter(Payment.supplier_id == supplier_id)
    if status:
        q = q.filter(Payment.status == status)
    rows = q.order_by(Payment.payment_date.desc(), Payment.id.desc()).offset(offset).limit(limit).all()
    if unallocated_only:
        rows = [p for p in rows if amount_unallocated(db, p) > 0 and p.status == "REGISTERED"]
    return rows
