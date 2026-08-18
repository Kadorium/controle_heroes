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
                    description=f"Criar Shipment PLANNED via logistics.create_shipment (PL {doc_num}, modal nulo)",
                    entity_type="shipment",
                    params={"modal": None, "pl_document_id": doc.id, "doc_number": doc_num},
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
    order_id: int | None = None,
    shipment_id: int | None = None,
    line_choices: list | None = None,
) -> IngestionCommitAttempt:
    """Commit PL Detail: orquestra Logistics via packing_commit_commands (C6)."""
    from app.ingestion.packing_commit_commands import commit_pl_detail as _commit

    return _commit(
        db,
        document_id=document_id,
        operation_key=operation_key,
        actor_id=actor_id,
        attachments_path=attachments_path,
        quarantine_path=quarantine_path,
        order_id=order_id,
        shipment_id=shipment_id,
        line_choices=line_choices,
    )


def commit_doganale(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
    process_id: int | None = None,
    invoice_id: int | None = None,
    shipment_id: int | None = None,
) -> IngestionCommitAttempt:
    """Commit Fattura Doganale: preenche CustomsDoganale via doganale_commit_commands."""
    from app.ingestion.doganale_commit_commands import commit_doganale as _commit

    return _commit(
        db,
        document_id=document_id,
        operation_key=operation_key,
        actor_id=actor_id,
        attachments_path=attachments_path,
        quarantine_path=quarantine_path,
        process_id=process_id,
        invoice_id=invoice_id,
        shipment_id=shipment_id,
    )
