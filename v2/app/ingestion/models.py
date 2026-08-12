"""Ingestion domain models — J3-I0 foundation (Batch / Blob / Occurrence)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

BATCH_STATUSES = ("OPEN", "CLOSED")
BLOB_PHYSICAL_STATUSES = ("PRESENT", "PURGED")
OCCURRENCE_STATUSES = (
    "RECEIVED",
    "VALIDATING",
    "STORED",
    "REJECTED",
    "FAILED",
    "ABANDONED",
)
TERMINAL_PURGE_ELIGIBLE = frozenset({"REJECTED", "ABANDONED", "FAILED"})
ACTIVE_CONTENT_STATUSES = frozenset({"RECEIVED", "VALIDATING", "STORED"})


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'CLOSED')",
            name="ck_ingestion_batches_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    created_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    occurrences: Mapped[list["IngestionOccurrence"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class IngestionBlob(Base):
    __tablename__ = "ingestion_blobs"
    __table_args__ = (
        CheckConstraint(
            "physical_status IN ('PRESENT', 'PURGED')",
            name="ck_ingestion_blobs_physical_status",
        ),
        UniqueConstraint("sha256", name="uq_ingestion_blobs_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detected_mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    physical_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PRESENT", index=True
    )
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    occurrences: Mapped[list["IngestionOccurrence"]] = relationship(back_populates="blob")


class IngestionOccurrence(Base):
    __tablename__ = "ingestion_occurrences"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'RECEIVED', 'VALIDATING', 'STORED', 'REJECTED', 'FAILED', 'ABANDONED'"
            ")",
            name="ck_ingestion_occurrences_status",
        ),
        Index(
            "uq_ingestion_occurrences_batch_client_key",
            "batch_id",
            "client_upload_key",
            unique=True,
            postgresql_where=text("client_upload_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingestion_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    blob_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingestion_blobs.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RECEIVED", index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    declared_mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detected_mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    client_upload_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    physical_reuse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rehydrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bytes_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    batch: Mapped[IngestionBatch] = relationship(back_populates="occurrences")
    blob: Mapped[IngestionBlob | None] = relationship(back_populates="occurrences")
