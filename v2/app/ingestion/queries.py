"""Queries Ingestion I0."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.ingestion.errors import BatchNotFound, OccurrenceNotFound
from app.ingestion.models import IngestionBatch, IngestionOccurrence


def get_batch_with_occurrences(db: Session, batch_id: int) -> IngestionBatch:
    batch = (
        db.query(IngestionBatch)
        .options(joinedload(IngestionBatch.occurrences).joinedload(IngestionOccurrence.blob))
        .filter(IngestionBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise BatchNotFound(batch_id)
    return batch


def get_occurrence_detail(db: Session, occurrence_id: int) -> IngestionOccurrence:
    occ = (
        db.query(IngestionOccurrence)
        .options(joinedload(IngestionOccurrence.blob))
        .filter(IngestionOccurrence.id == occurrence_id)
        .first()
    )
    if not occ:
        raise OccurrenceNotFound(occurrence_id)
    return occ


def exceptions(db: Session, *, limit: int = 20) -> list[dict]:
    """Falhas globais (FAILED/REJECTED/PARTIAL/ERROR) — não é a fila de revisão."""
    from app.ingestion.commit_models import IngestionCommitAttempt
    from app.ingestion.ir_models import IngestionIssue
    from app.ingestion.models import IngestionOccurrence

    out: list[dict] = []
    occs = (
        db.query(IngestionOccurrence)
        .filter(IngestionOccurrence.status.in_(("FAILED", "REJECTED")))
        .order_by(IngestionOccurrence.updated_at.desc())
        .limit(limit)
        .all()
    )
    for occ in occs:
        out.append(
            {
                "kind": "ingestion_failed",
                "severity": "blocker",
                "title": occ.original_filename or f"Arquivo {occ.id}",
                "reason": occ.rejection_reason or occ.status,
                "entity_id": occ.id,
                "href": f"/ingestion/occurrences/{occ.id}",
                "since": occ.updated_at.isoformat() if occ.updated_at else None,
                "module": "ingestion",
            }
        )
    attempts = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.status.in_(("FAILED", "PARTIAL")))
        .order_by(IngestionCommitAttempt.updated_at.desc())
        .limit(limit)
        .all()
    )
    for att in attempts:
        out.append(
            {
                "kind": "ingestion_commit_failed",
                "severity": "blocker",
                "title": f"Commit {att.operation_key}",
                "reason": att.status,
                "entity_id": att.document_id,
                "href": f"/ingestion/documents/{att.document_id}",
                "since": att.updated_at.isoformat() if att.updated_at else None,
                "module": "ingestion",
            }
        )
    issues = (
        db.query(IngestionIssue)
        .filter(IngestionIssue.severity == "ERROR", IngestionIssue.status == "OPEN")
        .order_by(IngestionIssue.created_at.desc())
        .limit(limit)
        .all()
    )
    for iss in issues:
        out.append(
            {
                "kind": "ingestion_issue",
                "severity": "blocker",
                "title": iss.code,
                "reason": iss.message,
                "entity_id": iss.document_id,
                "href": f"/ingestion/documents/{iss.document_id}",
                "since": iss.created_at.isoformat() if iss.created_at else None,
                "module": "ingestion",
            }
        )
    out.sort(key=lambda r: r.get("since") or "", reverse=True)
    return out[:limit]
