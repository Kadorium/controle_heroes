"""Ingestion commit ledger models — J3-I3.

IngestionCommitAttempt: tracks idempotent commit attempt per operation_key.
IngestionCommitOperation: individual operation steps within an attempt.

Idempotency:
- Same operation_key + same fingerprint → return existing attempt (200/202).
- Same operation_key + different fingerprint → 409 ConflictFingerprint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

COMMIT_ATTEMPT_STATUSES = ("SUCCEEDED", "PARTIAL", "FAILED", "UNKNOWN")
COMMIT_OPERATION_STATUSES = ("SUCCEEDED", "FAILED", "UNKNOWN", "SKIPPED")


class IngestionCommitAttempt(Base):
    __tablename__ = "ingestion_commit_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCEEDED', 'PARTIAL', 'FAILED', 'UNKNOWN')",
            name="ck_ingestion_commit_attempts_status",
        ),
        UniqueConstraint("operation_key", name="uq_ingestion_commit_attempts_opkey"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    operation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="UNKNOWN", index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    operations: Mapped[list["IngestionCommitOperation"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class IngestionCommitOperation(Base):
    __tablename__ = "ingestion_commit_operations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCEEDED', 'FAILED', 'UNKNOWN', 'SKIPPED')",
            name="ck_ingestion_commit_operations_status",
        ),
        UniqueConstraint(
            "attempt_id", "op_key", name="uq_ingestion_commit_operations_attempt_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_commit_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    op_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped[IngestionCommitAttempt] = relationship(back_populates="operations")
