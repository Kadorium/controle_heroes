"""HTTP Doganale — nested under /api/import-processes (I5-2)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.customs import public as customs_public
from app.customs.errors import CustomsError
from app.customs.models import CustomsDivergence, CustomsDoganaleVersion, CustomsProvenance
from app.customs.queries import dec_str
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork

router = APIRouter(tags=["customs-doganale"])


def _map_error(exc: CustomsError) -> AppError:
    code = getattr(exc, "code", "customs_error")
    status = 400
    if code in ("process_not_found", "doganale_not_found", "doganale_version_not_found"):
        status = 404
    elif code in (
        "conflict",
        "doganale_immutable",
        "process_immutable",
        "process_not_draft",
    ):
        status = 409
    elif code in (
        "validation_error",
        "invalid_decimal",
        "document_not_found",
        "invoice_not_linked",
        "invoice_not_found",
        "invoice_item_not_in_process",
        "invoice_item_mismatch",
        "product_not_found",
        "lines_required",
        "supersede_requires_current_active",
        "invalid_severity",
        "divergence_required",
        "provenance_required",
        "invalid_position",
        "text_too_long",
    ):
        status = 422
    return AppError(exc.message, code=code, status_code=status)


class DoganaleLineIn(BaseModel):
    position: int | None = None
    ncm: str | None = None
    description: str | None = None
    quantity: str | None = None
    unit: str | None = None
    currency: str | None = None
    unit_price: str | None = None
    line_amount: str | None = None
    manufacturer: str | None = None
    origin_country: str | None = None
    acquisition_country: str | None = None
    net_weight_kg: str | None = None
    gross_weight_kg: str | None = None
    pallet_count: str | None = None
    invoice_id: int | None = None
    invoice_item_id: int | None = None
    product_id: int | None = None
    document_id: int | None = None
    notes: str | None = None


class DoganaleLineOut(BaseModel):
    id: int
    position: int
    ncm: str | None
    description: str | None
    quantity: str | None
    unit: str | None
    currency: str | None
    unit_price: str | None
    line_amount: str | None
    manufacturer: str | None
    origin_country: str | None
    acquisition_country: str | None
    net_weight_kg: str | None
    gross_weight_kg: str | None
    pallet_count: str | None
    invoice_id: int | None
    invoice_item_id: int | None
    product_id: int | None
    document_id: int | None
    notes: str | None


class DoganaleVersionOut(BaseModel):
    id: int
    doganale_id: int
    process_id: int
    version_number: int
    status: str
    is_current: bool
    version: int
    document_id: int | None
    notes: str | None
    activated_at: datetime | None
    superseded_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime | None
    lines: list[DoganaleLineOut]


class DoganaleSummaryOut(BaseModel):
    id: int
    process_id: int
    current_version_id: int | None
    versions: list[DoganaleVersionOut]


class CreateVersionBody(BaseModel):
    notes: str | None = None
    document_id: int | None = None
    copy_from_current: bool = False
    idempotency_key: str | None = None


class ReplaceLinesBody(BaseModel):
    expected_version: int
    lines: list[DoganaleLineIn]


class VersionLockBody(BaseModel):
    expected_version: int


class SupersedeBody(BaseModel):
    expected_version: int
    notes: str | None = None
    document_id: int | None = None
    idempotency_key: str | None = None


class SetDocumentBody(BaseModel):
    expected_version: int
    document_id: int | None = None


class DivergenceIn(BaseModel):
    kind: str
    message: str
    severity: str = "WARN"
    doganale_version_id: int | None = None
    doganale_line_id: int | None = None
    field_name: str | None = None
    expected_value: str | None = None
    actual_value: str | None = None


class DivergenceOut(BaseModel):
    id: int
    process_id: int
    doganale_version_id: int | None
    doganale_line_id: int | None
    kind: str
    severity: str
    field_name: str | None
    expected_value: str | None
    actual_value: str | None
    message: str
    status: str
    created_at: datetime | None


class ProvenanceIn(BaseModel):
    entity_type: str
    entity_id: str
    source_kind: str
    document_id: int | None = None
    adapter_key: str | None = None
    notes: str | None = None


class ProvenanceOut(BaseModel):
    id: int
    process_id: int
    entity_type: str
    entity_id: str
    source_kind: str
    document_id: int | None
    adapter_key: str | None
    notes: str | None
    created_at: datetime | None


def _line_out(line) -> DoganaleLineOut:
    return DoganaleLineOut(
        id=line.id,
        position=line.position,
        ncm=line.ncm,
        description=line.description,
        quantity=dec_str(line.quantity),
        unit=line.unit,
        currency=line.currency,
        unit_price=dec_str(line.unit_price),
        line_amount=dec_str(line.line_amount),
        manufacturer=line.manufacturer,
        origin_country=line.origin_country,
        acquisition_country=line.acquisition_country,
        net_weight_kg=dec_str(line.net_weight_kg),
        gross_weight_kg=dec_str(line.gross_weight_kg),
        pallet_count=dec_str(line.pallet_count),
        invoice_id=line.invoice_id,
        invoice_item_id=line.invoice_item_id,
        product_id=line.product_id,
        document_id=line.document_id,
        notes=line.notes,
    )


def _version_out(ver: CustomsDoganaleVersion, process_id: int) -> DoganaleVersionOut:
    return DoganaleVersionOut(
        id=ver.id,
        doganale_id=ver.doganale_id,
        process_id=process_id,
        version_number=ver.version_number,
        status=ver.status,
        is_current=ver.is_current,
        version=ver.version,
        document_id=ver.document_id,
        notes=ver.notes,
        activated_at=ver.activated_at,
        superseded_at=ver.superseded_at,
        cancelled_at=ver.cancelled_at,
        created_at=ver.created_at,
        lines=[_line_out(x) for x in sorted(ver.lines or [], key=lambda l: l.position)],
    )


def _divergence_out(row: CustomsDivergence) -> DivergenceOut:
    return DivergenceOut(
        id=row.id,
        process_id=row.process_id,
        doganale_version_id=row.doganale_version_id,
        doganale_line_id=row.doganale_line_id,
        kind=row.kind,
        severity=row.severity,
        field_name=row.field_name,
        expected_value=row.expected_value,
        actual_value=row.actual_value,
        message=row.message,
        status=row.status,
        created_at=row.created_at,
    )


def _provenance_out(row: CustomsProvenance) -> ProvenanceOut:
    return ProvenanceOut(
        id=row.id,
        process_id=row.process_id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        source_kind=row.source_kind,
        document_id=row.document_id,
        adapter_key=row.adapter_key,
        notes=row.notes,
        created_at=row.created_at,
    )


@router.get(
    "/import-processes/{process_id}/doganale",
    response_model=DoganaleSummaryOut | None,
)
def api_get_doganale(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        dog = customs_public.get_doganale_for_process(db, process_id)
        if not dog:
            return None
        versions = customs_public.list_doganale_versions(db, process_id)
        current = next((v for v in versions if v.is_current), None)
        return DoganaleSummaryOut(
            id=dog.id,
            process_id=process_id,
            current_version_id=current.id if current else None,
            versions=[_version_out(v, process_id) for v in versions],
        )
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/doganale/versions",
    response_model=DoganaleVersionOut,
    status_code=201,
)
def api_create_version(
    process_id: int,
    body: CreateVersionBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            ver = customs_public.create_doganale_version(
                uow.session,
                process_id,
                notes=body.notes,
                document_id=body.document_id,
                copy_from_current=body.copy_from_current,
                idempotency_key=body.idempotency_key,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="doganale_version",
                entity_id=str(ver.id),
                action="doganale.version.create",
            )
            uow.commit()
            full = customs_public.list_doganale_versions(uow.session, process_id)
            ver2 = next(v for v in full if v.id == ver.id)
            return _version_out(ver2, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.put(
    "/import-processes/{process_id}/doganale/versions/{version_id}/lines",
    response_model=DoganaleVersionOut,
)
def api_replace_lines(
    process_id: int,
    version_id: int,
    body: ReplaceLinesBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            ver = customs_public.replace_doganale_lines(
                uow.session,
                version_id,
                expected_version=body.expected_version,
                lines=[line.model_dump() for line in body.lines],
            )
            dog = customs_public.get_doganale_for_process(uow.session, process_id)
            if not dog or ver.doganale_id != dog.id:
                raise AppError("Versão não pertence ao processo", code="version_mismatch", status_code=404)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="doganale_version",
                entity_id=str(version_id),
                action="doganale.lines.replace",
            )
            uow.commit()
            return _version_out(ver, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/doganale/versions/{version_id}/activate",
    response_model=DoganaleVersionOut,
)
def api_activate(
    process_id: int,
    version_id: int,
    body: VersionLockBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            ver = customs_public.activate_doganale_version(
                uow.session, version_id, expected_version=body.expected_version
            )
            dog = customs_public.get_doganale_for_process(uow.session, process_id)
            if not dog or ver.doganale_id != dog.id:
                raise AppError("Versão não pertence ao processo", code="version_mismatch", status_code=404)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="doganale_version",
                entity_id=str(version_id),
                action="doganale.version.activate",
            )
            uow.commit()
            return _version_out(ver, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/doganale/versions/{version_id}/supersede",
    response_model=DoganaleVersionOut,
)
def api_supersede(
    process_id: int,
    version_id: int,
    body: SupersedeBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            ver = customs_public.supersede_doganale_version(
                uow.session,
                version_id,
                expected_version=body.expected_version,
                notes=body.notes,
                document_id=body.document_id,
                idempotency_key=body.idempotency_key,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="doganale_version",
                entity_id=str(ver.id),
                action="doganale.version.supersede_draft",
                details=f"from_version_id={version_id}",
            )
            uow.commit()
            return _version_out(ver, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/doganale/versions/{version_id}/cancel",
    response_model=DoganaleVersionOut,
)
def api_cancel_version(
    process_id: int,
    version_id: int,
    body: VersionLockBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            ver = customs_public.cancel_doganale_version(
                uow.session, version_id, expected_version=body.expected_version
            )
            dog = customs_public.get_doganale_for_process(uow.session, process_id)
            if not dog or ver.doganale_id != dog.id:
                raise AppError("Versão não pertence ao processo", code="version_mismatch", status_code=404)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="doganale_version",
                entity_id=str(version_id),
                action="doganale.version.cancel",
            )
            uow.commit()
            return _version_out(ver, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/import-processes/{process_id}/doganale/versions/{version_id}/document",
    response_model=DoganaleVersionOut,
)
def api_set_document(
    process_id: int,
    version_id: int,
    body: SetDocumentBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            ver = customs_public.set_doganale_document(
                uow.session,
                version_id,
                expected_version=body.expected_version,
                document_id=body.document_id,
            )
            dog = customs_public.get_doganale_for_process(uow.session, process_id)
            if not dog or ver.doganale_id != dog.id:
                raise AppError("Versão não pertence ao processo", code="version_mismatch", status_code=404)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="doganale_version",
                entity_id=str(version_id),
                action="doganale.version.set_document",
            )
            uow.commit()
            return _version_out(ver, process_id)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/divergences",
    response_model=list[DivergenceOut],
)
def api_list_divergences(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return [_divergence_out(r) for r in customs_public.list_process_divergences(db, process_id)]
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/divergences",
    response_model=DivergenceOut,
    status_code=201,
)
def api_register_divergence(
    process_id: int,
    body: DivergenceIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            row = customs_public.register_divergence(
                uow.session,
                process_id,
                kind=body.kind,
                message=body.message,
                severity=body.severity,
                doganale_version_id=body.doganale_version_id,
                doganale_line_id=body.doganale_line_id,
                field_name=body.field_name,
                expected_value=body.expected_value,
                actual_value=body.actual_value,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_divergence",
                entity_id=str(row.id),
                action="divergence.register",
            )
            uow.commit()
            return _divergence_out(row)
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/import-processes/{process_id}/provenances",
    response_model=list[ProvenanceOut],
)
def api_list_provenances(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:read")
    try:
        return [_provenance_out(r) for r in customs_public.list_process_provenances(db, process_id)]
    except CustomsError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/import-processes/{process_id}/provenances",
    response_model=ProvenanceOut,
    status_code=201,
)
def api_attach_provenance(
    process_id: int,
    body: ProvenanceIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "customs:write")
    try:
        with UnitOfWork(db) as uow:
            row = customs_public.attach_provenance(
                uow.session,
                process_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
                source_kind=body.source_kind,
                document_id=body.document_id,
                adapter_key=body.adapter_key,
                notes=body.notes,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="customs_provenance",
                entity_id=str(row.id),
                action="provenance.attach",
            )
            uow.commit()
            return _provenance_out(row)
    except CustomsError as exc:
        raise _map_error(exc) from exc
