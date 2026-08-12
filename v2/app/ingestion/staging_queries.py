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
