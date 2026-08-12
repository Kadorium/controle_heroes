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
