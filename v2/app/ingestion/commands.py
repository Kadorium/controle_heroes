"""Commands Ingestion I0 — batch, upload, abandon, purge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.ingestion.errors import (
    BatchClosed,
    BatchNotFound,
    IdempotencyConflict,
    InvalidTransition,
    OccurrenceNotFound,
    RequestLimitExceeded,
)
from app.ingestion.limits import IngestionLimits, limits_from_mapping
from app.ingestion.models import (
    ACTIVE_CONTENT_STATUSES,
    TERMINAL_PURGE_ELIGIBLE,
    IngestionBatch,
    IngestionBlob,
    IngestionOccurrence,
)
from app.ingestion import storage as quarantine_storage
from app.ingestion.validation import sanitize_original_filename, validate_uploaded_file


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _actor(actor_id: str | None) -> str | None:
    return str(actor_id) if actor_id is not None else None


def create_batch(
    db: Session,
    *,
    actor_id: str | None,
    notes: str | None = None,
) -> IngestionBatch:
    batch = IngestionBatch(
        status="OPEN",
        created_by_actor_id=_actor(actor_id),
        notes=notes,
    )
    db.add(batch)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=_actor(actor_id),
        entity_type="ingestion_batch",
        entity_id=str(batch.id),
        action="batch_created",
        reason_code="INGEST_BATCH_CREATE",
    )
    return batch


def get_batch(db: Session, batch_id: int) -> IngestionBatch:
    batch = db.get(IngestionBatch, batch_id)
    if not batch:
        raise BatchNotFound(batch_id)
    return batch


def get_occurrence(db: Session, occurrence_id: int) -> IngestionOccurrence:
    occ = db.get(IngestionOccurrence, occurrence_id)
    if not occ:
        raise OccurrenceNotFound(occurrence_id)
    return occ


def _fingerprint(occ: IngestionOccurrence) -> str:
    if occ.sha256:
        return f"hash:{occ.sha256}"
    return f"rejected:{occ.rejection_reason or 'unknown'}"


def _retain_until(limits: IngestionLimits) -> datetime:
    return _now() + timedelta(days=limits.quarantine_ttl_days)


@dataclass
class FileUploadInput:
    filename: str | None
    content_type: str | None
    stream: BinaryIO
    client_upload_key: str | None = None


@dataclass
class UploadItemResult:
    occurrence: IngestionOccurrence
    ok: bool


@dataclass
class MultiUploadResult:
    batch_id: int
    items: list[UploadItemResult] = field(default_factory=list)


def _lock_blob_by_hash(db: Session, sha256: str) -> IngestionBlob | None:
    return (
        db.execute(
            select(IngestionBlob).where(IngestionBlob.sha256 == sha256).with_for_update()
        )
        .scalars()
        .first()
    )


def _ensure_blob_present(
    db: Session,
    *,
    quarantine_root: Path,
    streamed: quarantine_storage.StreamedUpload,
    detected_mime: str | None,
    pending_files: list[Path],
) -> tuple[IngestionBlob, bool, bool]:
    """Return (blob, physical_reuse, rehydrated). Uses savepoint on insert race."""
    blob = _lock_blob_by_hash(db, streamed.sha256)
    if blob is None:
        rel = quarantine_storage.commit_temp_to_final(
            quarantine_root, streamed.temp_path, streamed.sha256, pending_files=pending_files
        )
        blob = IngestionBlob(
            sha256=streamed.sha256,
            storage_path=rel,
            size_bytes=streamed.size_bytes,
            detected_mime=detected_mime,
            physical_status="PRESENT",
            purged_at=None,
        )
        try:
            with db.begin_nested():
                db.add(blob)
                db.flush()
            return blob, False, False
        except IntegrityError:
            # concurrent insert won — drop our file if unused and reuse winner
            dest = quarantine_root / rel
            quarantine_storage.delete_quarantine_file(quarantine_root, rel)
            pending_files[:] = [p for p in pending_files if p.resolve() != dest.resolve()]
            blob = _lock_blob_by_hash(db, streamed.sha256)
            if blob is None:
                raise RequestLimitExceeded(
                    "Falha ao resolver blob após corrida de hash",
                    code="hash_race_retry",
                )
            if blob.physical_status == "PRESENT" and quarantine_storage.blob_file_exists(
                quarantine_root, blob.storage_path
            ):
                return blob, True, False
            raise RequestLimitExceeded(
                "Corrida de rehydrate — retry o upload",
                code="hash_race_retry",
            )

    if blob.physical_status == "PRESENT" and quarantine_storage.blob_file_exists(
        quarantine_root, blob.storage_path
    ):
        quarantine_storage._safe_unlink(streamed.temp_path)
        return blob, True, False

    # PURGED or missing file → rehydrate
    rel = quarantine_storage.commit_temp_to_final(
        quarantine_root, streamed.temp_path, streamed.sha256, pending_files=pending_files
    )
    old_rel = blob.storage_path
    blob.storage_path = rel
    blob.size_bytes = streamed.size_bytes
    blob.detected_mime = detected_mime or blob.detected_mime
    blob.physical_status = "PRESENT"
    blob.purged_at = None
    db.flush()
    if old_rel and old_rel != rel:
        quarantine_storage.delete_quarantine_file(quarantine_root, old_rel)
    return blob, False, True


def upload_files(
    db: Session,
    *,
    batch_id: int,
    actor_id: str | None,
    files: list[FileUploadInput],
    quarantine_path: Path | None = None,
    settings: object | None = None,
    limits: IngestionLimits | None = None,
    pending_files: list[Path] | None = None,
) -> MultiUploadResult:
    limits = limits or (limits_from_mapping(settings) if settings is not None else IngestionLimits())
    quarantine_root = Path(quarantine_path or "data/quarantine")
    quarantine_root.mkdir(parents=True, exist_ok=True)
    pending = pending_files if pending_files is not None else []

    batch = get_batch(db, batch_id)
    if batch.status != "OPEN":
        raise BatchClosed()

    if not files:
        raise RequestLimitExceeded("Nenhum arquivo no request", code="no_files")
    if len(files) > limits.max_files_per_request:
        raise RequestLimitExceeded(
            f"Máximo {limits.max_files_per_request} arquivos por request"
        )

    # structural aggregate pre-check is soft; enforce while streaming
    result = MultiUploadResult(batch_id=batch.id)
    aggregate = 0

    for item in files:
        filename = sanitize_original_filename(item.filename)
        key = (item.client_upload_key or "").strip() or None
        if key and len(key) > 128:
            key = key[:128]

        if key:
            existing = (
                db.query(IngestionOccurrence)
                .filter(
                    IngestionOccurrence.batch_id == batch.id,
                    IngestionOccurrence.client_upload_key == key,
                )
                .first()
            )
            if existing:
                # will compare fingerprint after we know hash/rejection
                pass
        else:
            existing = None

        occ = IngestionOccurrence(
            batch_id=batch.id,
            status="RECEIVED",
            original_filename=filename,
            declared_mime=item.content_type,
            client_upload_key=key,
            created_by_actor_id=_actor(actor_id),
        )
        # If idempotent key exists, don't create duplicate yet
        if existing is not None:
            # Process stream only to fingerprint — expensive but correct
            try:
                streamed = quarantine_storage.stream_to_temp(
                    quarantine_root,
                    item.stream,
                    max_bytes=limits.max_upload_bytes,
                )
            except ValueError as exc:
                code = str(exc)
                if _fingerprint(existing).startswith("rejected:") and code in (
                    "empty_file",
                    "file_too_large",
                ):
                    # approximate — prefer conflict if reasons differ
                    pass
                quarantine_storage._safe_unlink(getattr(locals().get("streamed", None), "temp_path", None))
                raise IdempotencyConflict() from exc

            fp_new = f"hash:{streamed.sha256}"
            if _fingerprint(existing) == fp_new:
                quarantine_storage._safe_unlink(streamed.temp_path)
                result.items.append(UploadItemResult(occurrence=existing, ok=existing.status == "STORED"))
                continue
            quarantine_storage._safe_unlink(streamed.temp_path)
            raise IdempotencyConflict()

        db.add(occ)
        db.flush()
        occ.status = "VALIDATING"
        db.flush()

        try:
            streamed = quarantine_storage.stream_to_temp(
                quarantine_root,
                item.stream,
                max_bytes=limits.max_upload_bytes,
            )
        except ValueError as exc:
            code = str(exc)
            reason = "file_too_large" if code == "file_too_large" else "empty_file"
            occ.status = "REJECTED"
            occ.rejection_reason = reason
            occ.retain_until = _retain_until(limits)
            db.flush()
            audit_public.record_event(
                db,
                actor_id=_actor(actor_id),
                entity_type="ingestion_occurrence",
                entity_id=str(occ.id),
                action="upload_rejected",
                reason_code="INGEST_UPLOAD_REJECTED",
                details=reason,
            )
            result.items.append(UploadItemResult(occurrence=occ, ok=False))
            continue

        aggregate += streamed.size_bytes
        if aggregate > limits.max_batch_bytes:
            quarantine_storage._safe_unlink(streamed.temp_path)
            occ.status = "REJECTED"
            occ.rejection_reason = "batch_bytes_exceeded"
            occ.size_bytes = streamed.size_bytes
            occ.sha256 = streamed.sha256
            occ.retain_until = _retain_until(limits)
            db.flush()
            audit_public.record_event(
                db,
                actor_id=_actor(actor_id),
                entity_type="ingestion_occurrence",
                entity_id=str(occ.id),
                action="upload_rejected",
                reason_code="INGEST_UPLOAD_REJECTED",
                details="batch_bytes_exceeded",
            )
            result.items.append(UploadItemResult(occurrence=occ, ok=False))
            # remaining files also rejected without reading fully? mark structural
            continue

        occ.size_bytes = streamed.size_bytes
        occ.sha256 = streamed.sha256
        db.flush()

        vr = validate_uploaded_file(
            streamed.temp_path,
            original_filename=filename,
            declared_mime=item.content_type,
            limits=limits,
        )
        if not vr.ok:
            quarantine_storage._safe_unlink(streamed.temp_path)
            occ.status = "REJECTED"
            occ.rejection_reason = vr.reason
            occ.detected_mime = vr.detected_mime
            occ.retain_until = _retain_until(limits)
            db.flush()
            audit_public.record_event(
                db,
                actor_id=_actor(actor_id),
                entity_type="ingestion_occurrence",
                entity_id=str(occ.id),
                action="upload_rejected",
                reason_code="INGEST_UPLOAD_REJECTED",
                details=vr.reason,
            )
            result.items.append(UploadItemResult(occurrence=occ, ok=False))
            continue

        occ.detected_mime = vr.detected_mime
        try:
            blob, reused, rehydrated = _ensure_blob_present(
                db,
                quarantine_root=quarantine_root,
                streamed=streamed,
                detected_mime=vr.detected_mime,
                pending_files=pending,
            )
        except RequestLimitExceeded as exc:
            quarantine_storage._safe_unlink(streamed.temp_path)
            occ.status = "FAILED"
            occ.rejection_reason = exc.code
            occ.retain_until = _retain_until(limits)
            db.flush()
            result.items.append(UploadItemResult(occurrence=occ, ok=False))
            continue

        if blob.physical_status != "PRESENT" or not quarantine_storage.blob_file_exists(
            quarantine_root, blob.storage_path
        ):
            occ.status = "FAILED"
            occ.rejection_reason = "blob_missing_after_store"
            occ.retain_until = _retain_until(limits)
            db.flush()
            result.items.append(UploadItemResult(occurrence=occ, ok=False))
            continue

        occ.blob_id = blob.id
        occ.physical_reuse = reused
        occ.rehydrated = rehydrated
        occ.status = "STORED"
        occ.rejection_reason = None
        occ.retain_until = None
        db.flush()
        audit_public.record_event(
            db,
            actor_id=_actor(actor_id),
            entity_type="ingestion_occurrence",
            entity_id=str(occ.id),
            action="upload_accepted",
            reason_code="INGEST_UPLOAD_ACCEPTED",
            details=f"reuse={reused};rehydrated={rehydrated}",
        )
        result.items.append(UploadItemResult(occurrence=occ, ok=True))

    return result


def abandon_occurrence(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str | None,
    limits: IngestionLimits | None = None,
) -> IngestionOccurrence:
    limits = limits or IngestionLimits()
    occ = get_occurrence(db, occurrence_id)
    if occ.status not in ("STORED", "RECEIVED", "VALIDATING", "FAILED"):
        raise InvalidTransition(f"Não é possível abandonar occurrence em status {occ.status}")
    if occ.status == "ABANDONED":
        return occ
    occ.status = "ABANDONED"
    occ.retain_until = _retain_until(limits)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=_actor(actor_id),
        entity_type="ingestion_occurrence",
        entity_id=str(occ.id),
        action="occurrence_abandoned",
        reason_code="INGEST_ABANDON",
    )
    return occ


@dataclass
class PurgeBlobPlan:
    blob_id: int
    sha256: str
    size_bytes: int
    eligible: bool
    blockers: list[int]
    occurrence_ids: list[int]


@dataclass
class PurgePlan:
    eligible_occurrence_ids: list[int]
    blobs: list[PurgeBlobPlan]
    bytes_to_free: int


def plan_purge(db: Session, *, now: datetime | None = None) -> PurgePlan:
    now = now or _now()
    eligible_occs = (
        db.query(IngestionOccurrence)
        .filter(
            IngestionOccurrence.status.in_(tuple(TERMINAL_PURGE_ELIGIBLE)),
            IngestionOccurrence.retain_until.isnot(None),
            IngestionOccurrence.retain_until <= now,
            IngestionOccurrence.bytes_purged_at.is_(None),
            IngestionOccurrence.blob_id.isnot(None),
        )
        .all()
    )
    eligible_ids = [o.id for o in eligible_occs]
    by_blob: dict[int, list[IngestionOccurrence]] = {}
    for o in (
        db.query(IngestionOccurrence)
        .filter(IngestionOccurrence.blob_id.isnot(None))
        .all()
    ):
        by_blob.setdefault(o.blob_id, []).append(o)  # type: ignore[arg-type]

    blobs_out: list[PurgeBlobPlan] = []
    bytes_to_free = 0
    for blob_id, occs in by_blob.items():
        blob = db.get(IngestionBlob, blob_id)
        if not blob or blob.physical_status != "PRESENT":
            continue
        blockers: list[int] = []
        for o in occs:
            if o.status in ACTIVE_CONTENT_STATUSES:
                blockers.append(o.id)
            elif o.status in TERMINAL_PURGE_ELIGIBLE:
                if o.retain_until is None or o.retain_until > now:
                    blockers.append(o.id)
                elif o.bytes_purged_at is not None:
                    pass
            else:
                blockers.append(o.id)
        eligible = len(blockers) == 0 and any(
            o.id in set(eligible_ids) for o in occs
        )
        # blob eligible only if ALL occs are terminal+past retain and at least one still needs purge mark
        all_ready = True
        for o in occs:
            if o.status not in TERMINAL_PURGE_ELIGIBLE:
                all_ready = False
                break
            if o.retain_until is None or o.retain_until > now:
                all_ready = False
                break
        plan = PurgeBlobPlan(
            blob_id=blob.id,
            sha256=blob.sha256,
            size_bytes=blob.size_bytes,
            eligible=all_ready and blob.physical_status == "PRESENT",
            blockers=blockers,
            occurrence_ids=[o.id for o in occs],
        )
        blobs_out.append(plan)
        if plan.eligible:
            bytes_to_free += blob.size_bytes

    return PurgePlan(
        eligible_occurrence_ids=eligible_ids,
        blobs=blobs_out,
        bytes_to_free=bytes_to_free,
    )


def execute_purge(
    db: Session,
    *,
    actor_id: str | None,
    quarantine_path: Path | None = None,
    limits: IngestionLimits | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict:
    limits = limits or IngestionLimits()
    if quarantine_path is None:
        raise RequestLimitExceeded("quarantine_path obrigatório", code="quarantine_path_required")
    quarantine_root = Path(quarantine_path)
    now = now or _now()
    plan = plan_purge(db, now=now)
    if dry_run:
        return {
            "dry_run": True,
            "eligible_occurrence_ids": plan.eligible_occurrence_ids,
            "blobs": [
                {
                    "blob_id": b.blob_id,
                    "sha256": b.sha256,
                    "size_bytes": b.size_bytes,
                    "eligible": b.eligible,
                    "blockers": b.blockers,
                    "occurrence_ids": b.occurrence_ids,
                }
                for b in plan.blobs
            ],
            "bytes_to_free": plan.bytes_to_free,
            "purged_blob_ids": [],
            "marked_occurrence_ids": [],
        }

    purged_blobs: list[int] = []
    marked: list[int] = []
    for b in plan.blobs:
        if not b.eligible:
            continue
        blob = (
            db.execute(
                select(IngestionBlob).where(IngestionBlob.id == b.blob_id).with_for_update()
            )
            .scalars()
            .first()
        )
        if not blob or blob.physical_status != "PRESENT":
            continue
        # re-check blockers under lock
        occs = (
            db.query(IngestionOccurrence)
            .filter(IngestionOccurrence.blob_id == blob.id)
            .with_for_update()
            .all()
        )
        if any(
            o.status in ACTIVE_CONTENT_STATUSES
            or o.status not in TERMINAL_PURGE_ELIGIBLE
            or o.retain_until is None
            or o.retain_until > now
            for o in occs
        ):
            continue
        quarantine_storage.delete_quarantine_file(quarantine_root, blob.storage_path)
        blob.physical_status = "PURGED"
        blob.purged_at = now
        blob.storage_path = blob.storage_path  # keep last path for forensics
        for o in occs:
            if o.bytes_purged_at is None:
                o.bytes_purged_at = now
                marked.append(o.id)
        db.flush()
        purged_blobs.append(blob.id)
        audit_public.record_event(
            db,
            actor_id=_actor(actor_id),
            entity_type="ingestion_blob",
            entity_id=str(blob.id),
            action="bytes_purged",
            reason_code="INGEST_BYTES_PURGED",
            details=f"sha256={blob.sha256};occurrences={b.occurrence_ids}",
        )

    return {
        "dry_run": False,
        "eligible_occurrence_ids": plan.eligible_occurrence_ids,
        "blobs": [
            {
                "blob_id": b.blob_id,
                "sha256": b.sha256,
                "size_bytes": b.size_bytes,
                "eligible": b.eligible,
                "blockers": b.blockers,
                "occurrence_ids": b.occurrence_ids,
            }
            for b in plan.blobs
        ],
        "bytes_to_free": plan.bytes_to_free,
        "purged_blob_ids": purged_blobs,
        "marked_occurrence_ids": marked,
    }
