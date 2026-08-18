"""Print Declaration attach — Elo 7 / DEC-E7-PRINT.

Documents-only: promote PDF, link to ImportProcess, provenance.
Never SoT of qty, tax, or DUIMP. 0/1/N process by invoice_ref.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.billing import public as billing_public
from app.customs import public as customs_public
from app.documents import public as documents_public
from app.ingestion import staging_queries
from app.ingestion import storage as quarantine_storage
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence

DOC_TYPE = "PRINT_DECLARATION"


class PrintCommitBlocked(IngestionError):
    def __init__(self, message: str, *, code: str = "print_commit_blocked"):
        super().__init__(message, code=code)


class PrintConflictFingerprint(IngestionError):
    def __init__(self, op_key: str) -> None:
        super().__init__(
            f"operation_key '{op_key}' já existe com fingerprint diferente",
            code="commit_conflict_fingerprint",
        )


def _field_value(doc, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _record_op(db, attempt, op_key, *, status, entity_type=None, entity_id=None, error_message=None, details_json=None):
    db.add(
        IngestionCommitOperation(
            attempt_id=attempt.id,
            op_key=op_key,
            status=status,
            entity_type=entity_type,
            entity_id=entity_id,
            error_message=error_message,
            details_json=details_json,
        )
    )
    db.flush()


def _last_succeeded(db: Session, document_id: int) -> IngestionCommitAttempt | None:
    row = (
        db.query(IngestionCommitAttempt)
        .filter(
            IngestionCommitAttempt.document_id == document_id,
            IngestionCommitAttempt.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitAttempt.id.desc())
        .first()
    )
    if row is None or getattr(row, "status", None) != "SUCCEEDED":
        return None
    return row


def _process_id_from_attempt(attempt: IngestionCommitAttempt) -> int | None:
    for op in attempt.operations or []:
        if op.entity_type in ("import_process", "process") and op.entity_id:
            try:
                return int(op.entity_id)
            except (TypeError, ValueError):
                continue
    return None


@dataclass
class PrintPreviewOp:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class PrintPreviewResult:
    document_id: int
    fingerprint: str
    operations: list[PrintPreviewOp]
    open_error_count: int
    can_commit: bool
    invoice_ref: str | None = None
    process_targets: list[dict] = field(default_factory=list)
    process_targets_reason: str | None = None
    blockers: list[str] = field(default_factory=list)
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_process_id: int | None = None
    resolved_process_id: int | None = None


def collect_print_process_targets(db: Session, invoice_ref: str | None) -> list[dict]:
    out: list[dict] = []
    seen: set[int] = set()
    if invoice_ref:
        try:
            invoices = billing_public.find_invoices_by_number(db, invoice_ref)
        except Exception:
            invoices = []
        if isinstance(invoices, list):
            for inv in invoices:
                proc = customs_public.find_process_for_invoice(db, inv.id)
                if proc is None or proc.status == "CANCELLED" or proc.id in seen:
                    continue
                seen.add(proc.id)
                out.append(
                    {
                        "process_id": proc.id,
                        "code": proc.code,
                        "status": proc.status,
                        "compatible": True,
                        "evidence": [f"invoice_ref {invoice_ref} → fatura #{inv.id}"],
                    }
                )
    if out:
        return out
    try:
        drafts = list(customs_public.list_import_processes(db, status="DRAFT", limit=20))
        submitted = list(customs_public.list_import_processes(db, status="SUBMITTED", limit=20))
    except Exception:
        return out
    for proc in drafts + submitted:
        if proc.id in seen or proc.status == "CANCELLED":
            continue
        seen.add(proc.id)
        out.append(
            {
                "process_id": proc.id,
                "code": proc.code,
                "status": proc.status,
                "compatible": True,
                "evidence": ["Processo existente — confirme para anexar o Print"],
            }
        )
    return out


def preview_commit_print(
    db: Session,
    document_id: int,
    *,
    process_id: int | None = None,
) -> PrintPreviewResult:
    doc = staging_queries.get_document_detail(db, document_id)
    if (doc.doc_type or "") != DOC_TYPE:
        raise PrintCommitBlocked("Documento não é Print Declaration", code="print_wrong_doc_type")
    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )
    fingerprint = hashlib.sha256(
        json.dumps({"doc_id": document_id, "process_id": process_id}, sort_keys=True).encode()
    ).hexdigest()
    existing = _last_succeeded(db, document_id)
    if existing is not None:
        pid = _process_id_from_attempt(existing)
        return PrintPreviewResult(
            document_id=document_id,
            fingerprint=existing.payload_fingerprint or fingerprint,
            operations=[
                PrintPreviewOp(
                    op.op_key,
                    "Print já anexado a este processo" if op.entity_type in ("import_process", "process") else op.op_key,
                    op.entity_type,
                    {"entity_id": op.entity_id} if op.entity_id else {},
                )
                for op in (existing.operations or [])
            ],
            open_error_count=open_errors,
            can_commit=False,
            invoice_ref=_field_value(doc, "invoice_ref"),
            already_committed=True,
            last_succeeded_attempt_id=existing.id,
            last_succeeded_process_id=pid,
            resolved_process_id=pid,
        )

    invoice_ref = (_field_value(doc, "invoice_ref") or "").strip() or None
    targets = collect_print_process_targets(db, invoice_ref)
    blockers: list[str] = []
    reason = None
    resolved = process_id
    if process_id is not None:
        hit = next((t for t in targets if t["process_id"] == process_id), None)
        if hit is None:
            # allow explicit process even if invoice_ref didn't match — operator confirmed
            try:
                p = customs_public.get_import_process(db, process_id)
                if p.status == "CANCELLED":
                    blockers.append("Processo cancelado")
                    resolved = None
            except customs_public.CustomsError:
                blockers.append(f"Processo #{process_id} não encontrado")
                resolved = None
    elif len(targets) == 1:
        reason = "1 processo ligado à fatura do Print — confirme para anexar. Sem vínculo silencioso."
        blockers.append(reason)
    elif len(targets) > 1:
        reason = f"{len(targets)} processos possíveis — escolha."
        blockers.append(reason)
    else:
        reason = (
            "Nenhum processo com fatura ISSUED igual ao invoice_ref do Print. "
            "Crie/vincule a Doganale antes, ou confirme um processo existente."
        )
        blockers.append(reason)

    if open_errors:
        blockers.append(f"{open_errors} erro(s) em aberto")

    can_commit = open_errors == 0 and process_id is not None and not any(
        b.startswith("Processo") for b in blockers if "não encontrado" in b or "cancelado" in b.lower()
    )
    if process_id is not None and open_errors == 0 and resolved is not None:
        can_commit = True
        blockers = [b for b in blockers if b != reason]

    ops = [
        PrintPreviewOp("store_document", "Promover PDF Print Declaration", "document"),
        PrintPreviewOp(
            "link_print_to_process",
            "Anexar Print ao ImportProcess (Documents only — não é fonte de imposto/qty)",
            "import_process",
        ),
    ]
    return PrintPreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        operations=ops,
        open_error_count=open_errors,
        can_commit=can_commit,
        invoice_ref=invoice_ref,
        process_targets=targets,
        process_targets_reason=reason,
        blockers=blockers,
        resolved_process_id=resolved,
    )


def commit_print(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
    process_id: int | None = None,
) -> IngestionCommitAttempt:
    preview = preview_commit_print(db, document_id, process_id=process_id)
    if preview.already_committed:
        existing = _last_succeeded(db, document_id)
        if existing is not None:
            return existing
    if not preview.can_commit:
        raise PrintCommitBlocked(
            "; ".join(preview.blockers) or "Commit Print bloqueado",
            code="print_commit_blocked",
        )
    if process_id is None:
        raise PrintCommitBlocked("Confirme o processo para anexar o Print", code="print_process_id_required")

    fingerprint = hashlib.sha256(
        json.dumps({"doc_id": document_id, "process_id": process_id}, sort_keys=True).encode()
    ).hexdigest()
    existing_key = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing_key is not None:
        if getattr(existing_key, "payload_fingerprint", None) == fingerprint:
            return existing_key
        raise PrintConflictFingerprint(operation_key)

    doc = staging_queries.get_document_detail(db, document_id)
    attempt = IngestionCommitAttempt(
        document_id=document_id,
        operation_key=operation_key,
        payload_fingerprint=fingerprint,
        status="UNKNOWN",
        actor_id=actor_id,
    )
    db.add(attempt)
    db.flush()

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
                    filename=occ.original_filename or f"print_{document_id}.pdf",
                    content=pdf_bytes,
                    mime_type=occ.detected_mime or "application/pdf",
                )
                promoted_doc_id = promoted.id
        _record_op(
            db, attempt, "store_document", status="SUCCEEDED",
            entity_type="document",
            entity_id=str(promoted_doc_id) if promoted_doc_id else None,
        )
    except Exception as exc:
        _record_op(db, attempt, "store_document", status="FAILED", error_message=str(exc)[:512])
        attempt.status = "FAILED"
        db.flush()
        return attempt

    try:
        process = customs_public.get_import_process(db, process_id)
        if promoted_doc_id:
            documents_public.link_document(
                db,
                document_id=promoted_doc_id,
                entity_type="import_process",
                entity_id=str(process.id),
                role="print_declaration",
            )
        customs_public.attach_provenance(
            db,
            process.id,
            entity_type="import_process",
            entity_id=str(process.id),
            source_kind="PRINT_DECLARATION",
            document_id=promoted_doc_id,
            adapter_key="print_declaration_v1",
            notes=f"invoice_ref={preview.invoice_ref} (WARNING — não é SoT de qty/imposto)",
        )
        _record_op(
            db, attempt, "link_print_to_process", status="SUCCEEDED",
            entity_type="import_process",
            entity_id=str(process.id),
        )
        attempt.status = "SUCCEEDED"
    except Exception as exc:
        _record_op(
            db, attempt, "link_print_to_process", status="FAILED",
            error_message=str(exc)[:512],
        )
        attempt.status = "PARTIAL"

    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_print_completed",
        reason_code="INGEST_PRINT_ATTACH_DONE",
        details=json.dumps({"document_id": document_id, "process_id": process_id, "status": attempt.status}),
    )
    return attempt
