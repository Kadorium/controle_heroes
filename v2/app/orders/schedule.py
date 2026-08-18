"""FIN-4 — cronograma de pagamento (planejamento). Sem fatos financeiros."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.orders import repository as repo
from app.orders.errors import InvalidTransition, OrderNotFound, OrderValidationError
from app.orders.models import Order, OrderPaymentScheduleLine
from app.orders.money import decimal_str, money2, parse_decimal, split_percent_amounts
from app.orders.queries import compute_totals

MODE_PERCENT = "PERCENT"
MODE_AMOUNT = "AMOUNT"
COHERENCE_ALIGNED = "aligned"
COHERENCE_DIVERGENT = "divergent"
COHERENCE_UNVERIFIABLE = "unverifiable"


def _condition_text(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) > 256:
        raise OrderValidationError(
            "condition_text máximo 256 caracteres",
            code="validation_error",
        )
    return s


def _parse_due(raw) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw))


def snapshot_lines(lines: list[OrderPaymentScheduleLine]) -> list[dict]:
    out = []
    for line in lines:
        out.append(
            {
                "sequence": line.sequence,
                "due_date": line.due_date.isoformat() if line.due_date else None,
                "condition_text": line.condition_text,
                "percent": decimal_str(line.percent),
                "amount": decimal_str(line.amount),
            }
        )
    return out


def infer_mode(lines: list[OrderPaymentScheduleLine]) -> str | None:
    if not lines:
        return None
    has_pct = any(ln.percent is not None for ln in lines)
    has_amt = any(ln.amount is not None for ln in lines)
    if has_pct and has_amt:
        raise OrderValidationError(
            "Cronograma não pode misturar percentual e valor",
            code="schedule_mode_mixed",
        )
    if has_pct:
        return MODE_PERCENT
    return MODE_AMOUNT


def _amount_sum(lines: list[OrderPaymentScheduleLine]) -> Decimal | None:
    if not lines or any(ln.amount is None for ln in lines):
        return None
    return money2(sum((ln.amount for ln in lines), Decimal("0")))


def derived_amounts(
    lines: list[OrderPaymentScheduleLine], commercial_total: Decimal | None
) -> list[Decimal | None]:
    mode = infer_mode(lines)
    if mode == MODE_AMOUNT:
        return [money2(ln.amount) if ln.amount is not None else None for ln in lines]
    if mode == MODE_PERCENT:
        if commercial_total is None:
            return [None] * len(lines)
        percents = [ln.percent or Decimal("0") for ln in lines]
        return split_percent_amounts(money2(commercial_total), percents)
    return []


def coherence(
    *,
    mode: str | None,
    commercial_total: Decimal | None,
    amount_sum: Decimal | None,
) -> tuple[str, Decimal | None]:
    """Retorna (coherence, delta). delta None se não verificável — nunca zero fictício."""
    if mode is None:
        return COHERENCE_UNVERIFIABLE, None
    if commercial_total is None or amount_sum is None:
        return COHERENCE_UNVERIFIABLE, None
    total = money2(commercial_total)
    summed = money2(amount_sum)
    delta = money2(summed - total)
    if delta == Decimal("0.00"):
        return COHERENCE_ALIGNED, delta
    return COHERENCE_DIVERGENT, delta


def build_view(db: Session, order: Order) -> dict:
    lines = repo.list_schedule_lines(db, order.id)
    totals = compute_totals(list(order.items or []))
    commercial_total = totals.commercial_total
    mode = infer_mode(lines) if lines else None
    derived = derived_amounts(lines, commercial_total) if lines else []
    if mode == MODE_AMOUNT:
        amount_sum = _amount_sum(lines)
    elif mode == MODE_PERCENT and commercial_total is not None:
        amount_sum = money2(sum((d for d in derived if d is not None), Decimal("0")))
    else:
        amount_sum = None
    coh, delta = coherence(mode=mode, commercial_total=commercial_total, amount_sum=amount_sum)
    line_payloads = []
    for i, ln in enumerate(lines):
        der = derived[i] if i < len(derived) else None
        line_payloads.append(
            {
                "id": ln.id,
                "sequence": ln.sequence,
                "due_date": ln.due_date.isoformat() if ln.due_date else None,
                "condition_text": ln.condition_text,
                "percent": decimal_str(ln.percent),
                "amount": decimal_str(ln.amount),
                "derived_amount": decimal_str(der),
            }
        )
    return {
        "order_id": order.id,
        "order_version": order.version,
        "order_status": order.status,
        "currency": order.currency,
        "mode": mode,
        "commercial_total": decimal_str(commercial_total),
        "amount_sum": decimal_str(amount_sum),
        "delta": decimal_str(delta) if coh != COHERENCE_UNVERIFIABLE else None,
        "coherence": coh if lines else None,
        "lines": line_payloads,
    }


def validate_incoming(*, mode: str | None, raw_lines: list[dict]) -> list[dict]:
    if not raw_lines:
        return []
    mode_u = (mode or "").strip().upper()
    if mode_u not in (MODE_PERCENT, MODE_AMOUNT):
        raise OrderValidationError(
            "Modo do cronograma: PERCENT ou AMOUNT",
            code="validation_error",
        )
    parsed: list[dict] = []
    percents: list[Decimal] = []
    amounts: list[Decimal] = []
    for seq, raw in enumerate(raw_lines, start=1):
        due = _parse_due(raw.get("due_date"))
        cond = _condition_text(raw.get("condition_text"))
        if due is None and cond is None:
            raise OrderValidationError(
                f"Parcela {seq}: informe data ou condição comercial",
                code="schedule_when_required",
            )
        pct = parse_decimal(raw.get("percent"))
        amt = parse_decimal(raw.get("amount"))
        if mode_u == MODE_PERCENT:
            if pct is None or amt is not None:
                raise OrderValidationError(
                    "No modo PERCENT use apenas percent (sem amount)",
                    code="validation_error",
                )
            if pct <= 0:
                raise OrderValidationError(
                    "Percentual da parcela deve ser > 0",
                    code="validation_error",
                )
            percents.append(pct)
            parsed.append(
                {
                    "sequence": seq,
                    "due_date": due,
                    "condition_text": cond,
                    "percent": pct,
                    "amount": None,
                }
            )
        else:
            if amt is None or pct is not None:
                raise OrderValidationError(
                    "No modo AMOUNT use apenas amount (sem percent)",
                    code="validation_error",
                )
            amt2 = money2(amt)
            if amt2 <= 0:
                raise OrderValidationError(
                    "Valor da parcela deve ser > 0",
                    code="validation_error",
                )
            amounts.append(amt2)
            parsed.append(
                {
                    "sequence": seq,
                    "due_date": due,
                    "condition_text": cond,
                    "percent": None,
                    "amount": amt2,
                }
            )
    if mode_u == MODE_PERCENT:
        if sum(percents) != Decimal("100"):
            raise OrderValidationError(
                "Percentuais do cronograma devem somar 100%",
                code="validation_error",
            )
    return parsed


def assert_writable(order: Order) -> None:
    if order.status in ("CANCELLED", "CLOSED"):
        raise InvalidTransition(
            f"Não é possível alterar cronograma em pedido {order.status}"
        )


def assert_confirmed_reason(order: Order, reason_code: str | None) -> str:
    if order.status == "CONFIRMED":
        if not reason_code or not str(reason_code).strip():
            raise OrderValidationError(
                "reason_code obrigatório para alterar cronograma de pedido confirmado",
                code="reason_required",
            )
        return str(reason_code).strip()
    return "ORDER_SCHEDULE_DRAFT"


def incoming_amount_sum(parsed: list[dict]) -> Decimal | None:
    if not parsed or any(row.get("amount") is None for row in parsed):
        return None
    return money2(sum((row["amount"] for row in parsed), Decimal("0")))


def assert_incoming_amount_vs_order(order: Order, parsed: list[dict]) -> None:
    summed = incoming_amount_sum(parsed)
    if summed is None:
        return
    totals = compute_totals(list(order.items or []))
    if totals.commercial_total is None:
        return
    if money2(summed) != money2(totals.commercial_total):
        raise OrderValidationError(
            "Soma do cronograma em valor deve igualar o total comercial do pedido",
            code="schedule_amount_mismatch",
        )


def assert_amount_matches_total_if_calculable(db: Session, order: Order) -> None:
    """confirm_order: cronograma AMOUNT persistido vs total atual, se calculável."""
    lines = repo.list_schedule_lines(db, order.id)
    if not lines or infer_mode(lines) != MODE_AMOUNT:
        return
    totals = compute_totals(list(order.items or []))
    if totals.commercial_total is None:
        return
    summed = _amount_sum(lines)
    if summed is None:
        return
    if money2(summed) != money2(totals.commercial_total):
        raise OrderValidationError(
            "Soma do cronograma em valor deve igualar o total comercial do pedido",
            code="schedule_amount_mismatch",
        )


def persist_lines(db: Session, order_id: int, parsed: list[dict]) -> None:
    repo.clear_schedule_lines(db, order_id)
    for row in parsed:
        repo.add_schedule_line(
            db,
            OrderPaymentScheduleLine(
                order_id=order_id,
                sequence=row["sequence"],
                due_date=row["due_date"],
                condition_text=row["condition_text"],
                percent=row["percent"],
                amount=row["amount"],
            ),
        )


def require_order(db: Session, order_id: int) -> Order:
    order = repo.get_order(db, order_id)
    if not order:
        raise OrderNotFound(order_id)
    return order
