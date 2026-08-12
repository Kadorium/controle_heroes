"""J3-I0 — domain + purge + rehydrate + multi-upload."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.ingestion import commands as cmd
from app.ingestion.limits import IngestionLimits
from app.ingestion.models import IngestionBlob, IngestionOccurrence
from app.ingestion import storage as quarantine_storage
from tests.ingestion_i0_fixtures import minimal_pdf_bytes, minimal_xlsx_bytes


@pytest.fixture()
def quarantine(tmp_path: Path) -> Path:
    q = tmp_path / "q"
    q.mkdir()
    return q


def _upload(db: Session, batch_id: int, data: bytes, name: str, **kw):
    return cmd.upload_files(
        db,
        batch_id=batch_id,
        actor_id="1",
        files=[
            cmd.FileUploadInput(
                filename=name,
                content_type="application/pdf" if name.endswith(".pdf") else None,
                stream=io.BytesIO(data),
                client_upload_key=kw.get("key"),
            )
        ],
        quarantine_path=kw["quarantine"],
        limits=IngestionLimits(),
        pending_files=kw.get("pending", []),
    )


def test_batch_multi_occurrence_same_hash(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    pdf = minimal_pdf_bytes("same-hash-1")
    r1 = _upload(db, batch.id, pdf, "a.pdf", quarantine=quarantine)
    r2 = _upload(db, batch.id, pdf, "b.pdf", quarantine=quarantine)
    assert r1.items[0].occurrence.status == "STORED"
    assert r2.items[0].occurrence.status == "STORED"
    assert r1.items[0].occurrence.sha256 == r2.items[0].occurrence.sha256
    assert r2.items[0].occurrence.physical_reuse is True
    blobs = db.query(IngestionBlob).filter(IngestionBlob.sha256 == r1.items[0].occurrence.sha256).all()
    assert len(blobs) == 1


def test_purge_shared_blob_respects_ttl(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    pdf = minimal_pdf_bytes("purge-ttl")
    a = _upload(db, batch.id, pdf, "a.pdf", quarantine=quarantine).items[0].occurrence
    b = _upload(db, batch.id, pdf, "b.pdf", quarantine=quarantine).items[0].occurrence
    cmd.abandon_occurrence(db, occurrence_id=a.id, actor_id="1")
    cmd.abandon_occurrence(db, occurrence_id=b.id, actor_id="1")
    a = db.get(IngestionOccurrence, a.id)
    b = db.get(IngestionOccurrence, b.id)
    now = datetime.now(timezone.utc)
    a.retain_until = now - timedelta(days=1)
    b.retain_until = now + timedelta(days=10)
    db.flush()
    plan = cmd.plan_purge(db, now=now)
    eligible_blobs = [x for x in plan.blobs if x.blob_id == a.blob_id]
    assert eligible_blobs
    assert eligible_blobs[0].eligible is False
    assert b.id in eligible_blobs[0].blockers

    b.retain_until = now - timedelta(hours=1)
    db.flush()
    out = cmd.execute_purge(db, actor_id="1", quarantine_path=quarantine, dry_run=False, now=now)
    assert a.blob_id in out["purged_blob_ids"], out
    blob = db.get(IngestionBlob, a.blob_id)
    assert blob.physical_status == "PURGED"
    a = db.get(IngestionOccurrence, a.id)
    b = db.get(IngestionOccurrence, b.id)
    assert a.status == "ABANDONED" and b.status == "ABANDONED"
    assert a.bytes_purged_at is not None and b.bytes_purged_at is not None


def test_rehydrate_after_purge(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    pdf = minimal_pdf_bytes("rehydrate")
    o1 = _upload(db, batch.id, pdf, "a.pdf", quarantine=quarantine).items[0].occurrence
    cmd.abandon_occurrence(db, occurrence_id=o1.id, actor_id="1")
    o1 = db.get(IngestionOccurrence, o1.id)
    o1.retain_until = datetime.now(timezone.utc) - timedelta(days=1)
    db.flush()
    cmd.execute_purge(
        db,
        actor_id="1",
        quarantine_path=quarantine,
        dry_run=False,
        now=datetime.now(timezone.utc),
    )
    blob = db.get(IngestionBlob, o1.blob_id)
    assert blob.physical_status == "PURGED"
    assert not quarantine_storage.blob_file_exists(quarantine, blob.storage_path)

    r2 = _upload(db, batch.id, pdf, "again.pdf", quarantine=quarantine)
    o2 = r2.items[0].occurrence
    assert o2.status == "STORED"
    assert o2.rehydrated is True
    blob = db.get(IngestionBlob, o2.blob_id)
    assert blob.physical_status == "PRESENT"
    assert quarantine_storage.blob_file_exists(quarantine, blob.storage_path)


def test_multi_upload_partial(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    pdf = minimal_pdf_bytes("multi")
    result = cmd.upload_files(
        db,
        batch_id=batch.id,
        actor_id="1",
        files=[
            cmd.FileUploadInput("ok.pdf", "application/pdf", io.BytesIO(pdf)),
            cmd.FileUploadInput("bad.pdf", "application/pdf", io.BytesIO(b"not-a-pdf")),
            cmd.FileUploadInput("ok2.pdf", "application/pdf", io.BytesIO(pdf)),
        ],
        quarantine_path=quarantine,
        limits=IngestionLimits(),
        pending_files=[],
    )
    statuses = [i.occurrence.status for i in result.items]
    assert statuses == ["STORED", "REJECTED", "STORED"]
    assert result.items[2].occurrence.physical_reuse is True


def test_idempotent_key_replay(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    pdf = minimal_pdf_bytes("idem")
    r1 = _upload(db, batch.id, pdf, "a.pdf", quarantine=quarantine, key="k1")
    r2 = _upload(db, batch.id, pdf, "a.pdf", quarantine=quarantine, key="k1")
    assert r1.items[0].occurrence.id == r2.items[0].occurrence.id


def test_stored_implies_file_exists(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    pdf = minimal_pdf_bytes("exists")
    o = _upload(db, batch.id, pdf, "a.pdf", quarantine=quarantine).items[0].occurrence
    assert o.status == "STORED"
    blob = db.get(IngestionBlob, o.blob_id)
    assert quarantine_storage.blob_file_exists(quarantine, blob.storage_path)


def test_xlsx_accepted(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    data = minimal_xlsx_bytes()
    r = cmd.upload_files(
        db,
        batch_id=batch.id,
        actor_id="1",
        files=[
            cmd.FileUploadInput(
                "sheet.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                io.BytesIO(data),
            )
        ],
        quarantine_path=quarantine,
        limits=IngestionLimits(),
        pending_files=[],
    )
    assert r.items[0].occurrence.status == "STORED"
