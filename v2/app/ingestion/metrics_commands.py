"""Ingestion metrics commands + queries — J3-I7.

Records metric events per adapter+version and provides queryable aggregates.
Prefer to call record_* after a successful operation in the same UoW.

Queryable via:
- get_adapter_metrics(db, adapter_id, adapter_version) → AdapterMetricsSummary
- list_metric_events(db, adapter_id, ...) → raw events

NEVER blocks the operation if metrics recording fails (best-effort).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.metrics_models import IngestionMetricEvent, METRIC_EVENT_TYPES


# ---------------------------------------------------------------------------
# Errors (non-blocking by design; callers should catch and continue)
# ---------------------------------------------------------------------------


class MetricsError(Exception):
    pass


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------


def _record(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    event_type: str,
    document_id: int | None = None,
    occurrence_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> IngestionMetricEvent:
    if event_type not in METRIC_EVENT_TYPES:
        raise MetricsError(f"Unknown event_type: {event_type}")
    event = IngestionMetricEvent(
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type=event_type,
        document_id=document_id,
        occurrence_id=occurrence_id,
        payload_json=json.dumps(payload, default=str) if payload else None,
    )
    db.add(event)
    db.flush()
    return event


def record_adapter_run(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    document_id: int | None = None,
    occurrence_id: int | None = None,
    field_count: int = 0,
    row_count: int = 0,
    issue_count: int = 0,
    error_count: int = 0,
    warn_count: int = 0,
    processing_time_ms: float | None = None,
    classified: bool = True,
) -> IngestionMetricEvent:
    return _record(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type="ADAPTER_RUN",
        document_id=document_id,
        occurrence_id=occurrence_id,
        payload={
            "field_count": field_count,
            "row_count": row_count,
            "issue_count": issue_count,
            "error_count": error_count,
            "warn_count": warn_count,
            "processing_time_ms": processing_time_ms,
            "classified": classified,
        },
    )


def record_matching_result(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    document_id: int | None = None,
    matched_lines: int = 0,
    ambiguous_lines: int = 0,
    unmatched_lines: int = 0,
    supplier_found: bool = False,
) -> IngestionMetricEvent:
    return _record(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type="MATCHING_RESULT",
        document_id=document_id,
        payload={
            "matched_lines": matched_lines,
            "ambiguous_lines": ambiguous_lines,
            "unmatched_lines": unmatched_lines,
            "supplier_found": supplier_found,
            "total_lines": matched_lines + ambiguous_lines + unmatched_lines,
        },
    )


def record_commit_attempt(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    document_id: int | None = None,
    is_retry: bool = False,
) -> IngestionMetricEvent:
    event_type = "RETRY" if is_retry else "COMMIT_ATTEMPT"
    return _record(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type=event_type,
        document_id=document_id,
        payload={"is_retry": is_retry},
    )


def record_commit_complete(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    document_id: int | None = None,
    status: str,
    op_count: int = 0,
    failed_ops: int = 0,
) -> IngestionMetricEvent:
    return _record(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type="COMMIT_COMPLETE",
        document_id=document_id,
        payload={"status": status, "op_count": op_count, "failed_ops": failed_ops},
    )


def record_field_corrected(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    document_id: int | None = None,
    field_key: str | None = None,
) -> IngestionMetricEvent:
    return _record(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type="FIELD_CORRECTED",
        document_id=document_id,
        payload={"field_key": field_key},
    )


def record_review_complete(
    db: Session,
    *,
    adapter_id: str,
    adapter_version: str,
    document_id: int | None = None,
    corrections_count: int = 0,
    final_status: str = "READY",
) -> IngestionMetricEvent:
    return _record(
        db,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        event_type="REVIEW_COMPLETE",
        document_id=document_id,
        payload={"corrections_count": corrections_count, "final_status": final_status},
    )


# ---------------------------------------------------------------------------
# Aggregated metrics summary
# ---------------------------------------------------------------------------


@dataclass
class AdapterMetricsSummary:
    adapter_id: str
    adapter_version: str
    total_runs: int = 0
    classified_count: int = 0
    classification_rate: float = 0.0
    avg_field_count: float = 0.0
    avg_issue_count: float = 0.0
    total_corrections: int = 0
    total_commits: int = 0
    total_retries: int = 0
    commit_success_count: int = 0
    commit_partial_count: int = 0
    commit_failed_count: int = 0
    avg_matched_lines: float = 0.0
    raw_events: list[dict] = field(default_factory=list)


def get_adapter_metrics(
    db: Session,
    adapter_id: str,
    adapter_version: str,
    *,
    include_raw: bool = False,
    limit: int = 1000,
) -> AdapterMetricsSummary:
    """Aggregate metrics for a given adapter+version from the event log."""
    q = (
        db.query(IngestionMetricEvent)
        .filter(
            IngestionMetricEvent.adapter_id == adapter_id,
            IngestionMetricEvent.adapter_version == adapter_version,
        )
        .order_by(IngestionMetricEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    summary = AdapterMetricsSummary(adapter_id=adapter_id, adapter_version=adapter_version)

    total_field_count = 0
    total_issue_count = 0
    total_matched = 0
    matching_events = 0

    for ev in q:
        payload = json.loads(ev.payload_json) if ev.payload_json else {}
        if ev.event_type == "ADAPTER_RUN":
            summary.total_runs += 1
            if payload.get("classified", True):
                summary.classified_count += 1
            total_field_count += payload.get("field_count", 0)
            total_issue_count += payload.get("issue_count", 0)
        elif ev.event_type in ("COMMIT_ATTEMPT", "RETRY"):
            if ev.event_type == "RETRY":
                summary.total_retries += 1
            else:
                summary.total_commits += 1
        elif ev.event_type == "COMMIT_COMPLETE":
            status = payload.get("status", "")
            if status == "SUCCEEDED":
                summary.commit_success_count += 1
            elif status == "PARTIAL":
                summary.commit_partial_count += 1
            elif status == "FAILED":
                summary.commit_failed_count += 1
        elif ev.event_type == "FIELD_CORRECTED":
            summary.total_corrections += 1
        elif ev.event_type == "MATCHING_RESULT":
            matching_events += 1
            total_matched += payload.get("matched_lines", 0)

        if include_raw:
            summary.raw_events.append(
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "document_id": ev.document_id,
                    "occurrence_id": ev.occurrence_id,
                    "payload": payload,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
            )

    if summary.total_runs > 0:
        summary.classification_rate = summary.classified_count / summary.total_runs
        summary.avg_field_count = total_field_count / summary.total_runs
        summary.avg_issue_count = total_issue_count / summary.total_runs
    if matching_events > 0:
        summary.avg_matched_lines = total_matched / matching_events

    return summary


def list_metric_events(
    db: Session,
    *,
    adapter_id: str | None = None,
    adapter_version: str | None = None,
    event_type: str | None = None,
    document_id: int | None = None,
    limit: int = 100,
) -> list[IngestionMetricEvent]:
    q = db.query(IngestionMetricEvent)
    if adapter_id:
        q = q.filter(IngestionMetricEvent.adapter_id == adapter_id)
    if adapter_version:
        q = q.filter(IngestionMetricEvent.adapter_version == adapter_version)
    if event_type:
        q = q.filter(IngestionMetricEvent.event_type == event_type)
    if document_id is not None:
        q = q.filter(IngestionMetricEvent.document_id == document_id)
    return q.order_by(IngestionMetricEvent.created_at.desc()).limit(limit).all()
