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
from app.treasury.models import PURPOSE_ADVANCE, PURPOSE_SETTLEMENT, Payment, PaymentAllocation, PaymentAllocationBatch


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


def unallocated_registered_bulk(db: Session) -> dict:
    """Residual REGISTERED por moeda/purpose — uma query, sem N+1."""
    alloc_sq = (
        db.query(
            PaymentAllocation.payment_id.label("payment_id"),
            func.coalesce(func.sum(PaymentAllocation.amount), 0).label("allocated"),
        )
        .group_by(PaymentAllocation.payment_id)
        .subquery()
    )
    residual = Payment.amount - func.coalesce(alloc_sq.c.allocated, 0)
    rows = (
        db.query(
            Payment.currency,
            Payment.purpose,
            func.count(Payment.id),
            func.coalesce(func.sum(residual), 0),
        )
        .outerjoin(alloc_sq, alloc_sq.c.payment_id == Payment.id)
        .filter(Payment.status == "REGISTERED", residual > 0)
        .group_by(Payment.currency, Payment.purpose)
        .all()
    )
    by_currency: dict[str, dict] = {}
    mixed = set()
    for currency, purpose, cnt, amount in rows:
        cur = str(currency or "")
        mixed.add(cur)
        entry = by_currency.setdefault(
            cur, {"currency": cur, "count": 0, "amount": Decimal("0"), "by_purpose": []}
        )
        amt = money2(Decimal(str(amount or 0)))
        entry["count"] += int(cnt or 0)
        entry["amount"] += amt
        entry["by_purpose"].append(
            {
                "purpose": purpose,
                "count": int(cnt or 0),
                "amount": f"{amt:.2f}",
            }
        )
    items = []
    for cur in sorted(by_currency):
        e = by_currency[cur]
        items.append(
            {
                "currency": cur,
                "count": e["count"],
                "amount": f"{money2(e['amount']):.2f}",
                "by_purpose": e["by_purpose"],
            }
        )
    return {"mixed_currency": len(mixed) > 1, "by_currency": items}


def unallocated_registered_list(db: Session, *, limit: int = 20) -> list[dict]:
    """Pagamentos REGISTERED com residual, com ids — sem filtrar depois do limit."""
    alloc_sq = (
        db.query(
            PaymentAllocation.payment_id.label("payment_id"),
            func.coalesce(func.sum(PaymentAllocation.amount), 0).label("allocated"),
        )
        .group_by(PaymentAllocation.payment_id)
        .subquery()
    )
    residual = Payment.amount - func.coalesce(alloc_sq.c.allocated, 0)
    rows = (
        db.query(Payment, residual.label("residual"))
        .outerjoin(alloc_sq, alloc_sq.c.payment_id == Payment.id)
        .filter(Payment.status == "REGISTERED", residual > 0)
        .order_by(Payment.payment_date.asc(), Payment.id.asc())
        .limit(limit)
        .all()
    )
    out = []
    for payment, residual_amt in rows:
        amt = money2(Decimal(str(residual_amt or 0)))
        title = (payment.payee_display_name or payment.external_reference or f"Pagamento {payment.id}").strip()
        out.append(
            {
                "kind": "unallocated_payment",
                "severity": "warning",
                "title": title,
                "reason": f"Registrado sem aplicar · {payment.currency} {amt:.2f}",
                "entity_id": payment.id,
                "href": f"/payments/{payment.id}",
                "since": payment.payment_date.isoformat() if payment.payment_date else None,
                "module": "treasury",
                "currency": payment.currency,
                "amount": f"{amt:.2f}",
            }
        )
    return out


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
    amount: str | Decimal,
    payment_date: date,
    created_by_actor_id: str,
    supplier_id: int | None = None,
    payable_id: int | None = None,
    currency: str | None = None,
    external_reference: str | None = None,
    idempotency_key: str | None = None,
    allow_without_document: bool = False,
    order_id: int | None = None,
    purpose: str | None = None,
) -> Payment:
    if idempotency_key:
        key = idempotency_key.strip()
        existing = db.query(Payment).filter(Payment.idempotency_key == key).first()
        if existing:
            return get_payment(db, existing.id)

    if purpose is not None and payable_id is not None:
        raise PaymentValidationError("purpose é definido pelo servidor a partir da obrigação")

    payee_display_name: str | None = None
    payee_tax_id: str | None = None
    resolved_supplier_id: int | None = supplier_id
    resolved_order_id = order_id
    resolved_purpose: str | None = None
    cur = (currency or "").strip().upper() if currency else ""

    if payable_id is not None:
        if supplier_id is not None:
            raise PaymentValidationError("payable_id não aceita supplier_id no corpo")
        if order_id is not None:
            raise PaymentValidationError("Pagamento de Numerário não aceita pedido")
        try:
            payable = billing_public.get_payable(db, int(payable_id))
        except billing_public.BillingError as e:
            raise PaymentValidationError(getattr(e, "message", str(e))) from e
        if payable.source_type != "CUSTOMS_FUNDING" or payable.invoice_id is not None:
            raise PaymentValidationError(
                "Pagamento sem fornecedor somente a partir de Payable CUSTOMS_FUNDING elegível"
            )
        if payable.status in ("PAID", "CANCELLED"):
            raise PaymentValidationError(
                f"Payable #{payable.id} não aceita registro de pagamento (status {payable.status})"
            )
        payable_cur = (payable.currency or "").strip().upper()
        if payable_cur != "BRL":
            raise PaymentValidationError(
                "Numerário em moeda estrangeira não é liquidável nesta versão"
            )
        if cur and cur != payable_cur:
            raise PaymentValidationError(
                f"Moeda do pagamento deve ser {payable_cur} (derivada da obrigação)"
            )
        name = (payable.payee_display_name or "").strip()
        if not name:
            raise PaymentValidationError("Obrigação de Numerário sem favorecido")
        payee_display_name = name
        payee_tax_id = (getattr(payable, "payee_tax_id", None) or "").strip() or None
        cur = payable_cur
        resolved_supplier_id = None
        resolved_order_id = None
        resolved_purpose = PURPOSE_SETTLEMENT
    else:
        if resolved_supplier_id is None:
            raise PaymentValidationError("supplier_id obrigatório quando não há payable_id")
        catalog_public.get_supplier(db, resolved_supplier_id)
        if len(cur) < 3:
            cur = "EUR"
        supplier = catalog_public.get_supplier(db, resolved_supplier_id)
        payee_display_name = supplier.name
        if purpose is not None:
            resolved_purpose = purpose.strip().upper()
            if resolved_purpose not in (PURPOSE_ADVANCE, PURPOSE_SETTLEMENT):
                raise PaymentValidationError("purpose do pagamento deve ser ADVANCE ou SETTLEMENT")
        elif order_id is not None:
            resolved_purpose = PURPOSE_SETTLEMENT

    amt = parse_decimal(amount)
    if amt is None or amt <= 0:
        raise PaymentValidationError("Valor do pagamento deve ser > 0")
    amt = money2(amt)
    if len(cur) < 3:
        raise PaymentValidationError("Moeda inválida")
    if not created_by_actor_id or not str(created_by_actor_id).strip():
        raise PaymentValidationError("Ator da criação é obrigatório")

    payment = Payment(
        supplier_id=resolved_supplier_id,
        order_id=resolved_order_id,
        purpose=resolved_purpose,
        payee_display_name=payee_display_name,
        payee_tax_id=payee_tax_id,
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

    # Validate settlement party via Billing (Invoice vs CUSTOMS_FUNDING)
    for raw in allocations:
        pid = int(raw["payable_id"])
        try:
            payable = billing_public.get_payable(db, pid)
            billing_public.assert_payable_matches_payment(
                payable,
                currency=payment.currency,
                supplier_id=payment.supplier_id,
                order_id=payment.order_id,
                payee_display_name=getattr(payment, "payee_display_name", None),
                payee_tax_id=getattr(payment, "payee_tax_id", None),
            )
        except billing_public.BillingError as e:
            raise PaymentValidationError(getattr(e, "message", str(e))) from e


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
    _link_existing_fx_to_new_allocations(
        db,
        payment_id=payment_id,
        batch_id=batch.id,
        created_by_actor_id=created_by_actor_id,
    )
    return get_payment(db, payment_id)


def _link_existing_fx_to_new_allocations(
    db: Session,
    *,
    payment_id: int,
    batch_id: int,
    created_by_actor_id: str,
) -> None:
    """Se o Payment já tem FxExecution (adiantamento), rateia BRL nas alocações novas.

    Sem execução ainda (saldo pago primeiro, câmbio depois) — não faz nada;
    o link continua no fluxo FX existente.
    """
    from app.treasury.fx_commands import link_execution_allocation, list_executions
    from app.treasury.fx_models import FxExecutionAllocation

    executions = list_executions(db, payment_id)
    if not executions:
        return
    execution = executions[0]
    used_raw = (
        db.query(func.coalesce(func.sum(FxExecutionAllocation.foreign_amount), 0))
        .filter(FxExecutionAllocation.fx_execution_id == execution.id)
        .scalar()
    )
    remaining = money2(execution.foreign_amount - money2(Decimal(str(used_raw))))
    allocs = (
        db.query(PaymentAllocation)
        .filter(PaymentAllocation.batch_id == batch_id)
        .order_by(PaymentAllocation.id.asc())
        .all()
    )
    for alloc in allocs:
        if remaining <= 0:
            break
        fa = money2(alloc.amount if alloc.amount <= remaining else remaining)
        if fa <= 0:
            continue
        link_execution_allocation(
            db,
            fx_execution_id=execution.id,
            payment_allocation_id=alloc.id,
            foreign_amount=fa,
            created_by_actor_id=created_by_actor_id,
        )
        remaining = money2(remaining - fa)


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
    order_id: int | None = None,
    status: str | None = None,
    currency: str | None = None,
    unallocated_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Payment]:
    q = db.query(Payment).options(joinedload(Payment.allocations))
    if supplier_id is not None:
        q = q.filter(Payment.supplier_id == supplier_id)
    if order_id is not None:
        q = q.filter(Payment.order_id == order_id)
    if status:
        q = q.filter(Payment.status == status)
    if currency:
        q = q.filter(Payment.currency == currency.upper())
    rows = q.order_by(Payment.payment_date.desc(), Payment.id.desc()).offset(offset).limit(limit).all()
    if unallocated_only:
        rows = [p for p in rows if amount_unallocated(db, p) > 0 and p.status == "REGISTERED"]
    return rows
