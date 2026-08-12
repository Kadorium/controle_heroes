"""Ingestion metrics models — J3-I7.

IngestionMetricEvent: minimal event log for per-adapter+version metrics.
Event types: ADAPTER_RUN, COMMIT_ATTEMPT, COMMIT_COMPLETE, FIELD_CORRECTED,
             MATCHING_RESULT, REVIEW_COMPLETE, RETRY.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.foundation.database import Base

METRIC_EVENT_TYPES = (
    "ADAPTER_RUN",
    "COMMIT_ATTEMPT",
    "COMMIT_COMPLETE",
    "FIELD_CORRECTED",
    "MATCHING_RESULT",
    "REVIEW_COMPLETE",
    "RETRY",
)


class IngestionMetricEvent(Base):
    """Append-only event log — one row per metric event.

    payload_json stores event-specific data (field_count, issue_count, status, etc.).
    """

    __tablename__ = "ingestion_metric_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'ADAPTER_RUN','COMMIT_ATTEMPT','COMMIT_COMPLETE',"
            "'FIELD_CORRECTED','MATCHING_RESULT','REVIEW_COMPLETE','RETRY'"
            ")",
            name="ck_ingestion_metric_events_event_type",
        ),
        Index("ix_ingestion_metric_events_adapter", "adapter_id", "adapter_version"),
        Index("ix_ingestion_metric_events_event_type", "event_type"),
        Index("ix_ingestion_metric_events_document_id", "document_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    adapter_id: Mapped[str] = mapped_column(String(128), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    occurrence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
