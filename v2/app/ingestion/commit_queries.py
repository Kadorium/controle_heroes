"""Ingestion commit ledger queries — J3-I3."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ingestion.commit_commands import CommitAttemptNotFound
from app.ingestion.commit_models import IngestionCommitAttempt


def get_commit_attempt(db: Session, attempt_id: int) -> IngestionCommitAttempt:
    attempt = db.get(IngestionCommitAttempt, attempt_id)
    if attempt is None:
        raise CommitAttemptNotFound(attempt_id)
    return attempt


def list_commit_attempts_for_document(
    db: Session, document_id: int
) -> list[IngestionCommitAttempt]:
    return (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.document_id == document_id)
        .order_by(IngestionCommitAttempt.id.desc())
        .all()
    )
