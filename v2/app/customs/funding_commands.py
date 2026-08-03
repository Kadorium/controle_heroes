"""Customs Numerário / FundingRequest commands — I5-3A/I5-3B. Caller owns UoW.

Confirm cria Payable via billing.public + FundingPayableLink (I5-3B).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.customs import repository as repo
from app.customs.errors import (
    FundingConflict,
    FundingImmutable,
    FundingNotFound,
    FundingValidationError,
    PayeeNotFound,
    PayeeValidationError,
    ProcessImmutable,
    ProcessNotFound,
)
from app.customs.models import (
    CustomsExpenseLine,
    CustomsFundingRequest,
    CustomsPayee,
    CustomsTaxLine,
    CustomsValueBasis,
    FundingPayableLink,
)
from app.documents import public as documents_public


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _opt_str(value: str | None, *, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        raise FundingValidationError(f"Texto excede {max_len} caracteres", code="text_too_long")
    return s


def _req_str(value: str | None, *, field: str, max_len: int | None = None) -> str:
    s = _opt_str(value, max_len=max_len)
    if not s:
        raise FundingValidationError(f"{field} obrigatório", code="validation_error")
    return s


def _opt_dec(value: str | Decimal | None) -> Decimal | None:
    """Empty/null → None (vazio ≠ 0)."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError) as exc:
        raise FundingValidationError(f"Decimal inválido: {value}", code="invalid_decimal") from exc


def _req_dec(value: str | Decimal | None, *, field: str) -> Decimal:
    d = _opt_dec(value)
    if d is None:
        raise FundingValidationError(f"{field} obrigatório", code="validation_error")
    return d


def _parse_date(value: date | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise FundingValidationError(f"Data inválida: {value}", code="invalid_date") from exc


def _require_process(db: Session, process_id: int):
    p = repo.get_process_for_update(db, process_id)
    if not p:
        raise ProcessNotFound(process_id)
    if p.status == "CANCELLED":
        raise ProcessImmutable("Processo cancelado")
    return p


def _check_ver(fr: CustomsFundingRequest, expected_version: int) -> None:
    if fr.version != expected_version:
        raise FundingConflict()


def _bump(fr: CustomsFundingRequest) -> None:
    fr.version += 1


def _assert_draft(fr: CustomsFundingRequest) -> None:
    if fr.status != "DRAFT":
        raise FundingImmutable("Somente DRAFT permite edição")


def structured_total(fr: CustomsFundingRequest) -> Decimal:
    """Soma apenas amounts não-nulos (None/vazio não entra; 0 entra)."""
    total = Decimal("0")
    for line in list(fr.value_bases or []) + list(fr.tax_lines or []) + list(fr.expense_lines or []):
        if line.amount is not None:
            total += Decimal(str(line.amount))
    return total


def funding_divergence(fr: CustomsFundingRequest) -> Decimal:
    """structured_total − declared_total."""
    return structured_total(fr) - Decimal(str(fr.declared_total))


# —— Payee ——


def create_payee(
    db: Session,
    *,
    name: str,
    tax_id: str | None = None,
    bank_name: str | None = None,
    agency: str | None = None,
    account: str | None = None,
    pix_key: str | None = None,
    notes: str | None = None,
) -> CustomsPayee:
    n = _opt_str(name, max_len=256)
    if not n:
        raise PayeeValidationError("name obrigatório", code="payee_name_required")
    row = CustomsPayee(
        name=n,
        tax_id=_opt_str(tax_id, max_len=64),
        bank_name=_opt_str(bank_name, max_len=256),
        agency=_opt_str(agency, max_len=64),
        account=_opt_str(account, max_len=64),
        pix_key=_opt_str(pix_key, max_len=256),
        notes=_opt_str(notes),
    )
    db.add(row)
    db.flush()
    return row


def update_payee(
    db: Session,
    payee_id: int,
    *,
    name: str | None = None,
    tax_id: str | None = None,
    bank_name: str | None = None,
    agency: str | None = None,
    account: str | None = None,
    pix_key: str | None = None,
    notes: str | None = None,
) -> CustomsPayee:
    row = repo.get_payee(db, payee_id)
    if not row:
        raise PayeeNotFound(payee_id)
    if name is not None:
        n = _opt_str(name, max_len=256)
        if not n:
            raise PayeeValidationError("name obrigatório", code="payee_name_required")
        row.name = n
    if tax_id is not None:
        row.tax_id = _opt_str(tax_id, max_len=64)
    if bank_name is not None:
        row.bank_name = _opt_str(bank_name, max_len=256)
    if agency is not None:
        row.agency = _opt_str(agency, max_len=64)
    if account is not None:
        row.account = _opt_str(account, max_len=64)
    if pix_key is not None:
        row.pix_key = _opt_str(pix_key, max_len=256)
    if notes is not None:
        row.notes = _opt_str(notes)
    db.flush()
    return row


# —— FundingRequest ——


def create_funding_request(
    db: Session,
    process_id: int,
    *,
    payee_id: int,
    currency: str,
    declared_total: str | Decimal,
    reference: str | None = None,
    issue_date: date | str | None = None,
    due_date: date | str | None = None,
    document_id: int | None = None,
    notes: str | None = None,
    idempotency_key: str | None = None,
) -> CustomsFundingRequest:
    _require_process(db, process_id)

    key = _opt_str(idempotency_key, max_len=128)
    if key:
        existing = repo.get_funding_by_idempotency(db, process_id, key)
        if existing:
            return existing

    payee = repo.get_payee(db, payee_id)
    if not payee:
        raise PayeeNotFound(payee_id)

    cur = _req_str(currency, field="currency", max_len=3).upper()
    if len(cur) != 3:
        raise FundingValidationError("currency deve ter 3 letras", code="invalid_currency")

    if document_id is not None:
        doc = documents_public.get_document(db, document_id)
        if not doc:
            raise FundingValidationError("Documento não encontrado", code="document_not_found")

    fr = CustomsFundingRequest(
        process_id=process_id,
        payee_id=payee_id,
        reference=_opt_str(reference, max_len=128),
        issue_date=_parse_date(issue_date),
        due_date=_parse_date(due_date),
        currency=cur,
        declared_total=_req_dec(declared_total, field="declared_total"),
        document_id=document_id,
        version=1,
        idempotency_key=key,
        status="DRAFT",
        notes=_opt_str(notes),
    )
    db.add(fr)
    db.flush()
    return repo.get_funding(db, fr.id) or fr


def update_funding_request(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
    payee_id: int | None = None,
    reference: str | None = None,
    issue_date: date | str | None = None,
    due_date: date | str | None = None,
    currency: str | None = None,
    declared_total: str | Decimal | None = None,
    document_id: int | None = None,
    notes: str | None = None,
    clear_document: bool = False,
) -> CustomsFundingRequest:
    fr = repo.get_funding_for_update(db, funding_id)
    if not fr:
        raise FundingNotFound(funding_id)
    _check_ver(fr, expected_version)
    _assert_draft(fr)
    _require_process(db, fr.process_id)

    if payee_id is not None:
        if not repo.get_payee(db, payee_id):
            raise PayeeNotFound(payee_id)
        fr.payee_id = payee_id
    if reference is not None:
        fr.reference = _opt_str(reference, max_len=128)
    if issue_date is not None:
        fr.issue_date = _parse_date(issue_date)
    if due_date is not None:
        fr.due_date = _parse_date(due_date)
    if currency is not None:
        cur = _req_str(currency, field="currency", max_len=3).upper()
        if len(cur) != 3:
            raise FundingValidationError("currency deve ter 3 letras", code="invalid_currency")
        fr.currency = cur
    if declared_total is not None:
        fr.declared_total = _req_dec(declared_total, field="declared_total")
    if clear_document:
        fr.document_id = None
    elif document_id is not None:
        doc = documents_public.get_document(db, document_id)
        if not doc:
            raise FundingValidationError("Documento não encontrado", code="document_not_found")
        fr.document_id = document_id
    if notes is not None:
        fr.notes = _opt_str(notes)

    _bump(fr)
    db.flush()
    db.expire(fr)
    return repo.get_funding(db, fr.id) or fr


def _replace_lines(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
    lines: list[dict[str, Any]],
    line_cls: type,
    attr: str,
) -> CustomsFundingRequest:
    fr = repo.get_funding_for_update(db, funding_id)
    if not fr:
        raise FundingNotFound(funding_id)
    _check_ver(fr, expected_version)
    _assert_draft(fr)
    _require_process(db, fr.process_id)

    for row in getattr(fr, attr):
        db.delete(row)
    db.flush()

    for idx, raw in enumerate(lines):
        position = int(raw.get("position") if raw.get("position") is not None else idx + 1)
        if position < 1:
            raise FundingValidationError("position deve ser >= 1", code="invalid_position")
        db.add(
            line_cls(
                funding_request_id=fr.id,
                position=position,
                label=_opt_str(raw.get("label"), max_len=256),
                code=_opt_str(raw.get("code"), max_len=64),
                amount=_opt_dec(raw.get("amount")),
                currency=_opt_str(raw.get("currency"), max_len=3),
                notes=_opt_str(raw.get("notes")),
            )
        )
    db.flush()
    _bump(fr)
    db.flush()
    db.expire(fr)
    return repo.get_funding(db, fr.id) or fr


def replace_value_bases(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
    lines: list[dict[str, Any]],
) -> CustomsFundingRequest:
    return _replace_lines(
        db,
        funding_id,
        expected_version=expected_version,
        lines=lines,
        line_cls=CustomsValueBasis,
        attr="value_bases",
    )


def replace_tax_lines(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
    lines: list[dict[str, Any]],
) -> CustomsFundingRequest:
    return _replace_lines(
        db,
        funding_id,
        expected_version=expected_version,
        lines=lines,
        line_cls=CustomsTaxLine,
        attr="tax_lines",
    )


def replace_expense_lines(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
    lines: list[dict[str, Any]],
) -> CustomsFundingRequest:
    return _replace_lines(
        db,
        funding_id,
        expected_version=expected_version,
        lines=lines,
        line_cls=CustomsExpenseLine,
        attr="expense_lines",
    )


def _ensure_customs_payable_link(db: Session, fr: CustomsFundingRequest) -> None:
    """Cria Payable CUSTOMS_FUNDING + FundingPayableLink (idempotente)."""
    payee = repo.get_payee(db, fr.payee_id)
    payee_name = payee.name if payee else f"Payee #{fr.payee_id}"
    due = fr.due_date or fr.issue_date or date.today()
    try:
        payable = billing_public.create_customs_payable_from_funding(
            db,
            funding_request_id=fr.id,
            source_id=fr.id,
            sequence=1,
            due_date=due,
            amount=fr.declared_total,
            currency=fr.currency,
            payee_display_name=payee_name,
            idempotent=True,
        )
    except billing_public.BillingError as exc:
        raise FundingValidationError(getattr(exc, "message", str(exc))) from exc

    existing = (
        db.query(FundingPayableLink)
        .filter(
            FundingPayableLink.funding_request_id == fr.id,
            FundingPayableLink.payable_id == payable.id,
        )
        .first()
    )
    if existing is None:
        db.add(
            FundingPayableLink(
                funding_request_id=fr.id,
                payable_id=payable.id,
                sequence=1,
                amount=payable.amount,
                currency=payable.currency,
            )
        )
        db.flush()


def confirm_funding_request(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
) -> CustomsFundingRequest:
    """DRAFT → CONFIRMED; cria Payable + FundingPayableLink (I5-3B, idempotente)."""
    fr = repo.get_funding_for_update(db, funding_id)
    if not fr:
        raise FundingNotFound(funding_id)
    _check_ver(fr, expected_version)
    if fr.status == "CONFIRMED":
        _ensure_customs_payable_link(db, fr)
        return repo.get_funding(db, fr.id) or fr  # idempotent
    if fr.status != "DRAFT":
        raise FundingImmutable("Somente DRAFT pode ser confirmado")
    _require_process(db, fr.process_id)
    fr.status = "CONFIRMED"
    fr.confirmed_at = _now()
    _bump(fr)
    db.flush()
    _ensure_customs_payable_link(db, fr)
    db.expire(fr)
    return repo.get_funding(db, fr.id) or fr


def cancel_funding_request(
    db: Session,
    funding_id: int,
    *,
    expected_version: int,
) -> CustomsFundingRequest:
    fr = repo.get_funding_for_update(db, funding_id)
    if not fr:
        raise FundingNotFound(funding_id)
    _check_ver(fr, expected_version)
    if fr.status == "CANCELLED":
        return repo.get_funding(db, fr.id) or fr
    if fr.status == "CONFIRMED":
        links = (
            db.query(FundingPayableLink)
            .filter(FundingPayableLink.funding_request_id == fr.id)
            .order_by(FundingPayableLink.sequence.asc())
            .all()
        )
        for link in links:
            try:
                billing_public.cancel_customs_payable(db, link.payable_id)
            except billing_public.BillingError as exc:
                raise FundingImmutable(
                    f"CONFIRMED não pode ser cancelado: payable #{link.payable_id} "
                    f"já liquidado ou não cancelável ({getattr(exc, 'message', exc)})"
                ) from exc
        _require_process(db, fr.process_id)
        fr.status = "CANCELLED"
        fr.cancelled_at = _now()
        _bump(fr)
        db.flush()
        db.expire(fr)
        return repo.get_funding(db, fr.id) or fr
    if fr.status != "DRAFT":
        raise FundingImmutable("Somente DRAFT pode ser cancelado")
    _require_process(db, fr.process_id)
    fr.status = "CANCELLED"
    fr.cancelled_at = _now()
    _bump(fr)
    db.flush()
    db.expire(fr)
    return repo.get_funding(db, fr.id) or fr
