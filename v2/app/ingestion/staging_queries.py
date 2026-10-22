"""Staging IR queries — J3-I1."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.ingestion.errors import DocumentNotFound, DocumentSetNotFound, FieldNotFound, RowNotFound
from app.ingestion.ir_models import (
    IngestionDocument,
    IngestionDocumentSet,
    IngestionField,
    IngestionReviewChange,
    IngestionRow,
)


def get_document_detail(db: Session, document_id: int) -> IngestionDocument:
    doc = (
        db.query(IngestionDocument)
        .options(
            joinedload(IngestionDocument.sections),
            joinedload(IngestionDocument.fields),
            joinedload(IngestionDocument.rows),
            joinedload(IngestionDocument.issues),
        )
        .filter(IngestionDocument.id == document_id)
        .first()
    )
    if doc is None:
        raise DocumentNotFound(document_id)
    return doc


def list_documents_for_batch(db: Session, batch_id: int) -> list[IngestionDocument]:
    return (
        db.query(IngestionDocument)
        .filter(IngestionDocument.batch_id == batch_id)
        .order_by(IngestionDocument.id.asc())
        .all()
    )


def get_field(db: Session, field_id: int) -> IngestionField:
    field = db.get(IngestionField, field_id)
    if field is None:
        raise FieldNotFound(field_id)
    return field


def get_row(db: Session, row_id: int) -> IngestionRow:
    row = db.get(IngestionRow, row_id)
    if row is None:
        raise RowNotFound(row_id)
    return row


def list_review_changes(db: Session, document_id: int) -> list[IngestionReviewChange]:
    _ = get_document_detail(db, document_id)
    return (
        db.query(IngestionReviewChange)
        .filter(IngestionReviewChange.document_id == document_id)
        .order_by(IngestionReviewChange.id.asc())
        .all()
    )


def get_document_set(db: Session, set_id: int) -> IngestionDocumentSet:
    ds = (
        db.query(IngestionDocumentSet)
        .options(joinedload(IngestionDocumentSet.members))
        .filter(IngestionDocumentSet.id == set_id)
        .first()
    )
    if ds is None:
        raise DocumentSetNotFound(set_id)
    return ds


def list_documents_for_set(db: Session, document_set_id: int) -> list[IngestionDocument]:
    """List all IngestionDocuments belonging to a DocumentSet (via members)."""
    from app.ingestion.ir_models import IngestionDocumentSetMember

    member_doc_ids = (
        db.query(IngestionDocumentSetMember.document_id)
        .filter(IngestionDocumentSetMember.document_set_id == document_set_id)
        .all()
    )
    if not member_doc_ids:
        return []
    ids = [r[0] for r in member_doc_ids]
    return (
        db.query(IngestionDocument)
        .options(
            joinedload(IngestionDocument.sections),
            joinedload(IngestionDocument.fields),
            joinedload(IngestionDocument.rows),
            joinedload(IngestionDocument.issues),
        )
        .filter(IngestionDocument.id.in_(ids))
        .order_by(IngestionDocument.id.asc())
        .all()
    )


def staging_queue(
    db: Session,
    *,
    review_status: str | None = None,
    limit: int = 100,
) -> list[IngestionDocument]:
    q = db.query(IngestionDocument)
    if review_status:
        q = q.filter(IngestionDocument.review_status == review_status)
    return q.order_by(IngestionDocument.updated_at.desc()).limit(limit).all()


def staging_queue_summary(db: Session) -> dict:
    from datetime import datetime, timezone

    from sqlalchemy import func

    open_status = ("DRAFT", "IN_REVIEW")
    rows = (
        db.query(
            IngestionDocument.doc_type,
            func.count(IngestionDocument.id),
            func.min(IngestionDocument.updated_at),
        )
        .filter(IngestionDocument.review_status.in_(open_status))
        .group_by(IngestionDocument.doc_type)
        .all()
    )
    now = datetime.now(timezone.utc)
    families = []
    total = 0
    oldest = None
    for doc_type, cnt, oldest_at in rows:
        total += int(cnt or 0)
        age_hours = None
        if oldest_at is not None:
            ts = oldest_at if oldest_at.tzinfo else oldest_at.replace(tzinfo=timezone.utc)
            age_hours = max(0, int((now - ts).total_seconds() // 3600))
            if oldest is None or ts < oldest:
                oldest = ts
        families.append(
            {
                "doc_type": doc_type,
                "count": int(cnt or 0),
                "oldest_updated_at": oldest_at.isoformat() if oldest_at else None,
                "age_hours": age_hours,
            }
        )
    return {
        "total_open": total,
        "families": sorted(families, key=lambda r: r["doc_type"]),
        "oldest_updated_at": oldest.isoformat() if oldest else None,
    }


def review_exceptions(db: Session, *, limit: int = 20) -> list[dict]:
    docs = staging_queue(db, review_status="IN_REVIEW", limit=limit)
    if len(docs) < limit:
        extra = staging_queue(db, review_status="DRAFT", limit=limit)
        seen = {d.id for d in docs}
        docs = list(docs) + [d for d in extra if d.id not in seen]
    out = []
    for doc in docs[:limit]:
        out.append(
            {
                "kind": "ingestion_review",
                "severity": "warning",
                "title": f"{doc.doc_type} #{doc.id}",
                "reason": "Documento aguardando revisão",
                "entity_id": doc.id,
                "href": f"/ingestion/documents/{doc.id}",
                "since": doc.updated_at.isoformat() if doc.updated_at else None,
                "module": "ingestion",
            }
        )
    return out
