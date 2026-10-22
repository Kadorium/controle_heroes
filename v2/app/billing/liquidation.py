"""Liquidação de Payables — ownership Billing (Inc-3 + CUSTOMS_FUNDING)."""

from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.billing import repository as repo
from app.billing.errors import PayableConflict, PayableNotFound, PayableValidationError
from app.billing.models import Invoice, Payable
from app.billing.money import decimal_str, money2, parse_decimal

SOURCE_INVOICE = "INVOICE"
SOURCE_CUSTOMS_FUNDING = "CUSTOMS_FUNDING"
DERIVED_TO_PAY = "TO_PAY"
DERIVED_PARTIAL = "PARTIALLY_PAID"
DERIVED_PAID = "PAID"
DERIVED_NONE = "NONE"
DERIVED_LABELS = {
    DERIVED_TO_PAY: "A pagar",
    DERIVED_PARTIAL: "Parcialmente pago",
    DERIVED_PAID: "Pago",
    DERIVED_NONE: "—",
}


def _status_for_balance(amount: Decimal, balance: Decimal) -> str:
    if balance <= 0:
        return "PAID"
    if balance < amount:
        return "PARTIALLY_PAID"
    return "OPEN"


def normalize_tax_id(value: str | None) -> str | None:
    if value is None:
        return None
    compact = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    return compact or None


def normalize_payee_name(value: str | None) -> str | None:
    if value is None:
        return None
    compact = " ".join(str(value).split()).casefold()
    return compact or None


def customs_identity_matches(
    *,
    left_name: str | None,
    left_tax_id: str | None,
    right_name: str | None,
    right_tax_id: str | None,
) -> bool:
    """Regra exata CUSTOMS: tax ID se ambos têm; nome exato se nenhum tem; senão não associa."""
    left_tax = normalize_tax_id(left_tax_id)
    right_tax = normalize_tax_id(right_tax_id)
    if left_tax and right_tax:
        return left_tax == right_tax
    if left_tax or right_tax:
        return False
    left_n = normalize_payee_name(left_name)
    right_n = normalize_payee_name(right_name)
    if not left_n or not right_n:
        return False
    return left_n == right_n


def apply_payable_allocations(
    db: Session,
    applications: list[dict],
) -> list[Payable]:
    """Aplica valores aos Payables (ordem determinística por payable_id).

    Cada item: {payable_id, amount, expected_version}.
    Não cria PaymentAllocation. Locks FOR UPDATE + optimistic version → conflict.
    """
    if not applications:
        raise PayableValidationError("Informe ao menos uma aplicação")

    ids = [int(a["payable_id"]) for a in applications]
    if len(ids) != len(set(ids)):
        raise PayableValidationError("Payable duplicado no mesmo lote")

    ordered = sorted(applications, key=lambda a: int(a["payable_id"]))
    updated: list[Payable] = []
    for raw in ordered:
        payable_id = int(raw["payable_id"])
        expected_version = int(raw["expected_version"])
        amount = parse_decimal(raw["amount"])
        if amount is None or amount <= 0:
            raise PayableValidationError("Valor de alocação deve ser > 0")
        amount = money2(amount)

        row = repo.get_payable_for_update(db, payable_id)
        if not row:
            raise PayableNotFound(payable_id)
        if row.invoice_id is None and row.source_type != SOURCE_CUSTOMS_FUNDING:
            raise PayableValidationError(
                f"Payable #{payable_id} sem fatura (origem {row.source_type}) "
                "não é elegível para alocação via Payment"
            )
        if row.status in ("PAID", "CANCELLED"):
            raise PayableValidationError(
                f"Payable #{payable_id} não aceita liquidação (status {row.status})"
            )

        if amount > row.balance:
            raise PayableValidationError(
                f"Valor {amount} excede saldo {row.balance} do payable #{payable_id}"
            )
        if not repo.bump_payable_version_if_match(db, payable_id, expected_version):
            raise PayableConflict(payable_id)

        row = repo.get_payable(db, payable_id)
        assert row is not None
        row.balance = money2(row.balance - amount)
        row.status = _status_for_balance(row.amount, row.balance)
        db.flush()
        updated.append(row)
    return updated


def assert_payable_matches_payment(
    payable: Payable,
    *,
    currency: str,
    supplier_id: int | None,
    order_id: int | None = None,
    payee_display_name: str | None = None,
    payee_tax_id: str | None = None,
) -> None:
    """Contrato de settlement party — Invoice vs CUSTOMS_FUNDING, sem fuzzy."""
    cur = (currency or "").strip().upper()
    if payable.currency != cur:
        raise PayableValidationError(
            f"Payable #{payable.id} está em moeda diferente ({payable.currency})"
        )
    if payable.status in ("PAID", "CANCELLED"):
        raise PayableValidationError(
            f"Payable #{payable.id} não aceita liquidação (status {payable.status})"
        )

    if supplier_id is not None:
        if payable.invoice_id is None:
            raise PayableValidationError(
                f"Payable #{payable.id} sem fatura não é elegível para pagamento de fornecedor"
            )
        inv = payable.invoice
        if inv is None:
            raise PayableValidationError(f"Payable #{payable.id} sem fatura carregada")
        if inv.supplier_id != supplier_id:
            raise PayableValidationError(f"Payable #{payable.id} pertence a outro fornecedor")
        if order_id is not None and inv.order_id != order_id:
            raise PayableValidationError(
                f"Payable #{payable.id} pertence a outro pedido "
                f"(crédito do pedido {order_id}, obrigação do pedido {inv.order_id})"
            )
        return

    if order_id is not None:
        raise PayableValidationError("Pagamento de Numerário não aceita pedido")
    if payable.source_type != SOURCE_CUSTOMS_FUNDING or payable.invoice_id is not None:
        raise PayableValidationError(
            f"Payable #{payable.id} não é obrigação de Numerário (CUSTOMS_FUNDING)"
        )
    if not customs_identity_matches(
        left_name=payee_display_name,
        left_tax_id=payee_tax_id,
        right_name=payable.payee_display_name,
        right_tax_id=getattr(payable, "payee_tax_id", None),
    ):
        raise PayableValidationError(
            f"Payable #{payable.id} não pertence ao mesmo favorecido"
        )


def list_eligible_payables(
    db: Session,
    *,
    currency: str,
    supplier_id: int | None = None,
    order_id: int | None = None,
    payee_display_name: str | None = None,
    payee_tax_id: str | None = None,
    source_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Payable]:
    """Payables liquidáveis. Invoice: supplier+moeda. CUSTOMS: regra exata de favorecido."""
    cur = (currency or "").strip().upper()
    if supplier_id is not None:
        q = (
            db.query(Payable)
            .join(Invoice, Invoice.id == Payable.invoice_id)
            .filter(
                Invoice.supplier_id == supplier_id,
                Payable.currency == cur,
                Payable.status.in_(("OPEN", "PARTIALLY_PAID")),
                Payable.balance > 0,
            )
        )
        if order_id is not None:
            q = q.filter(Invoice.order_id == order_id)
        q = q.order_by(Payable.due_date.asc(), Payable.id.asc()).offset(offset).limit(limit)
        return list(q.all())

    src = (source_type or SOURCE_CUSTOMS_FUNDING).strip().upper()
    if src != SOURCE_CUSTOMS_FUNDING:
        raise PayableValidationError("source_type de elegibilidade sem fornecedor deve ser CUSTOMS_FUNDING")
    rows = (
        db.query(Payable)
        .filter(
            Payable.source_type == SOURCE_CUSTOMS_FUNDING,
            Payable.invoice_id.is_(None),
            Payable.currency == cur,
            Payable.status.in_(("OPEN", "PARTIALLY_PAID")),
            Payable.balance > 0,
        )
        .order_by(Payable.due_date.asc(), Payable.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        p
        for p in rows
        if customs_identity_matches(
            left_name=payee_display_name,
            left_tax_id=payee_tax_id,
            right_name=p.payee_display_name,
            right_tax_id=getattr(p, "payee_tax_id", None),
        )
    ]


def _derived_status(active: list[Payable]) -> tuple[str, str]:
    if not active:
        return DERIVED_NONE, DERIVED_LABELS[DERIVED_NONE]
    amount = money2(sum((p.amount for p in active), Decimal("0")))
    balance = money2(sum((p.balance for p in active), Decimal("0")))
    allocated = money2(amount - balance)
    if balance <= 0 and all(p.status == "PAID" or p.balance <= 0 for p in active):
        code = DERIVED_PAID
    elif allocated > 0:
        code = DERIVED_PARTIAL
    else:
        code = DERIVED_TO_PAY
    return code, DERIVED_LABELS[code]


def settlement_summary_for_source(
    db: Session,
    *,
    source_type: str,
    source_id: int,
) -> dict:
    """Fórmula canônica de liquidação por origem. Billing é o dono do saldo."""
    src = (source_type or "").strip().upper()
    if not src:
        raise PayableValidationError("source_type obrigatório")
    sid = int(source_id)
    rows = (
        db.query(Payable)
        .filter(Payable.source_type == src, Payable.source_id == sid)
        .order_by(Payable.sequence.asc(), Payable.id.asc())
        .all()
    )
    active = [p for p in rows if p.status != "CANCELLED"]
    amount = money2(sum((p.amount for p in active), Decimal("0")))
    balance = money2(sum((p.balance for p in active), Decimal("0")))
    allocated = money2(amount - balance)
    derived, label = _derived_status(active)
    currencies = {p.currency for p in active}
    payable_ids = [p.id for p in rows]
    refs = _allocation_refs(db, payable_ids)
    return {
        "source_type": src,
        "source_id": sid,
        "amount": decimal_str(amount) or "0.00",
        "allocated": decimal_str(allocated) or "0.00",
        "balance": decimal_str(balance) or "0.00",
        "currency": next(iter(currencies)) if len(currencies) == 1 else None,
        "derived_status": derived,
        "derived_status_label": label,
        "payable_statuses": [p.status for p in rows],
        "payables": [
            {
                "id": p.id,
                "status": p.status,
                "amount": decimal_str(p.amount) or "0.00",
                "balance": decimal_str(p.balance) or "0.00",
                "currency": p.currency,
                "version": p.version,
            }
            for p in rows
        ],
        "allocations": refs,
    }


def _allocation_refs(db: Session, payable_ids: list[int]) -> list[dict]:
    """Lê referências de alocação sem importar o módulo Treasury."""
    if not payable_ids:
        return []
    stmt = text(
        "SELECT id, payment_id, payable_id, amount "
        "FROM payment_allocations WHERE payable_id IN :ids ORDER BY id"
    ).bindparams(bindparam("ids", expanding=True))
    rows = db.execute(stmt, {"ids": payable_ids}).mappings().all()
    return [
        {
            "allocation_id": int(r["id"]),
            "payment_id": int(r["payment_id"]),
            "payable_id": int(r["payable_id"]),
            "amount": decimal_str(money2(Decimal(str(r["amount"])))) or "0.00",
        }
        for r in rows
    ]
