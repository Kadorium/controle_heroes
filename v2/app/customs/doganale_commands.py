"""Customs Doganale commands — I5-2. Caller owns UoW."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.customs import repository as repo
from app.customs.errors import (
    DoganaleConflict,
    DoganaleImmutable,
    DoganaleNotFound,
    DoganaleValidationError,
    DoganaleVersionNotFound,
    ProcessImmutable,
    ProcessNotFound,
)
from app.customs.models import (
    CustomsDivergence,
    CustomsDoganale,
    CustomsDoganaleLine,
    CustomsDoganaleVersion,
    CustomsProvenance,
)
from app.documents import public as documents_public


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _opt_dec(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError) as exc:
        raise DoganaleValidationError(f"Decimal inválido: {value}", code="invalid_decimal") from exc


def _opt_str(value: str | None, *, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        raise DoganaleValidationError(f"Texto excede {max_len} caracteres", code="text_too_long")
    return s


def _require_process(db: Session, process_id: int):
    p = repo.get_process_for_update(db, process_id)
    if not p:
        raise ProcessNotFound(process_id)
    if p.status == "CANCELLED":
        raise ProcessImmutable("Processo cancelado")
    return p


def _check_ver(ver: CustomsDoganaleVersion, expected_version: int) -> None:
    if ver.version != expected_version:
        raise DoganaleConflict()


def _bump(ver: CustomsDoganaleVersion) -> None:
    ver.version += 1


def _assert_draft(ver: CustomsDoganaleVersion) -> None:
    if ver.status != "DRAFT":
        raise DoganaleImmutable("Somente DRAFT permite edição de linhas")


def ensure_doganale(db: Session, process_id: int) -> CustomsDoganale:
    _require_process(db, process_id)
    existing = repo.get_doganale_by_process(db, process_id)
    if existing:
        return existing
    dog = CustomsDoganale(process_id=process_id)
    db.add(dog)
    db.flush()
    return dog


def create_doganale_version(
    db: Session,
    process_id: int,
    *,
    notes: str | None = None,
    document_id: int | None = None,
    copy_from_current: bool = False,
    idempotency_key: str | None = None,
) -> CustomsDoganaleVersion:
    _require_process(db, process_id)
    dog = ensure_doganale(db, process_id)

    key = _opt_str(idempotency_key, max_len=128)
    if key:
        existing = repo.get_version_by_idempotency(db, dog.id, key)
        if existing:
            return existing

    if document_id is not None:
        doc = documents_public.get_document(db, document_id)
        if not doc:
            raise DoganaleValidationError("Documento fonte não encontrado", code="document_not_found")

    next_num = repo.next_version_number(db, dog.id)
    ver = CustomsDoganaleVersion(
        doganale_id=dog.id,
        version_number=next_num,
        status="DRAFT",
        is_current=False,
        version=1,
        document_id=document_id,
        idempotency_key=key,
        notes=_opt_str(notes),
    )
    db.add(ver)
    db.flush()

    if copy_from_current:
        current = repo.get_current_version(db, dog.id)
        if current:
            for line in sorted(current.lines, key=lambda x: x.position):
                db.add(
                    CustomsDoganaleLine(
                        version_id=ver.id,
                        position=line.position,
                        ncm=line.ncm,
                        description=line.description,
                        quantity=line.quantity,
                        unit=line.unit,
                        currency=line.currency,
                        unit_price=line.unit_price,
                        line_amount=line.line_amount,
                        manufacturer=line.manufacturer,
                        origin_country=line.origin_country,
                        acquisition_country=line.acquisition_country,
                        net_weight_kg=line.net_weight_kg,
                        gross_weight_kg=line.gross_weight_kg,
                        pallet_count=line.pallet_count,
                        invoice_id=line.invoice_id,
                        invoice_item_id=line.invoice_item_id,
                        product_id=line.product_id,
                        document_id=line.document_id,
                        notes=line.notes,
                    )
                )
            db.flush()

    return repo.get_version(db, ver.id) or ver


def _validate_line_links(db: Session, process_id: int, line: dict[str, Any]) -> None:
    invoice_id = line.get("invoice_id")
    invoice_item_id = line.get("invoice_item_id")
    product_id = line.get("product_id")
    document_id = line.get("document_id")

    if invoice_id is not None:
        link = repo.find_invoice_link_on_process(db, process_id, int(invoice_id))
        if not link:
            raise DoganaleValidationError(
                "Invoice não vinculada ao processo", code="invoice_not_linked"
            )
        try:
            billing_public.get_invoice(db, int(invoice_id))
        except billing_public.BillingError as exc:
            raise DoganaleValidationError(str(exc), code="invoice_not_found") from exc

    if invoice_item_id is not None:
        try:
            inv = billing_public.get_invoice(db, int(invoice_id)) if invoice_id else None
        except billing_public.BillingError as exc:
            raise DoganaleValidationError(str(exc), code="invoice_not_found") from exc
        if inv is None:
            # resolve item via process invoices
            found = False
            process = repo.get_process(db, process_id)
            assert process
            for link in process.invoices:
                inv2 = billing_public.get_invoice(db, link.invoice_id)
                if any(it.id == int(invoice_item_id) for it in inv2.items):
                    found = True
                    break
            if not found:
                raise DoganaleValidationError(
                    "InvoiceItem não pertence às invoices do processo",
                    code="invoice_item_not_in_process",
                )
        elif not any(it.id == int(invoice_item_id) for it in inv.items):
            raise DoganaleValidationError(
                "InvoiceItem não pertence à invoice informada",
                code="invoice_item_mismatch",
            )

    if product_id is not None:
        try:
            catalog_public.get_product(db, int(product_id))
        except catalog_public.CatalogError as exc:
            raise DoganaleValidationError(str(exc), code="product_not_found") from exc

    if document_id is not None:
        doc = documents_public.get_document(db, int(document_id))
        if not doc:
            raise DoganaleValidationError("Documento da linha não encontrado", code="document_not_found")


def replace_doganale_lines(
    db: Session,
    version_id: int,
    *,
    expected_version: int,
    lines: list[dict[str, Any]],
) -> CustomsDoganaleVersion:
    ver = repo.get_version_for_update(db, version_id)
    if not ver:
        raise DoganaleVersionNotFound(version_id)
    _check_ver(ver, expected_version)
    _assert_draft(ver)

    dog = repo.get_doganale(db, ver.doganale_id)
    if not dog:
        raise DoganaleNotFound(ver.doganale_id)
    _require_process(db, dog.process_id)

    for row in ver.lines:
        db.delete(row)
    db.flush()

    for idx, raw in enumerate(lines):
        position = int(raw.get("position") if raw.get("position") is not None else idx + 1)
        if position < 1:
            raise DoganaleValidationError("position deve ser >= 1", code="invalid_position")
        _validate_line_links(db, dog.process_id, raw)
        qty = _opt_dec(raw.get("quantity"))
        unit_price = _opt_dec(raw.get("unit_price"))
        line_amount = _opt_dec(raw.get("line_amount"))
        if line_amount is None and qty is not None and unit_price is not None:
            line_amount = (qty * unit_price).quantize(Decimal("0.0001"))
        db.add(
            CustomsDoganaleLine(
                version_id=ver.id,
                position=position,
                ncm=_opt_str(raw.get("ncm"), max_len=16),
                description=_opt_str(raw.get("description")),
                quantity=qty,
                unit=_opt_str(raw.get("unit"), max_len=16),
                currency=_opt_str(raw.get("currency"), max_len=3),
                unit_price=unit_price,
                line_amount=line_amount,
                manufacturer=_opt_str(raw.get("manufacturer"), max_len=256),
                origin_country=_opt_str(raw.get("origin_country"), max_len=2),
                acquisition_country=_opt_str(raw.get("acquisition_country"), max_len=2),
                net_weight_kg=_opt_dec(raw.get("net_weight_kg")),
                gross_weight_kg=_opt_dec(raw.get("gross_weight_kg")),
                pallet_count=_opt_dec(raw.get("pallet_count")),
                invoice_id=raw.get("invoice_id"),
                invoice_item_id=raw.get("invoice_item_id"),
                product_id=raw.get("product_id"),
                document_id=raw.get("document_id"),
                notes=_opt_str(raw.get("notes")),
            )
        )
    db.flush()
    _bump(ver)
    db.expire(ver, ["lines"])
    return repo.get_version(db, ver.id) or ver


def activate_doganale_version(
    db: Session,
    version_id: int,
    *,
    expected_version: int,
) -> CustomsDoganaleVersion:
    ver = repo.get_version_for_update(db, version_id)
    if not ver:
        raise DoganaleVersionNotFound(version_id)
    _check_ver(ver, expected_version)
    if ver.status == "ACTIVE" and ver.is_current:
        return ver  # idempotent
    if ver.status != "DRAFT":
        raise DoganaleImmutable("Somente DRAFT pode ser ativada")
    db.expire(ver, ["lines"])
    if not list(ver.lines):
        raise DoganaleValidationError("Versão sem linhas não pode ser ativada", code="lines_required")

    dog = repo.get_doganale_for_update(db, ver.doganale_id)
    if not dog:
        raise DoganaleNotFound(ver.doganale_id)
    _require_process(db, dog.process_id)

    now = _now()
    current = repo.get_current_version_for_update(db, dog.id)
    if current and current.id != ver.id:
        current.is_current = False
        if current.status == "ACTIVE":
            current.status = "SUPERSEDED"
            current.superseded_at = now
            current.version += 1

    ver.status = "ACTIVE"
    ver.is_current = True
    ver.activated_at = now
    _bump(ver)
    db.flush()
    return repo.get_version(db, ver.id) or ver


def supersede_doganale_version(
    db: Session,
    version_id: int,
    *,
    expected_version: int,
    notes: str | None = None,
    document_id: int | None = None,
    idempotency_key: str | None = None,
) -> CustomsDoganaleVersion:
    """Cria DRAFT de retificação a partir da versão current (tipicamente ACTIVE) e deixa a current marcada para supersede na ativação.

    Fluxo explícito: se version_id é current ACTIVE, cria nova DRAFT copiando linhas.
    A supersede definitiva ocorre em activate da nova versão.
    """
    ver = repo.get_version_for_update(db, version_id)
    if not ver:
        raise DoganaleVersionNotFound(version_id)
    _check_ver(ver, expected_version)
    if not ver.is_current or ver.status != "ACTIVE":
        raise DoganaleValidationError(
            "Supersede exige versão current ACTIVE", code="supersede_requires_current_active"
        )

    dog = repo.get_doganale(db, ver.doganale_id)
    if not dog:
        raise DoganaleNotFound(ver.doganale_id)

    new_ver = create_doganale_version(
        db,
        dog.process_id,
        notes=notes or f"Retificação de v{ver.version_number}",
        document_id=document_id if document_id is not None else ver.document_id,
        copy_from_current=True,
        idempotency_key=idempotency_key,
    )
    return new_ver


def cancel_doganale_version(
    db: Session,
    version_id: int,
    *,
    expected_version: int,
) -> CustomsDoganaleVersion:
    ver = repo.get_version_for_update(db, version_id)
    if not ver:
        raise DoganaleVersionNotFound(version_id)
    _check_ver(ver, expected_version)
    if ver.status != "DRAFT":
        raise DoganaleImmutable("Somente DRAFT pode ser cancelada")
    if ver.is_current:
        raise DoganaleImmutable("Não cancela versão current")
    ver.status = "CANCELLED"
    ver.cancelled_at = _now()
    _bump(ver)
    db.flush()
    return ver


def set_doganale_document(
    db: Session,
    version_id: int,
    *,
    expected_version: int,
    document_id: int | None,
) -> CustomsDoganaleVersion:
    ver = repo.get_version_for_update(db, version_id)
    if not ver:
        raise DoganaleVersionNotFound(version_id)
    _check_ver(ver, expected_version)
    _assert_draft(ver)
    if document_id is not None:
        doc = documents_public.get_document(db, document_id)
        if not doc:
            raise DoganaleValidationError("Documento fonte não encontrado", code="document_not_found")
    ver.document_id = document_id
    _bump(ver)
    db.flush()
    return ver


def register_divergence(
    db: Session,
    process_id: int,
    *,
    kind: str,
    message: str,
    severity: str = "WARN",
    doganale_version_id: int | None = None,
    doganale_line_id: int | None = None,
    field_name: str | None = None,
    expected_value: str | None = None,
    actual_value: str | None = None,
) -> CustomsDivergence:
    _require_process(db, process_id)
    sev = (severity or "WARN").strip().upper()
    if sev not in ("INFO", "WARN", "ERROR"):
        raise DoganaleValidationError("severity inválida", code="invalid_severity")
    kind_s = _opt_str(kind, max_len=64)
    msg = _opt_str(message)
    if not kind_s or not msg:
        raise DoganaleValidationError("kind e message obrigatórios", code="divergence_required")
    if doganale_version_id is not None and not repo.get_version(db, doganale_version_id):
        raise DoganaleVersionNotFound(doganale_version_id)
    row = CustomsDivergence(
        process_id=process_id,
        doganale_version_id=doganale_version_id,
        doganale_line_id=doganale_line_id,
        kind=kind_s,
        severity=sev,
        field_name=_opt_str(field_name, max_len=64),
        expected_value=_opt_str(expected_value),
        actual_value=_opt_str(actual_value),
        message=msg,
        status="OPEN",
    )
    db.add(row)
    db.flush()
    return row


def attach_provenance(
    db: Session,
    process_id: int,
    *,
    entity_type: str,
    entity_id: str,
    source_kind: str,
    document_id: int | None = None,
    adapter_key: str | None = None,
    notes: str | None = None,
) -> CustomsProvenance:
    _require_process(db, process_id)
    et = _opt_str(entity_type, max_len=64)
    eid = _opt_str(entity_id, max_len=64)
    sk = _opt_str(source_kind, max_len=64)
    if not et or not eid or not sk:
        raise DoganaleValidationError("provenance incompleta", code="provenance_required")
    if document_id is not None:
        doc = documents_public.get_document(db, document_id)
        if not doc:
            raise DoganaleValidationError("Documento não encontrado", code="document_not_found")
    existing = repo.get_provenance(db, et, eid, sk)
    if existing:
        existing.document_id = document_id
        existing.adapter_key = _opt_str(adapter_key, max_len=128)
        existing.notes = _opt_str(notes)
        db.flush()
        return existing
    row = CustomsProvenance(
        process_id=process_id,
        entity_type=et,
        entity_id=eid,
        source_kind=sk,
        document_id=document_id,
        adapter_key=_opt_str(adapter_key, max_len=128),
        notes=_opt_str(notes),
    )
    db.add(row)
    db.flush()
    return row
