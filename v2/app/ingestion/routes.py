"""HTTP Ingestion — /api/ingestion/* (J3-I0/I1/I3)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.documents import public as documents_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
from app.ingestion import commands as ingestion_commands
from app.ingestion import commit_commands
from app.ingestion import commit_failure
from app.ingestion import commit_queries
from app.ingestion import fattura_commit_commands
from app.ingestion import queries as ingestion_queries
from app.ingestion import staging_commands
from app.ingestion import staging_queries
from app.ingestion import storage as quarantine_storage
from app.ingestion.commit_commands import (
    CommitAttemptNotFound,
    CommitBlockedByIssues,
    CommitConflictFingerprint,
    CommitDocumentNotReady,
    CommitOrderCodeExists,
    CommitSupplierLinkRequired,
)
from app.ingestion.commit_failure import CommitOperationFailed
from app.ingestion.fattura_commit_commands import (
    FatturaCommitBlockedByIssues,
    FatturaCommitConflictFingerprint,
    FatturaOrderDraftMustConfirm,
    FatturaC2MissingReason,
)
from app.ingestion import dossier_commands
from app.ingestion import packing_commit_commands
from app.ingestion.dossier_commands import (
    DossierConflictFingerprint,
    DossierCommitBlockedByIssues,
)
from app.ingestion import numerario_commit_commands
from app.ingestion import doganale_commit_commands
from app.ingestion import print_commit_commands
from app.ingestion.numerario_commit_commands import (
    NumerarioCommitConflictFingerprint,
    NumerarioCommitBlockedByIssues,
)
from app.ingestion import xlsx_commit_commands
from app.ingestion.xlsx_commit_commands import (
    XlsxCommitConflictFingerprint,
    XlsxCommitBlockedByIssues,
)
from app.ingestion import metrics_commands as ingestion_metrics_commands
from app.ingestion.errors import IngestionError, DocumentDeleteBlocked
from app.ingestion.limits import limits_from_mapping
from app.ingestion.models import IngestionOccurrence
from app.ingestion.staging_commands import effective_field_value
from app.ingestion.schemas import (
    BatchCreate,
    BatchOut,
    CommitAttemptOut,
    CommitIn,
    CommitOperationOut,
    DocumentOut,
    DocumentReviewIn,
    DocumentSeedIn,
    DocumentSetCreateIn,
    DocumentSetMemberIn,
    DocumentSetMemberOut,
    DocumentSetOut,
    DocumentSummaryOut,
    FatturaCommitIn,
    FatturaLineCandidateOut,
    FatturaLineMatchOut,
    FatturaOrderCandidateOut,
    FatturaPreviewOperationOut,
    FatturaPreviewOut,
    FatturaPolicyMatchOut,
    FieldCorrectIn,
    FieldOut,
    FieldRestoreIn,
    IssueCreateIn,
    IssueOut,
    IssueResolveIn,
    OccurrenceOut,
    OrderCodeOverrideIn,
    PreviewCommitOut,
    PreviewOperationOut,
    PurgeRequest,
    PurgeResponse,
    ReviewChangeOut,
    RowCorrectIn,
    RowAddIn,
    RowOut,
    RunAdapterIn,
    RunAdapterOut,
    AdapterInfoOut,
    ClassifyOut,
    ClassifySuggestionOut,
    SectionOut,
    SectionReviewIn,
    UploadResponse,
    # I5
    DossierPreviewOut,
    DossierPreviewItemOut,
    ReconciliationIssueOut,
    DossierCommitIn,
    DoganaleCommitIn,
    DoganalePreviewOut,
    DoganalePreviewOpOut,
    DoganaleProcessTargetOut,
    DoganaleInvoiceCandidateOut,
    DoganaleShipmentTargetOut,
    DoganaleLinePreviewOut,
    PrintCommitIn,
    PrintPreviewOut,
    PrintPreviewOpOut,
    PrintProcessTargetOut,
    PackingCommitIn,
    PackingPreviewOut,
    PackingPreviewOperationOut,
    PackingOrderCandidateOut,
    PackingShipmentTargetOut,
    PackingLineMatchOut,
    PackingLineCandidateOut,
    PackingCartonOut,
    # I6
    NumerarioCommitIn,
    NumerarioPreviewOut,
    NumerarioPreviewOpOut,
    NumerarioProcessCandidateOut,
    NumerarioOpResultOut,
    NumerarioCommitResultOut,
    # I7
    XlsxRunAdapterOut,
    XlsxPreviewOut,
    XlsxPreviewOperationOut,
    XlsxCommitIn,
    XlsxCommitResultOut,
    XlsxCommitOpOut,
    MetricEventOut,
    AdapterMetricsSummaryOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _map_error(exc: IngestionError) -> AppError:
    code = exc.code
    status = 400
    if code in (
        "batch_not_found",
        "occurrence_not_found",
        "document_not_found",
        "field_not_found",
        "row_not_found",
        "section_not_found",
        "issue_not_found",
        "document_set_not_found",
        "commit_attempt_not_found",
        "unknown_adapter",
        "blob_unavailable",
    ):
        status = 404
    elif code in (
        "idempotency_conflict",
        "batch_closed",
        "invalid_transition",
        "version_conflict",
        "document_locked",
        "document_already_exists",
        "occurrence_not_stored",
        "commit_conflict_fingerprint",
        "commit_supplier_link_required",
        "commit_order_code_exists",
        "fattura_invoice_conflict",
        "reextract_blocked",
        "document_delete_blocked",
        "document_reject_blocked",
        "packing_shipment_incompatible",
    ):
        status = 409
    elif code in ("request_limit_exceeded", "no_files", "hash_race_retry"):
        status = 422 if code != "hash_race_retry" else 409
    elif code in (
        "commit_blocked_by_issues",
        "commit_document_not_ready",
        "order_draft_must_confirm",
        "order_pending_confirm",
        "c2_missing_reason",
        "c2_missing_confirm",
        "invalid_policy",
        "issue_justification_required",
        "order_id_required",
        "fattura_sku_not_on_order",
        "fattura_qty_exceeds_remaining",
        "fattura_no_billable_lines",
        "fattura_line_ambiguous",
        "fattura_line_choice_invalid",
        "packing_order_id_required",
        "packing_shipment_id_required",
        "packing_line_ambiguous",
        "packing_line_choice_invalid",
        "packing_commitment_unbound",
        "packing_no_carton_rows",
        "packing_qty_exceeds_residual",
        "packing_commit_blocked",
        "packing_wrong_doc_type",
        "doganale_commit_blocked",
        "doganale_wrong_doc_type",
        "doganale_process_id_required",
        "print_commit_blocked",
        "print_wrong_doc_type",
        "print_process_id_required",
        "overship",
        "validation_error",
    ):
        status = 422
    details = None
    if code == "commit_order_code_exists":
        details = {
            "order_id": getattr(exc, "order_id", None),
            "order_code": getattr(exc, "order_code", None),
        }
    return AppError(exc.message, code=code, status_code=status, details=details)


def _occ_out(occ: IngestionOccurrence) -> OccurrenceOut:
    blob_status = occ.blob.physical_status if occ.blob is not None else None
    return OccurrenceOut(
        id=occ.id,
        batch_id=occ.batch_id,
        blob_id=occ.blob_id,
        status=occ.status,
        original_filename=occ.original_filename,
        declared_mime=occ.declared_mime,
        detected_mime=occ.detected_mime,
        size_bytes=occ.size_bytes,
        sha256=occ.sha256,
        client_upload_key=occ.client_upload_key,
        rejection_reason=occ.rejection_reason,
        physical_reuse=occ.physical_reuse,
        rehydrated=occ.rehydrated,
        retain_until=occ.retain_until,
        bytes_purged_at=occ.bytes_purged_at,
        blob_physical_status=blob_status,
        created_at=occ.created_at,
        updated_at=occ.updated_at,
    )


@router.post("/batches", response_model=BatchOut)
def create_batch(
    body: BatchCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            batch = ingestion_commands.create_batch(
                uow.session, actor_id=str(user.id), notes=body.notes
            )
            uow.commit()
            uow.session.refresh(batch)
            return BatchOut(
                id=batch.id,
                status=batch.status,
                created_by_actor_id=batch.created_by_actor_id,
                notes=batch.notes,
                created_at=batch.created_at,
                updated_at=batch.updated_at,
                occurrences=[],
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        batch = ingestion_queries.get_batch_with_occurrences(db, batch_id)
        return BatchOut(
            id=batch.id,
            status=batch.status,
            created_by_actor_id=batch.created_by_actor_id,
            notes=batch.notes,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            occurrences=[_occ_out(o) for o in batch.occurrences],
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/batches/{batch_id}/files", response_model=UploadResponse)
async def upload_files(
    batch_id: int,
    files: list[UploadFile] = File(...),
    client_upload_keys: list[str] | None = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    settings = get_settings()
    limits = limits_from_mapping(settings)
    keys = client_upload_keys or []
    pending: list[Path] = []
    try:
        inputs: list[ingestion_commands.FileUploadInput] = []
        for idx, f in enumerate(files):
            key = keys[idx] if idx < len(keys) else None
            inputs.append(
                ingestion_commands.FileUploadInput(
                    filename=f.filename,
                    content_type=f.content_type,
                    stream=f.file,
                    client_upload_key=key,
                )
            )
        with UnitOfWork(db) as uow:
            try:
                result = ingestion_commands.upload_files(
                    uow.session,
                    batch_id=batch_id,
                    actor_id=str(user.id),
                    files=inputs,
                    quarantine_path=settings.quarantine_path,
                    limits=limits,
                    pending_files=pending,
                )
                uow.commit()
            except Exception:
                quarantine_storage.cleanup_paths(pending)
                raise
        # reload with blob
        outs: list[OccurrenceOut] = []
        for item in result.items:
            occ = ingestion_queries.get_occurrence_detail(db, item.occurrence.id)
            outs.append(_occ_out(occ))
        return UploadResponse(batch_id=batch_id, results=outs)
    except IngestionError as exc:
        quarantine_storage.cleanup_paths(pending)
        raise _map_error(exc) from exc


@router.get("/occurrences/{occurrence_id}", response_model=OccurrenceOut)
def get_occurrence(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        occ = ingestion_queries.get_occurrence_detail(db, occurrence_id)
        return _occ_out(occ)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/occurrences/{occurrence_id}/content")
def get_occurrence_content(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve bytes da quarantine para viewer (I2) — não promove Documents."""
    enforce_permission(user, "ingestion:read")
    settings = get_settings()
    try:
        occ = ingestion_queries.get_occurrence_detail(db, occurrence_id)
    except IngestionError as exc:
        raise _map_error(exc) from exc
    if occ.blob is None or occ.blob.physical_status != "PRESENT" or not occ.blob.storage_path:
        raise AppError(
            "Conteúdo físico indisponível (purged ou ausente)",
            code="content_unavailable",
            status_code=404,
        )
    path = quarantine_storage.resolve_quarantine_path(
        settings.quarantine_path, occ.blob.storage_path
    )
    if path is None or not path.is_file():
        raise AppError(
            "Arquivo de quarantine não encontrado",
            code="content_unavailable",
            status_code=404,
        )
    media = occ.detected_mime or occ.declared_mime or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media,
        filename=occ.original_filename or f"occurrence-{occurrence_id}",
    )


@router.post("/occurrences/{occurrence_id}/abandon", response_model=OccurrenceOut)
def abandon_occurrence(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            occ = ingestion_commands.abandon_occurrence(
                uow.session,
                occurrence_id=occurrence_id,
                actor_id=str(user.id),
                limits=limits_from_mapping(get_settings()),
            )
            uow.commit()
        occ = ingestion_queries.get_occurrence_detail(db, occurrence_id)
        return _occ_out(occ)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/purge", response_model=PurgeResponse)
def purge(
    body: PurgeRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:purge")
    settings = get_settings()
    try:
        with UnitOfWork(db) as uow:
            raw = ingestion_commands.execute_purge(
                uow.session,
                actor_id=str(user.id),
                quarantine_path=settings.quarantine_path,
                limits=limits_from_mapping(settings),
                dry_run=body.dry_run,
            )
            if not body.dry_run:
                uow.commit()
            else:
                uow.session.rollback()
        return PurgeResponse(**raw)
    except IngestionError as exc:
        raise _map_error(exc) from exc


# --- J3-I1 staging IR ---


def _field_out(f) -> FieldOut:
    return FieldOut(
        id=f.id,
        document_id=f.document_id,
        section_id=f.section_id,
        field_key=f.field_key,
        value_type=f.value_type,
        raw_value=f.raw_value,
        normalized_value=f.normalized_value,
        corrected_value=f.corrected_value,
        effective_value=effective_field_value(f),
        locator_json=f.locator_json,
        provenance_json=f.provenance_json,
        review_status=f.review_status,
        version=f.version,
    )


def _doc_out(doc, *, created_order_id: int | None = None, created_order_code: str | None = None) -> DocumentOut:
    issues = list(doc.issues or [])
    return DocumentOut(
        id=doc.id,
        occurrence_id=doc.occurrence_id,
        batch_id=doc.batch_id,
        document_set_id=doc.document_set_id,
        doc_type=doc.doc_type,
        adapter_id=doc.adapter_id,
        adapter_version=doc.adapter_version,
        ir_schema_version=doc.ir_schema_version,
        review_status=doc.review_status,
        version=doc.version,
        locked_by_actor_id=doc.locked_by_actor_id,
        locked_at=doc.locked_at,
        created_by_actor_id=doc.created_by_actor_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        sections=[
            SectionOut(
                id=s.id,
                document_id=s.document_id,
                section_key=s.section_key,
                title=s.title,
                ordinal=s.ordinal,
                review_status=s.review_status,
                version=s.version,
            )
            for s in sorted(doc.sections or [], key=lambda x: x.ordinal)
        ],
        fields=[_field_out(f) for f in doc.fields or []],
        rows=[
            RowOut(
                id=r.id,
                document_id=r.document_id,
                section_id=r.section_id,
                row_index=r.row_index,
                row_key=r.row_key,
                cells_json=r.cells_json,
                review_status=r.review_status,
                version=r.version,
            )
            for r in sorted(doc.rows or [], key=lambda x: x.row_index)
        ],
        issues=[
            IssueOut(
                id=i.id,
                document_id=i.document_id,
                severity=i.severity,
                code=i.code,
                message=i.message,
                target_type=i.target_type,
                target_id=i.target_id,
                status=i.status,
                locator_json=i.locator_json,
            )
            for i in issues
        ],
        open_issue_count=sum(1 for i in issues if i.status == "OPEN"),
        created_order_id=created_order_id,
        created_order_code=created_order_code,
    )


def _doc_summary(
    doc,
    *,
    created_order_id: int | None = None,
    created_order_code: str | None = None,
) -> DocumentSummaryOut:
    open_count = 0
    if getattr(doc, "issues", None) is not None:
        open_count = sum(1 for i in doc.issues if i.status == "OPEN")
    return DocumentSummaryOut(
        id=doc.id,
        occurrence_id=doc.occurrence_id,
        batch_id=doc.batch_id,
        doc_type=doc.doc_type,
        review_status=doc.review_status,
        version=doc.version,
        adapter_id=doc.adapter_id,
        open_issue_count=open_count,
        updated_at=doc.updated_at,
        created_order_id=created_order_id,
        created_order_code=created_order_code,
    )


def _created_order_kwargs(db: Session, document_id: int) -> dict:
    info = staging_commands.get_succeeded_create_order(db, document_id)
    if info is None:
        return {"created_order_id": None, "created_order_code": None}
    return {"created_order_id": info[0], "created_order_code": info[1]}


@router.post("/documents", response_model=DocumentOut)
def seed_document(
    body: DocumentSeedIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            doc = staging_commands.seed_document_from_occurrence(
                uow.session,
                occurrence_id=body.occurrence_id,
                actor_id=str(user.id),
                doc_type=body.doc_type,
                adapter_id=body.adapter_id,
                adapter_version=body.adapter_version,
                fields=[f.model_dump() for f in body.fields],
                rows=[r.model_dump() for r in body.rows],
                sections=[s.model_dump() for s in body.sections],
                issues=[i.model_dump() for i in body.issues],
            )
            uow.commit()
        detail = staging_queries.get_document_detail(db, doc.id)
        return _doc_out(detail)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        detail = staging_queries.get_document_detail(db, document_id)
        kwargs = _created_order_kwargs(db, document_id)
        out = _doc_out(detail, **kwargs)
        if out.review_status == "REJECTED" and out.created_order_id is not None:
            out.review_status = "READY"
        return out
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/documents/{document_id}/reextract", response_model=DocumentOut)
def reextract_document(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RUX-2R-b — isolado: endpoint desabilitado até autorização + revisão + testes.

    Implementação permanece em staging_commands.reextract_document (WIP).
    """
    enforce_permission(user, "ingestion:write")
    _ = (document_id, db)  # path reserved; not invoked
    raise AppError(
        "Reextract isolado (RUX-2R-b) — campanha não autorizada na árvore 019",
        code="reextract_not_authorized",
        status_code=501,
    )


@router.get("/batches/{batch_id}/documents", response_model=list[DocumentSummaryOut])
def list_batch_documents(
    batch_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    docs = staging_queries.list_documents_for_batch(db, batch_id)
    order_map = staging_commands.get_succeeded_create_orders_map(db, [d.id for d in docs])
    out = []
    for d in docs:
        oid, ocode = order_map.get(d.id, (None, None))
        out.append(_doc_summary(d, created_order_id=oid, created_order_code=ocode))
    return out


@router.get("/staging/queue", response_model=list[DocumentSummaryOut])
def staging_queue(
    review_status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    docs = staging_queries.staging_queue(db, review_status=review_status)
    order_map = staging_commands.get_succeeded_create_orders_map(db, [d.id for d in docs])
    out = []
    for d in docs:
        oid, ocode = order_map.get(d.id, (None, None))
        # Status desonesto: REJECTED + pedido criado → exibe READY (repair persistente no cleanup R4).
        display_status = d.review_status
        if display_status == "REJECTED" and oid is not None:
            display_status = "READY"
        summary = _doc_summary(d, created_order_id=oid, created_order_code=ocode)
        summary.review_status = display_status
        out.append(summary)
    return out


@router.put("/documents/{document_id}/order-code", response_model=FieldOut)
def put_order_code(
    document_id: int,
    body: OrderCodeOverrideIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Define código interno do pedido sem alterar o número do documento (external_ref)."""
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            field = staging_commands.set_order_code_override(
                uow.session,
                document_id=document_id,
                actor_id=str(user.id),
                order_code=body.order_code,
                expected_version=body.expected_version,
                reason=body.reason,
            )
            uow.commit()
        return _field_out(field)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.patch("/fields/{field_id}", response_model=FieldOut)
def patch_field(
    field_id: int,
    body: FieldCorrectIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            field = staging_commands.correct_field(
                uow.session,
                field_id=field_id,
                actor_id=str(user.id),
                corrected_value=body.corrected_value,
                expected_version=body.expected_version,
                reason=body.reason,
            )
            uow.commit()
            uow.session.refresh(field)
            return _field_out(field)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/fields/{field_id}/restore", response_model=FieldOut)
def restore_field(
    field_id: int,
    body: FieldRestoreIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            field = staging_commands.restore_field(
                uow.session,
                field_id=field_id,
                actor_id=str(user.id),
                expected_version=body.expected_version,
                reason=body.reason,
            )
            uow.commit()
            uow.session.refresh(field)
            return _field_out(field)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.patch("/rows/{row_id}", response_model=RowOut)
def patch_row(
    row_id: int,
    body: RowCorrectIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    import json as _json

    cells_json = body.cells_json
    if cells_json is None and body.cells is not None:
        cells_json = _json.dumps(body.cells, ensure_ascii=False)
    if cells_json is None:
        raise AppError("cells_json ou cells obrigatório", code="validation_error", status_code=422)
    try:
        with UnitOfWork(db) as uow:
            row = staging_commands.correct_row(
                uow.session,
                row_id=row_id,
                actor_id=str(user.id),
                cells_json=cells_json,
                expected_version=body.expected_version,
                reason=body.reason,
            )
            uow.commit()
            uow.session.refresh(row)
            return RowOut(
                id=row.id,
                document_id=row.document_id,
                section_id=row.section_id,
                row_index=row.row_index,
                row_key=row.row_key,
                cells_json=row.cells_json,
                review_status=row.review_status,
                version=row.version,
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


def _row_out(row) -> RowOut:
    return RowOut(
        id=row.id,
        document_id=row.document_id,
        section_id=row.section_id,
        row_index=row.row_index,
        row_key=row.row_key,
        cells_json=row.cells_json,
        review_status=row.review_status,
        version=row.version,
    )


@router.post("/documents/{document_id}/rows", response_model=RowOut, status_code=201)
def add_row(
    document_id: int,
    body: RowAddIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    import json as _json

    cells_json = body.cells_json
    if cells_json is None and body.cells is not None:
        cells_json = _json.dumps(body.cells, ensure_ascii=False)
    if cells_json is None:
        cells_json = "{}"
    try:
        with UnitOfWork(db) as uow:
            row = staging_commands.add_row(
                uow.session,
                document_id=document_id,
                actor_id=str(user.id),
                cells_json=cells_json,
                expected_document_version=body.expected_version,
                section_id=body.section_id,
                row_key=body.row_key,
                reason=body.reason,
            )
            uow.commit()
            uow.session.refresh(row)
            return _row_out(row)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.delete("/rows/{row_id}", status_code=204)
def delete_row(
    row_id: int,
    expected_version: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            staging_commands.remove_row(
                uow.session,
                row_id=row_id,
                actor_id=str(user.id),
                expected_version=expected_version,
            )
            uow.commit()
        return None
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.patch("/sections/{section_id}", response_model=SectionOut)
def patch_section(
    section_id: int,
    body: SectionReviewIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            section = staging_commands.review_section(
                uow.session,
                section_id=section_id,
                actor_id=str(user.id),
                review_status=body.review_status,
                expected_version=body.expected_version,
                reason=body.reason,
            )
            uow.commit()
            uow.session.refresh(section)
            return SectionOut(
                id=section.id,
                document_id=section.document_id,
                section_key=section.section_key,
                title=section.title,
                ordinal=section.ordinal,
                review_status=section.review_status,
                version=section.version,
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.patch("/documents/{document_id}/review-status", response_model=DocumentOut)
def patch_document_review(
    document_id: int,
    body: DocumentReviewIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            staging_commands.set_document_review_status(
                uow.session,
                document_id=document_id,
                actor_id=str(user.id),
                review_status=body.review_status,
                expected_version=body.expected_version,
            )
            uow.commit()
        return _doc_out(
            staging_queries.get_document_detail(db, document_id),
            **_created_order_kwargs(db, document_id),
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exclusão definitiva da importação — bloqueada se já criou pedido."""
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            staging_commands.hard_delete_document(
                uow.session,
                document_id=document_id,
                actor_id=str(user.id),
            )
            uow.commit()
        return None
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/documents/{document_id}/lock", response_model=DocumentOut)
def lock_document(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            staging_commands.lock_document(
                uow.session, document_id=document_id, actor_id=str(user.id)
            )
            uow.commit()
        return _doc_out(staging_queries.get_document_detail(db, document_id))
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/documents/{document_id}/unlock", response_model=DocumentOut)
def unlock_document(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            staging_commands.unlock_document(
                uow.session, document_id=document_id, actor_id=str(user.id)
            )
            uow.commit()
        return _doc_out(staging_queries.get_document_detail(db, document_id))
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/documents/{document_id}/issues", response_model=IssueOut)
def create_issue(
    document_id: int,
    body: IssueCreateIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            issue = staging_commands.create_issue(
                uow.session,
                document_id=document_id,
                actor_id=str(user.id),
                severity=body.severity,
                code=body.code,
                message=body.message,
                target_type=body.target_type,
                target_id=body.target_id,
                locator_json=body.locator_json,
            )
            uow.commit()
            uow.session.refresh(issue)
            return IssueOut(
                id=issue.id,
                document_id=issue.document_id,
                severity=issue.severity,
                code=issue.code,
                message=issue.message,
                target_type=issue.target_type,
                target_id=issue.target_id,
                status=issue.status,
                locator_json=issue.locator_json,
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.patch("/issues/{issue_id}", response_model=IssueOut)
def resolve_issue(
    issue_id: int,
    body: IssueResolveIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            issue = staging_commands.resolve_issue(
                uow.session,
                issue_id=issue_id,
                actor_id=str(user.id),
                status=body.status,
                justification=body.justification,
            )
            uow.commit()
            uow.session.refresh(issue)
            return IssueOut(
                id=issue.id,
                document_id=issue.document_id,
                severity=issue.severity,
                code=issue.code,
                message=issue.message,
                target_type=issue.target_type,
                target_id=issue.target_id,
                status=issue.status,
                locator_json=issue.locator_json,
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/documents/{document_id}/changes", response_model=list[ReviewChangeOut])
def list_changes(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        changes = staging_queries.list_review_changes(db, document_id)
        return [
            ReviewChangeOut(
                id=c.id,
                document_id=c.document_id,
                target_type=c.target_type,
                target_id=c.target_id,
                actor_id=c.actor_id,
                previous_value=c.previous_value,
                new_value=c.new_value,
                previous_review_status=c.previous_review_status,
                new_review_status=c.new_review_status,
                reason=c.reason,
                created_at=c.created_at,
            )
            for c in changes
        ]
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/document-sets", response_model=DocumentSetOut)
def create_document_set(
    body: DocumentSetCreateIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            ds = staging_commands.create_document_set(
                uow.session,
                actor_id=str(user.id),
                batch_id=body.batch_id,
                projection_key=body.projection_key,
                label=body.label,
            )
            uow.commit()
        detail = staging_queries.get_document_set(db, ds.id)
        return DocumentSetOut(
            id=detail.id,
            batch_id=detail.batch_id,
            projection_key=detail.projection_key,
            label=detail.label,
            created_by_actor_id=detail.created_by_actor_id,
            created_at=detail.created_at,
            members=[
                DocumentSetMemberOut(
                    id=m.id,
                    document_set_id=m.document_set_id,
                    document_id=m.document_id,
                    role=m.role,
                )
                for m in detail.members
            ],
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/document-sets/{set_id}/members", response_model=DocumentSetMemberOut)
def add_set_member(
    set_id: int,
    body: DocumentSetMemberIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            m = staging_commands.add_document_to_set(
                uow.session,
                document_set_id=set_id,
                document_id=body.document_id,
                role=body.role,
            )
            uow.commit()
            uow.session.refresh(m)
            return DocumentSetMemberOut(
                id=m.id,
                document_set_id=m.document_set_id,
                document_id=m.document_id,
                role=m.role,
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/document-sets/{set_id}", response_model=DocumentSetOut)
def get_document_set(
    set_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        detail = staging_queries.get_document_set(db, set_id)
        return DocumentSetOut(
            id=detail.id,
            batch_id=detail.batch_id,
            projection_key=detail.projection_key,
            label=detail.label,
            created_by_actor_id=detail.created_by_actor_id,
            created_at=detail.created_at,
            members=[
                DocumentSetMemberOut(
                    id=m.id,
                    document_set_id=m.document_set_id,
                    document_id=m.document_id,
                    role=m.role,
                )
                for m in detail.members
            ],
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


# --- J3-I3: adapter / preview / commit ---


def _attempt_out(attempt) -> CommitAttemptOut:
    return CommitAttemptOut(
        id=attempt.id,
        document_id=attempt.document_id,
        operation_key=attempt.operation_key,
        payload_fingerprint=attempt.payload_fingerprint,
        status=attempt.status,
        actor_id=attempt.actor_id,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
        operations=[
            CommitOperationOut(
                id=op.id,
                op_key=op.op_key,
                status=op.status,
                entity_type=op.entity_type,
                entity_id=op.entity_id,
                error_message=op.error_message,
                details_json=op.details_json,
            )
            for op in (attempt.operations or [])
        ],
    )


def _promote_or_log(pending_files: list[Path], *, document_id: int, attempt_id: int) -> None:
    """Promove os arquivos temporários após o commit de banco.

    Falha aqui não invalida o commit: o Document já existe e a leitura promove o
    pendente (heal em ``documents_public.resolve_content_path``).
    """
    failures = documents_public.promote_pending_files(pending_files)
    if failures:
        logger.error(
            "promote de arquivo pendente falhou — heal na leitura "
            "(document_id=%s attempt_id=%s paths=%s)",
            document_id,
            attempt_id,
            [str(p) for p in failures],
        )


@router.get("/adapters", response_model=list[AdapterInfoOut])
def list_adapters(user=Depends(get_current_user)):
    enforce_permission(user, "ingestion:read")
    from app.ingestion import adapter_registry

    return [
        AdapterInfoOut(
            adapter_id=e.adapter_id,
            doc_type=e.doc_type,
            label=e.label,
            adapter_version="1",
            mime_kinds=list(e.mime_kinds),
        )
        for e in adapter_registry.list_adapters()
    ]


@router.post("/occurrences/{occurrence_id}/classify", response_model=ClassifyOut)
def classify_occurrence(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sugere adapter/doc_type sem semear IR — operador confirma na UI."""
    enforce_permission(user, "ingestion:write")
    settings = get_settings()
    from app.ingestion import adapter_registry

    try:
        occ = ingestion_queries.get_occurrence_detail(db, occurrence_id)
    except IngestionError as exc:
        raise _map_error(exc) from exc
    if occ.blob is None or occ.blob.physical_status != "PRESENT" or not occ.blob.storage_path:
        raise AppError(
            "Conteúdo físico indisponível",
            code="content_unavailable",
            status_code=404,
        )
    path = quarantine_storage.resolve_quarantine_path(
        settings.quarantine_path, occ.blob.storage_path
    )
    if path is None or not path.is_file():
        raise AppError("Arquivo de quarantine não encontrado", code="content_unavailable", status_code=404)
    data = path.read_bytes()
    suggestions = adapter_registry.classify_occurrence_bytes(
        data,
        filename=occ.original_filename,
        detected_mime=occ.detected_mime or occ.declared_mime,
    )
    return ClassifyOut(
        occurrence_id=occurrence_id,
        filename=occ.original_filename,
        detected_mime=occ.detected_mime or occ.declared_mime,
        suggestions=[ClassifySuggestionOut(**s) for s in suggestions],
    )


@router.post("/occurrences/{occurrence_id}/run-adapter", response_model=DocumentOut)
def run_adapter(
    occurrence_id: int,
    body: RunAdapterIn | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executa adapter tipado via registry (Ordine default se body vazio).

    Body opcional: {adapter_id} ou {doc_type}. Aliases dedicados (fattura/xlsx/…)
    permanecem por compatibilidade.
    """
    enforce_permission(user, "ingestion:write")
    settings = get_settings()
    from app.ingestion import adapter_registry

    payload = body or RunAdapterIn()
    try:
        adapter_id = adapter_registry.resolve_adapter_id(
            adapter_id=payload.adapter_id,
            doc_type=payload.doc_type,
        )
        entry = adapter_registry.get_adapter(adapter_id)
        with UnitOfWork(db) as uow:
            doc = entry.run(
                uow.session,
                occurrence_id=occurrence_id,
                actor_id=str(user.id),
                quarantine_path=settings.quarantine_path,
            )
            uow.commit()
        detail = staging_queries.get_document_detail(db, doc.id)
        return _doc_out(detail)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/documents/{document_id}/preview-commit", response_model=PreviewCommitOut)
def preview_commit(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna digest + lista de operações que o commit executaria (sem escrever owners)."""
    enforce_permission(user, "ingestion:read")
    try:
        result = commit_commands.preview_commit(db, document_id)
        return PreviewCommitOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            operations=[
                PreviewOperationOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    params=op.params,
                )
                for op in result.operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
            can_create_order=result.can_create_order,
            blocking_reasons=list(result.blocking_reasons or []),
            human_summary=result.human_summary or "",
            readiness_derived=result.readiness_derived,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/documents/{document_id}/commit", response_model=CommitAttemptOut)
def commit_document(
    document_id: int,
    body: CommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executa commit tudo-ou-nada: promote document + cria Order DRAFT.

    Dual-auth: requer ingestion:commit E orders:write.
    Se o preview inclui create_supplier (intent no IR), exige também catalog:write.
    Idempotência por operation_key + payload_fingerprint.
    Qualquer operação que falhe reverte a transação inteira; o arquivo só é
    promovido da área temporária depois do commit de banco.
    """
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "orders:write")
    preview = commit_commands.preview_commit(db, document_id)
    if any(op.op_key == "create_supplier" for op in preview.operations):
        enforce_permission(user, "catalog:write")
    settings = get_settings()
    pending_files: list[Path] = []
    try:
        with UnitOfWork(db) as uow:
            attempt = commit_commands.execute_commit(
                uow.session,
                document_id=document_id,
                operation_key=body.operation_key,
                actor_id=str(user.id),
                attachments_path=settings.attachments_path,
                quarantine_path=settings.quarantine_path,
                pending_files=pending_files,
            )
            uow.commit()
            uow.session.refresh(attempt)
            attempt_id = attempt.id
        _promote_or_log(pending_files, document_id=document_id, attempt_id=attempt_id)
        return _attempt_out(commit_queries.get_commit_attempt(db, attempt_id))
    except CommitOperationFailed as exc:
        db.rollback()
        documents_public.discard_pending_files(pending_files)
        attempt_id = commit_failure.record_commit_failure(exc.trail)
        return _attempt_out(commit_queries.get_commit_attempt(db, attempt_id))
    except CommitSupplierLinkRequired as exc:
        db.rollback()
        documents_public.discard_pending_files(pending_files)
        raise _map_error(exc) from exc
    except CommitOrderCodeExists as exc:
        db.rollback()
        documents_public.discard_pending_files(pending_files)
        raise _map_error(exc) from exc
    except IngestionError as exc:
        db.rollback()
        documents_public.discard_pending_files(pending_files)
        raise _map_error(exc) from exc


@router.get("/commit-attempts/{attempt_id}", response_model=CommitAttemptOut)
def get_commit_attempt(
    attempt_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consulta status de um CommitAttempt."""
    enforce_permission(user, "ingestion:read")
    try:
        attempt = commit_queries.get_commit_attempt(db, attempt_id)
        return _attempt_out(attempt)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/documents/{document_id}/commit-attempts", response_model=list[CommitAttemptOut])
def list_document_commit_attempts(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista todos os CommitAttempts para um documento."""
    enforce_permission(user, "ingestion:read")
    attempts = commit_queries.list_commit_attempts_for_document(db, document_id)
    return [_attempt_out(a) for a in attempts]


# --- J3-I4: Fattura + Order policy A/B/C1/C2 ---


@router.post("/occurrences/{occurrence_id}/run-adapter-fattura", response_model=DocumentOut)
def run_adapter_fattura(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Classifica e extrai Fattura da quarantine; semeia IR IngestionDocument.

    Usa o adapter fattura_heroes_v1. Falha com 409 se já existe IR para esta occurrence.
    """
    enforce_permission(user, "ingestion:write")
    settings = get_settings()
    try:
        from app.ingestion.adapters import fattura_heroes_v1 as adapter

        with UnitOfWork(db) as uow:
            doc = adapter.run_adapter(
                uow.session,
                occurrence_id=occurrence_id,
                actor_id=str(user.id),
                quarantine_path=settings.quarantine_path,
            )
            uow.commit()
        detail = staging_queries.get_document_detail(db, doc.id)
        return _doc_out(detail)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get("/documents/{document_id}/preview-commit-fattura", response_model=FatturaPreviewOut)
def preview_commit_fattura(
    document_id: int,
    policy: str = "A",
    order_id: int | None = None,
    c2_confirm: bool = False,
    c2_reason: str | None = None,
    line_choices: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview do commit Fattura com policy A/B/C1/C2 — sem escrever owners."""
    enforce_permission(user, "ingestion:read")
    try:
        parsed_choices = None
        if line_choices:
            try:
                raw = json.loads(line_choices)
            except json.JSONDecodeError as exc:
                raise IngestionError(
                    "line_choices inválido (JSON)",
                    code="fattura_line_choice_invalid",
                ) from exc
            if not isinstance(raw, list):
                raise IngestionError(
                    "line_choices deve ser uma lista JSON",
                    code="fattura_line_choice_invalid",
                )
            parsed_choices = raw
        result = fattura_commit_commands.preview_commit_fattura(
            db,
            document_id,
            policy=policy,
            order_id=order_id,
            c2_confirm=c2_confirm,
            c2_reason=c2_reason,
            line_choices=parsed_choices,
        )
        return FatturaPreviewOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            policy_match=FatturaPolicyMatchOut(
                policy=result.policy_match.policy,
                order_id=result.policy_match.order_id,
                order_status=result.policy_match.order_status,
                order_code=result.policy_match.order_code,
                invoice_will_be_created=result.policy_match.invoice_will_be_created,
                warning=result.policy_match.warning,
            ),
            operations=[
                FatturaPreviewOperationOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    params=op.params,
                )
                for op in result.operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
            order_candidates=[
                FatturaOrderCandidateOut(**c) for c in result.order_candidates
            ],
            order_candidates_reason=result.order_candidates_reason,
            line_matches=[
                FatturaLineMatchOut(
                    row_index=m["row_index"],
                    sku=m["sku"],
                    pdf_qty=m["pdf_qty"],
                    pdf_unit_price=m.get("pdf_unit_price"),
                    order_item_id=m.get("order_item_id"),
                    order_unit_price=m.get("order_unit_price"),
                    remaining_before=m.get("remaining_before"),
                    candidate_count=m.get("candidate_count") or 0,
                    candidates=[
                        FatturaLineCandidateOut(**c) for c in (m.get("candidates") or [])
                    ],
                    price_mismatch=bool(m.get("price_mismatch")),
                    ambiguous_price=bool(m.get("ambiguous_price")),
                    status=m.get("status") or "unmatched",
                )
                for m in result.line_matches
            ],
            already_committed=result.already_committed,
            last_succeeded_attempt_id=result.last_succeeded_attempt_id,
            last_succeeded_invoice_id=result.last_succeeded_invoice_id,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post("/documents/{document_id}/commit-fattura", response_model=CommitAttemptOut)
def commit_document_fattura(
    document_id: int,
    body: FatturaCommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executa commit idempotente Fattura com policy A/B/C1/C2.

    - Policy A: Order CONFIRMED → Invoice DRAFT (ingestion:commit + billing:write + orders:write)
    - Policy B: Order DRAFT → bloqueia (422, user must confirm separately)
    - Policy C1: Sem Order → cria reconstruction DRAFT, PENDING_CONFIRM
    - Policy C2: Sem Order + c2_confirm=True → reconstruction + confirm + Invoice DRAFT
                 (dual-auth: ingestion:commit + billing:write + orders:write)

    Idempotência por operation_key + payload_fingerprint.
    """
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "orders:write")
    if body.policy in (fattura_commit_commands.POLICY_A, fattura_commit_commands.POLICY_C2):
        enforce_permission(user, "billing:write")
    settings = get_settings()
    pending_files: list[Path] = []
    try:
        with UnitOfWork(db) as uow:
            attempt = fattura_commit_commands.execute_commit_fattura(
                uow.session,
                document_id=document_id,
                operation_key=body.operation_key,
                actor_id=str(user.id),
                policy=body.policy,
                order_id=body.order_id,
                c2_confirm=body.c2_confirm,
                c2_reason=body.c2_reason,
                line_choices=[c.model_dump() for c in body.line_choices],
                attachments_path=settings.attachments_path,
                quarantine_path=settings.quarantine_path,
                pending_files=pending_files,
            )
            if attempt.status != "SUCCEEDED":
                # Tudo-ou-nada: nenhuma operação sobrevive a um commit incompleto.
                trail = commit_failure.snapshot_attempt_failure(
                    attempt, context={"policy": body.policy, "doc_type": "FATTURA"}
                )
                uow.rollback()
                documents_public.discard_pending_files(pending_files)
                attempt_id = commit_failure.record_commit_failure(trail)
                return _attempt_out(commit_queries.get_commit_attempt(db, attempt_id))
            uow.commit()
            uow.session.refresh(attempt)
            attempt_id = attempt.id
        _promote_or_log(pending_files, document_id=document_id, attempt_id=attempt_id)
        return _attempt_out(commit_queries.get_commit_attempt(db, attempt_id))
    except CommitOperationFailed as exc:
        db.rollback()
        documents_public.discard_pending_files(pending_files)
        attempt_id = commit_failure.record_commit_failure(exc.trail)
        return _attempt_out(commit_queries.get_commit_attempt(db, attempt_id))
    except IngestionError as exc:
        db.rollback()
        documents_public.discard_pending_files(pending_files)
        raise _map_error(exc) from exc

# ---------------------------------------------------------------------------
# I5 routes: Dossier preview + commit (PL Detail, Fattura Doganale)
# ---------------------------------------------------------------------------


@router.get("/document-sets/{document_set_id}/preview-dossier", response_model=DossierPreviewOut)
def preview_dossier(
    document_set_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview do commit do dossier - sem escrever nada."""
    enforce_permission(user, "ingestion:read")
    try:
        result = dossier_commands.preview_dossier(db, document_set_id)
        return DossierPreviewOut(
            document_set_id=result.document_set_id,
            documents_found=result.documents_found,
            reconciliation_issues=[
                ReconciliationIssueOut(
                    code=ri["code"],
                    severity=ri["severity"],
                    message=ri["message"],
                    doc_types=ri.get("doc_types", []),
                )
                for ri in result.reconciliation_issues
            ],
            planned_operations=[
                DossierPreviewItemOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                )
                for op in result.planned_operations
            ],
            can_commit=result.can_commit,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/documents/{document_id}/preview-commit-pl-detail",
    response_model=PackingPreviewOut,
)
def preview_commit_pl_detail(
    document_id: int,
    order_id: int | None = None,
    shipment_id: int | None = None,
    line_choices: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview do commit Packing List Detail — sem escrever owners."""
    enforce_permission(user, "ingestion:read")
    try:
        parsed_choices = None
        if line_choices:
            try:
                raw = json.loads(line_choices)
            except json.JSONDecodeError as exc:
                raise IngestionError(
                    "line_choices inválido (JSON)",
                    code="packing_line_choice_invalid",
                ) from exc
            if not isinstance(raw, list):
                raise IngestionError(
                    "line_choices deve ser uma lista JSON",
                    code="packing_line_choice_invalid",
                )
            parsed_choices = raw
        result = packing_commit_commands.preview_commit_pl_detail(
            db,
            document_id,
            order_id=order_id,
            shipment_id=shipment_id,
            line_choices=parsed_choices,
        )
        return PackingPreviewOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            operations=[
                PackingPreviewOperationOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    params=op.params,
                )
                for op in result.operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
            order_candidates=[
                PackingOrderCandidateOut(**c) for c in result.order_candidates
            ],
            order_candidates_reason=result.order_candidates_reason,
            shipment_targets=[
                PackingShipmentTargetOut(**t) for t in result.shipment_targets
            ],
            shipment_targets_reason=result.shipment_targets_reason,
            line_matches=[
                PackingLineMatchOut(
                    **{
                        **m,
                        "candidates": [
                            PackingLineCandidateOut(**c) for c in m.get("candidates", [])
                        ],
                    }
                )
                for m in result.line_matches
            ],
            cartons=[PackingCartonOut(**c) for c in result.cartons],
            blockers=result.blockers,
            resolved_order_id=result.resolved_order_id,
            resolved_shipment_id=result.resolved_shipment_id,
            will_create_shipment=result.will_create_shipment,
            already_committed=result.already_committed,
            last_succeeded_attempt_id=result.last_succeeded_attempt_id,
            last_succeeded_shipment_id=result.last_succeeded_shipment_id,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/documents/{document_id}/commit-pl-detail",
    response_model=CommitAttemptOut,
)
def commit_document_pl_detail(
    document_id: int,
    body: PackingCommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Commit PL Detail: promove documento + preenche Shipment PLANNED via Logistics."""
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "logistics:write")
    settings = get_settings()
    try:
        with UnitOfWork(db) as uow:
            attempt = dossier_commands.commit_pl_detail(
                uow.session,
                document_id=document_id,
                operation_key=body.operation_key,
                actor_id=str(user.id),
                attachments_path=settings.attachments_path,
                quarantine_path=settings.quarantine_path,
                order_id=body.order_id,
                shipment_id=body.shipment_id,
                line_choices=[c.model_dump() for c in body.line_choices],
            )
            uow.commit()
            uow.session.refresh(attempt)
        attempt = commit_queries.get_commit_attempt(db, attempt.id)
        return _attempt_out(attempt)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/documents/{document_id}/preview-commit-doganale",
    response_model=DoganalePreviewOut,
)
def preview_commit_doganale(
    document_id: int,
    process_id: int | None = None,
    invoice_id: int | None = None,
    shipment_id: int | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        result = doganale_commit_commands.preview_commit_doganale(
            db,
            document_id,
            process_id=process_id,
            invoice_id=invoice_id,
            shipment_id=shipment_id,
        )
        return DoganalePreviewOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            operations=[
                DoganalePreviewOpOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    params=op.params,
                )
                for op in result.operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
            process_targets=[DoganaleProcessTargetOut(**t) for t in result.process_targets],
            process_targets_reason=result.process_targets_reason,
            invoice_candidates=[DoganaleInvoiceCandidateOut(**c) for c in result.invoice_candidates],
            invoice_candidates_reason=result.invoice_candidates_reason,
            shipment_targets=[DoganaleShipmentTargetOut(**t) for t in result.shipment_targets],
            shipment_targets_reason=result.shipment_targets_reason,
            lines=[DoganaleLinePreviewOut(**{k: ln.get(k) for k in (
                "position", "ncm", "description", "quantity", "unit", "currency",
                "unit_price", "line_amount",
            )}) for ln in result.lines],
            blockers=result.blockers,
            resolved_process_id=result.resolved_process_id,
            resolved_invoice_id=result.resolved_invoice_id,
            resolved_shipment_id=result.resolved_shipment_id,
            will_create_process=result.will_create_process,
            reuse_reason=result.reuse_reason,
            already_committed=result.already_committed,
            last_succeeded_attempt_id=result.last_succeeded_attempt_id,
            last_succeeded_process_id=result.last_succeeded_process_id,
            document_number=result.document_number,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/documents/{document_id}/commit-doganale",
    response_model=CommitAttemptOut,
)
def commit_document_doganale(
    document_id: int,
    body: DoganaleCommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Commit Fattura Doganale: preenche CustomsDoganale + 0/1/N processo/fatura/embarque."""
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "customs:write")
    settings = get_settings()
    try:
        with UnitOfWork(db) as uow:
            attempt = dossier_commands.commit_doganale(
                uow.session,
                document_id=document_id,
                operation_key=body.operation_key,
                actor_id=str(user.id),
                attachments_path=settings.attachments_path,
                quarantine_path=settings.quarantine_path,
                process_id=body.process_id,
                invoice_id=body.invoice_id,
                shipment_id=body.shipment_id,
            )
            uow.commit()
            uow.session.refresh(attempt)
        attempt = commit_queries.get_commit_attempt(db, attempt.id)
        return _attempt_out(attempt)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/documents/{document_id}/preview-commit-print",
    response_model=PrintPreviewOut,
)
def preview_commit_print(
    document_id: int,
    process_id: int | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:read")
    try:
        result = print_commit_commands.preview_commit_print(
            db, document_id, process_id=process_id
        )
        return PrintPreviewOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            operations=[
                PrintPreviewOpOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    params=op.params,
                )
                for op in result.operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
            invoice_ref=result.invoice_ref,
            process_targets=[PrintProcessTargetOut(**t) for t in result.process_targets],
            process_targets_reason=result.process_targets_reason,
            blockers=result.blockers,
            already_committed=result.already_committed,
            last_succeeded_attempt_id=result.last_succeeded_attempt_id,
            last_succeeded_process_id=result.last_succeeded_process_id,
            resolved_process_id=result.resolved_process_id,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/documents/{document_id}/commit-print",
    response_model=CommitAttemptOut,
)
def commit_document_print(
    document_id: int,
    body: PrintCommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "customs:write")
    settings = get_settings()
    try:
        with UnitOfWork(db) as uow:
            attempt = print_commit_commands.commit_print(
                uow.session,
                document_id=document_id,
                operation_key=body.operation_key,
                actor_id=str(user.id),
                attachments_path=settings.attachments_path,
                quarantine_path=settings.quarantine_path,
                process_id=body.process_id,
            )
            uow.commit()
            uow.session.refresh(attempt)
        attempt = commit_queries.get_commit_attempt(db, attempt.id)
        return _attempt_out(attempt)
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/document-sets/{document_set_id}/reconcile",
    response_model=list[ReconciliationIssueOut],
)
def reconcile_document_set_route(
    document_set_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executa reconciliacao cruzada e persiste issues no DB."""
    enforce_permission(user, "ingestion:write")
    try:
        with UnitOfWork(db) as uow:
            persisted = dossier_commands.reconcile_and_persist(
                uow.session,
                document_set_id=document_set_id,
                actor_id=str(user.id),
            )
            uow.commit()
        return [
            ReconciliationIssueOut(
                code=ri["code"],
                severity=ri["severity"],
                message=ri.get("message", ""),
                doc_types=[ri.get("doc_type", "")] if ri.get("doc_type") else [],
            )
            for ri in persisted
        ]
    except IngestionError as exc:
        raise _map_error(exc) from exc


# ---------- I6 Numerário ----------


@router.post(
    "/occurrences/{occurrence_id}/run-adapter-numerario",
    response_model=RunAdapterOut,
)
def run_adapter_numerario(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executa o adapter solicitacao_numerario_v1 em uma occurrence."""
    enforce_permission(user, "ingestion:write")
    settings = get_settings()
    try:
        from app.ingestion.adapters import solicitacao_numerario_v1

        with UnitOfWork(db) as uow:
            doc = solicitacao_numerario_v1.run_adapter(
                uow.session,
                occurrence_id=occurrence_id,
                actor_id=str(user.id),
                quarantine_path=settings.quarantine_path,
            )
            uow.commit()
            uow.session.refresh(doc)
        open_issues = sum(
            1
            for i in (doc.issues or [])
            if i.status == "OPEN"
        )
        return RunAdapterOut(
            document_id=doc.id,
            doc_type=doc.doc_type,
            adapter_id=doc.adapter_id,
            adapter_version=doc.adapter_version,
            review_status=doc.review_status,
            open_issue_count=open_issues,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/documents/{document_id}/preview-numerario",
    response_model=NumerarioPreviewOut,
)
def preview_numerario_commit(
    document_id: int,
    process_ids: str = "",
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview read-only do commit de Numerário — nenhuma escrita em owners.

    process_ids: comma-separated list of ImportProcess IDs to create FundingRequests for.
    """
    enforce_permission(user, "ingestion:read")
    pids: list[int] = []
    if process_ids:
        try:
            pids = [int(x.strip()) for x in process_ids.split(",") if x.strip()]
        except ValueError as exc:
            from app.foundation.errors import AppError
            raise AppError("process_ids deve ser lista de inteiros separados por vírgula", code="invalid_input", status_code=422) from exc
    try:
        result = numerario_commit_commands.preview_numerario(db, document_id, pids)
        return NumerarioPreviewOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            invoice_refs=result.invoice_refs,
            process_ids_input=result.process_ids_input,
            planned_operations=[
                NumerarioPreviewOpOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    process_id=op.process_id,
                    params=op.params,
                )
                for op in result.planned_operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
            process_candidates=[
                NumerarioProcessCandidateOut(**c) for c in result.process_candidates
            ],
            process_candidates_reason=result.process_candidates_reason,
            already_committed=result.already_committed,
            last_succeeded_attempt_id=result.last_succeeded_attempt_id,
            last_succeeded_process_id=result.last_succeeded_process_id,
            can_create_process=result.can_create_process,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/documents/{document_id}/commit-numerario",
    response_model=NumerarioCommitResultOut,
    status_code=201,
)
def commit_document_numerario(
    document_id: int,
    body: NumerarioCommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Commit Solicitação de Numerário: promove documento + cria Payee + FundingRequest DRAFT por processo.

    Multi-owner: cria um FundingRequest DRAFT por process_id em body.process_ids.
    NUNCA auto-confirma FundingRequest. NUNCA cria Payment. NUNCA liquida CUSTOMS_FUNDING.
    Sem rollback cross-owner — PARTIAL é o estado explícito para falha parcial.
    """
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "customs:write")
    settings = get_settings()
    try:
        with UnitOfWork(db) as uow:
            attempt = numerario_commit_commands.commit_numerario(
                uow.session,
                document_id=document_id,
                operation_key=body.operation_key,
                process_ids=list(body.process_ids or []),
                actor_id=str(user.id),
                attachments_path=settings.attachments_path,
                quarantine_path=settings.quarantine_path,
                create_process=body.create_process,
            )
            uow.commit()
            uow.session.refresh(attempt)
        attempt = commit_queries.get_commit_attempt(db, attempt.id)
        return NumerarioCommitResultOut(
            attempt_id=attempt.id,
            document_id=attempt.document_id,
            operation_key=attempt.operation_key,
            status=attempt.status,
            operations=[
                NumerarioOpResultOut(
                    op_key=op.op_key,
                    status=op.status,
                    entity_type=op.entity_type,
                    entity_id=op.entity_id,
                    error_message=op.error_message,
                    details_json=op.details_json,
                )
                for op in (attempt.operations or [])
            ],
        )
    except (NumerarioCommitConflictFingerprint, NumerarioCommitBlockedByIssues) as exc:
        raise _map_error(exc) from exc
    except IngestionError as exc:
        raise _map_error(exc) from exc


# ---------------------------------------------------------------------------
# J3-I7 — XLSX adapter routes
# ---------------------------------------------------------------------------


@router.post(
    "/occurrences/{occurrence_id}/run-adapter-xlsx",
    response_model=XlsxRunAdapterOut,
    status_code=201,
)
def run_adapter_xlsx(
    occurrence_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executa adapter ordine_heroes_xlsx_v1 para uma occurrence XLSX."""
    enforce_permission(user, "ingestion:write")
    from app.ingestion.adapters import ordine_heroes_xlsx_v1
    settings = get_settings()
    from pathlib import Path

    try:
        with UnitOfWork(db) as uow:
            doc = ordine_heroes_xlsx_v1.run_adapter(
                uow.session,
                occurrence_id=occurrence_id,
                actor_id=str(user.id),
                quarantine_path=Path(settings.quarantine_path),
            )
            uow.commit()
            uow.session.refresh(doc)

            formula_field = next(
                (f for f in (doc.fields or []) if f.field_key == "formula_cell_count"),
                None,
            )
            formula_count = int(formula_field.normalized_value or "0") if formula_field else 0
            classified = ordine_heroes_xlsx_v1.classify(
                ordine_heroes_xlsx_v1.AdapterRawResult(
                    order_number=next(
                        (f.normalized_value for f in doc.fields if f.field_key == "order_number"),
                        None,
                    ),
                    order_number_cell=None,
                    versato=None,
                    versato_cell=None,
                    sheet_name=next(
                        (f.normalized_value for f in doc.fields if f.field_key == "sheet_name"),
                        "",
                    ) or "",
                    all_sheets=[],
                )
            )
            return XlsxRunAdapterOut(
                occurrence_id=occurrence_id,
                document_id=doc.id,
                adapter_id=doc.adapter_id,
                doc_type=doc.doc_type,
                classified=classified,
                field_count=len(doc.fields or []),
                row_count=len(doc.rows or []),
                issue_count=len(doc.issues or []),
                formula_cell_count=formula_count,
            )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/documents/{document_id}/preview-commit-xlsx",
    response_model=XlsxPreviewOut,
)
def preview_commit_xlsx(
    document_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview read-only do commit XLSX — nenhuma escrita em owners."""
    enforce_permission(user, "ingestion:read")
    try:
        result = xlsx_commit_commands.preview_commit_xlsx(db, document_id)
        return XlsxPreviewOut(
            document_id=result.document_id,
            fingerprint=result.fingerprint,
            operations=[
                XlsxPreviewOperationOut(
                    op_key=op.op_key,
                    description=op.description,
                    entity_type=op.entity_type,
                    params=op.params,
                )
                for op in result.operations
            ],
            open_error_count=result.open_error_count,
            can_commit=result.can_commit,
        )
    except IngestionError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/documents/{document_id}/commit-xlsx",
    response_model=XlsxCommitResultOut,
    status_code=201,
)
def commit_document_xlsx(
    document_id: int,
    body: XlsxCommitIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Commit Ordine XLSX: store_document + create_order DRAFT + add_items + link_document.

    Dual-auth: ingestion:commit + orders:write.
    Idempotente por operation_key + fingerprint.
    """
    enforce_permission(user, "ingestion:commit")
    enforce_permission(user, "orders:write")
    settings = get_settings()
    from pathlib import Path

    try:
        with UnitOfWork(db) as uow:
            result = xlsx_commit_commands.commit_xlsx(
                uow.session,
                document_id,
                actor_id=str(user.id),
                operation_key=body.operation_key,
                quarantine_path=Path(settings.quarantine_path),
            )
            uow.commit()
            return XlsxCommitResultOut(
                attempt_id=result.attempt_id,
                document_id=result.document_id,
                status=result.status,
                operations=[
                    XlsxCommitOpOut(
                        op_key=op["op_key"],
                        status=op["status"],
                        entity_type=op.get("entity_type"),
                        entity_id=op.get("entity_id"),
                    )
                    for op in result.operations
                ],
            )
    except (XlsxCommitConflictFingerprint, XlsxCommitBlockedByIssues) as exc:
        raise _map_error(exc) from exc
    except IngestionError as exc:
        raise _map_error(exc) from exc


# ---------------------------------------------------------------------------
# J3-I7 — Metrics routes
# ---------------------------------------------------------------------------


@router.get(
    "/metrics/adapter/{adapter_id}/{adapter_version}",
    response_model=AdapterMetricsSummaryOut,
)
def get_adapter_metrics(
    adapter_id: str,
    adapter_version: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna métricas agregadas por adapter+version."""
    enforce_permission(user, "ingestion:read")
    summary = ingestion_metrics_commands.get_adapter_metrics(db, adapter_id, adapter_version)
    return AdapterMetricsSummaryOut(
        adapter_id=summary.adapter_id,
        adapter_version=summary.adapter_version,
        total_runs=summary.total_runs,
        classified_count=summary.classified_count,
        classification_rate=summary.classification_rate,
        avg_field_count=summary.avg_field_count,
        avg_issue_count=summary.avg_issue_count,
        total_corrections=summary.total_corrections,
        total_commits=summary.total_commits,
        total_retries=summary.total_retries,
        commit_success_count=summary.commit_success_count,
        commit_partial_count=summary.commit_partial_count,
        commit_failed_count=summary.commit_failed_count,
        avg_matched_lines=summary.avg_matched_lines,
    )


@router.get(
    "/metrics/events",
    response_model=list[MetricEventOut],
)
def list_metric_events(
    adapter_id: str | None = None,
    adapter_version: str | None = None,
    event_type: str | None = None,
    document_id: int | None = None,
    limit: int = 100,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista eventos de métricas com filtros opcionais."""
    enforce_permission(user, "ingestion:read")
    events = ingestion_metrics_commands.list_metric_events(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type=event_type,
        document_id=document_id,
        limit=min(limit, 500),
    )
    return [
        MetricEventOut(
            id=ev.id,
            adapter_id=ev.adapter_id,
            adapter_version=ev.adapter_version,
            event_type=ev.event_type,
            document_id=ev.document_id,
            occurrence_id=ev.occurrence_id,
            payload_json=ev.payload_json,
            created_at=ev.created_at,
        )
        for ev in events
    ]
