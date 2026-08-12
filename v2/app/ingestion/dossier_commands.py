"""Dossier commands — J3-I5.

Constrói DocumentSet para dossiê de ingestão 202 (ou qualquer batch).
Comandos opcionais de commit que criam entidades downstream via APIs públicas:
- PL Detail commit → Logistics Shipment PLANNED
- Fattura Doganale commit → Customs ImportProcess DRAFT

Regras:
- Sem Payment; sem bypass de auth
- Logistics/Customs criados via public APIs somente
- Preview disponível sem escrever owners
- Commit é explícito e idempotente via IngestionCommitAttempt
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.customs import public as customs_public
from app.documents import public as documents_public
from app.ingestion import staging_commands
from app.ingestion import staging_queries
from app.ingestion import storage as quarantine_storage
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.ingestion.reconciler import reconcile_document_set
from app.logistics import public as logistics_public

DOC_TYPE_PL_DETAIL = "PACKING_LIST_DETAIL"
DOC_TYPE_DOGANALE = "FATTURA_DOGANALE"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DossierConflictFingerprint(IngestionError):
    def __init__(self, op_key: str) -> None:
        super().__init__(
            f"operation_key '{op_key}' já existe com fingerprint diferente",
            code="commit_conflict_fingerprint",
        )


class DossierCommitBlockedByIssues(IngestionError):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} issue(s) OPEN ERROR bloqueiam o commit do dossier",
            code="commit_blocked_by_issues",
        )


# ---------------------------------------------------------------------------
# Reconcile and persist issues
# ---------------------------------------------------------------------------


def reconcile_and_persist(
    db: Session,
    *,
    document_set_id: int,
    actor_id: str,
) -> list[dict]:
    """Run reconciler and persist issues to each involved document.

    Returns list of issue dicts created.
    """
    recon_issues = reconcile_document_set(db, document_set_id)
    persisted: list[dict] = []

    docs_in_set = staging_queries.list_documents_for_set(db, document_set_id)
    doc_map = {d.doc_type: d for d in docs_in_set}

    for ri in recon_issues:
        # Attach to first involved document found
        target_doc = None
        for dt in ri.doc_types_involved:
            if dt in doc_map:
                target_doc = doc_map[dt]
                break

        if target_doc is None and docs_in_set:
            target_doc = docs_in_set[0]

        if target_doc is None:
            continue

        issue = staging_commands.create_issue(
            db,
            document_id=target_doc.id,
            actor_id=actor_id,
            severity=ri.severity,
            code=ri.code,
            message=ri.message,
            target_type="DOCUMENT",
            target_id=None,
            locator_json=json.dumps({"reconciliation": True, "docs": ri.doc_types_involved}),
        )
        db.flush()
        persisted.append(
            {
                "issue_id": issue.id,
                "document_id": target_doc.id,
                "doc_type": target_doc.doc_type,
                "code": ri.code,
                "severity": ri.severity,
            }
        )

    return persisted


# ---------------------------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------------------------


@dataclass
class DossierPreviewItem:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class DossierPreviewResult:
    document_set_id: int
    documents_found: list[str]
    reconciliation_issues: list[dict]
    planned_operations: list[DossierPreviewItem]
    can_commit: bool


def preview_dossier(
    db: Session,
    document_set_id: int,
) -> DossierPreviewResult:
    """Compute what a dossier commit would do — no writes."""
    docs = staging_queries.list_documents_for_set(db, document_set_id)
    doc_types = [d.doc_type for d in docs]

    # Reconcile (read-only, not persisted)
    recon_issues = reconcile_document_set(db, document_set_id)
    recon_dicts = [
        {
            "code": ri.code,
            "severity": ri.severity,
            "message": ri.message,
            "doc_types": ri.doc_types_involved,
        }
        for ri in recon_issues
    ]

    error_count = sum(1 for r in recon_issues if r.severity == "ERROR")

    planned_ops: list[DossierPreviewItem] = []

    # Check if PL Detail is present → would create Shipment PLANNED
    for doc in docs:
        if doc.doc_type == DOC_TYPE_PL_DETAIL:
            doc_num = None
            for f in doc.fields or []:
                if f.field_key == "document_number":
                    doc_num = f.normalized_value or f.raw_value
                    break
            planned_ops.append(
                DossierPreviewItem(
                    op_key="create_shipment_planned",
                    description=f"Criar Shipment PLANNED via logistics.create_shipment (PL {doc_num})",
                    entity_type="shipment",
                    params={"modal": "MARITIME", "pl_document_id": doc.id, "doc_number": doc_num},
                )
            )

        if doc.doc_type == DOC_TYPE_DOGANALE:
            dog_num = None
            for f in doc.fields or []:
                if f.field_key == "document_number":
                    dog_num = f.normalized_value or f.raw_value
                    break
            planned_ops.append(
                DossierPreviewItem(
                    op_key="create_import_process_draft",
                    description=f"Criar ImportProcess DRAFT via customs.create_import_process (Doganale {dog_num})",
                    entity_type="import_process",
                    params={"doganale_document_id": doc.id, "external_ref": dog_num},
                )
            )

    can_commit = error_count == 0

    return DossierPreviewResult(
        document_set_id=document_set_id,
        documents_found=doc_types,
        reconciliation_issues=recon_dicts,
        planned_operations=planned_ops,
        can_commit=can_commit,
    )


# ---------------------------------------------------------------------------
# Commit (optional — creates Shipment/ImportProcess when applicable)
# ---------------------------------------------------------------------------


def _get_field_value(doc, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _record_op(
    db: Session,
    attempt: IngestionCommitAttempt,
    op_key: str,
    *,
    status: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    error_message: str | None = None,
    details_json: str | None = None,
) -> None:
    op = IngestionCommitOperation(
        attempt_id=attempt.id,
        op_key=op_key,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        error_message=error_message,
        details_json=details_json,
    )
    db.add(op)
    db.flush()


def commit_pl_detail(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
) -> IngestionCommitAttempt:
    """Commit PL Detail: promote document + create Logistics Shipment PLANNED."""
    import hashlib

    doc = staging_queries.get_document_detail(db, document_id)

    open_errors = [i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"]
    if open_errors:
        raise DossierCommitBlockedByIssues(len(open_errors))

    # Fingerprint
    canonical = json.dumps(
        {"doc_id": document_id, "doc_type": doc.doc_type, "adapter": doc.adapter_id},
        sort_keys=True,
    )
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()

    existing = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing is not None:
        if existing.payload_fingerprint == fingerprint:
            return existing
        raise DossierConflictFingerprint(operation_key)

    attempt = IngestionCommitAttempt(
        document_id=document_id,
        operation_key=operation_key,
        payload_fingerprint=fingerprint,
        status="UNKNOWN",
        actor_id=actor_id,
    )
    db.add(attempt)
    db.flush()

    succeeded: list[str] = []
    failed: list[str] = []

    # Op 1: store_document
    promoted_doc_id: int | None = None
    try:
        occ = db.get(IngestionOccurrence, doc.occurrence_id)
        if occ and occ.blob and occ.blob.physical_status == "PRESENT" and occ.blob.storage_path:
            blob_path = quarantine_storage.resolve_quarantine_path(
                quarantine_path, occ.blob.storage_path
            )
            if blob_path and blob_path.is_file():
                pdf_bytes = blob_path.read_bytes()
                promoted = documents_public.store_document(
                    db,
                    attachments_path=attachments_path,
                    actor_id=actor_id,
                    filename=occ.original_filename or f"pl_{document_id}.pdf",
                    content=pdf_bytes,
                    mime_type=occ.detected_mime or "application/pdf",
                )
                promoted_doc_id = promoted.id
        _record_op(
            db, attempt, "store_document",
            status="SUCCEEDED",
            entity_type="document",
            entity_id=str(promoted_doc_id) if promoted_doc_id else None,
        )
        succeeded.append("store_document")
    except Exception as exc:
        _record_op(db, attempt, "store_document", status="FAILED", error_message=str(exc)[:512])
        failed.append("store_document")
        attempt.status = "FAILED"
        db.flush()
        return attempt

    # Op 2: create_shipment PLANNED via logistics public API
    try:
        doc_num = _get_field_value(doc, "document_number")
        shipment = logistics_public.create_shipment(
            db,
            modal="MARITIME",
            notes=f"Criado via ingestão PL Detail — documento IR {document_id} ref={doc_num}",
        )
        _record_op(
            db, attempt, "create_shipment_planned",
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
            details_json=json.dumps({"shipment_code": shipment.code, "status": shipment.status}),
        )
        succeeded.append("create_shipment_planned")

        # Link document to shipment
        if promoted_doc_id:
            try:
                documents_public.link_document(
                    db,
                    document_id=promoted_doc_id,
                    entity_type="shipment",
                    entity_id=str(shipment.id),
                    role="packing_list",
                )
            except Exception:
                pass  # link failure is non-fatal

    except Exception as exc:
        _record_op(
            db, attempt, "create_shipment_planned",
            status="FAILED",
            error_message=str(exc)[:512],
        )
        failed.append("create_shipment_planned")

    attempt.status = "PARTIAL" if failed else "SUCCEEDED"
    db.flush()

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_pl_detail_completed",
        reason_code="INGEST_PL_COMMIT_DONE",
        details=json.dumps(
            {"document_id": document_id, "status": attempt.status, "succeeded": succeeded, "failed": failed}
        ),
    )
    return attempt


def commit_doganale(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
) -> IngestionCommitAttempt:
    """Commit Fattura Doganale: promote document + create Customs ImportProcess DRAFT."""
    import hashlib

    doc = staging_queries.get_document_detail(db, document_id)

    open_errors = [i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"]
    if open_errors:
        raise DossierCommitBlockedByIssues(len(open_errors))

    canonical = json.dumps(
        {"doc_id": document_id, "doc_type": doc.doc_type, "adapter": doc.adapter_id},
        sort_keys=True,
    )
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()

    existing = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing is not None:
        if existing.payload_fingerprint == fingerprint:
            return existing
        raise DossierConflictFingerprint(operation_key)

    attempt = IngestionCommitAttempt(
        document_id=document_id,
        operation_key=operation_key,
        payload_fingerprint=fingerprint,
        status="UNKNOWN",
        actor_id=actor_id,
    )
    db.add(attempt)
    db.flush()

    succeeded: list[str] = []
    failed: list[str] = []

    # Op 1: store_document
    promoted_doc_id: int | None = None
    try:
        occ = db.get(IngestionOccurrence, doc.occurrence_id)
        if occ and occ.blob and occ.blob.physical_status == "PRESENT" and occ.blob.storage_path:
            blob_path = quarantine_storage.resolve_quarantine_path(
                quarantine_path, occ.blob.storage_path
            )
            if blob_path and blob_path.is_file():
                pdf_bytes = blob_path.read_bytes()
                promoted = documents_public.store_document(
                    db,
                    attachments_path=attachments_path,
                    actor_id=actor_id,
                    filename=occ.original_filename or f"doganale_{document_id}.pdf",
                    content=pdf_bytes,
                    mime_type=occ.detected_mime or "application/pdf",
                )
                promoted_doc_id = promoted.id
        _record_op(
            db, attempt, "store_document",
            status="SUCCEEDED",
            entity_type="document",
            entity_id=str(promoted_doc_id) if promoted_doc_id else None,
        )
        succeeded.append("store_document")
    except Exception as exc:
        _record_op(db, attempt, "store_document", status="FAILED", error_message=str(exc)[:512])
        failed.append("store_document")
        attempt.status = "FAILED"
        db.flush()
        return attempt

    # Op 2: create ImportProcess DRAFT via customs public API
    try:
        doc_num = _get_field_value(doc, "document_number")
        process = customs_public.create_import_process(
            db,
            external_reference=f"ING-DOGANALE-{doc_num or document_id}",
            notes=f"Criado via ingestão Fattura Doganale — documento IR {document_id} ref={doc_num}",
        )
        _record_op(
            db, attempt, "create_import_process_draft",
            status="SUCCEEDED",
            entity_type="import_process",
            entity_id=str(process.id),
            details_json=json.dumps({"process_code": process.code, "status": process.status}),
        )
        succeeded.append("create_import_process_draft")

        # Link document to import process
        if promoted_doc_id:
            try:
                documents_public.link_document(
                    db,
                    document_id=promoted_doc_id,
                    entity_type="import_process",
                    entity_id=str(process.id),
                    role="fattura_doganale",
                )
            except Exception:
                pass

    except Exception as exc:
        _record_op(
            db, attempt, "create_import_process_draft",
            status="FAILED",
            error_message=str(exc)[:512],
        )
        failed.append("create_import_process_draft")

    attempt.status = "PARTIAL" if failed else "SUCCEEDED"
    db.flush()

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_doganale_completed",
        reason_code="INGEST_DOGANALE_COMMIT_DONE",
        details=json.dumps(
            {"document_id": document_id, "status": attempt.status, "succeeded": succeeded, "failed": failed}
        ),
    )
    return attempt
