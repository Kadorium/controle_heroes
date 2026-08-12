"""J3-I0 — security validation."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.ingestion import commands as cmd
from app.ingestion.limits import IngestionLimits
from app.ingestion.validation import check_filename_safe, validate_uploaded_file
from tests.ingestion_i0_fixtures import (
    minimal_pdf_bytes,
    minimal_xlsx_bytes,
    pdf_with_javascript_token,
    write_fixture,
)


@pytest.fixture()
def quarantine(tmp_path: Path) -> Path:
    q = tmp_path / "q"
    q.mkdir()
    return q


def test_filename_traversal():
    assert check_filename_safe("../x.pdf") == "path_traversal_filename"
    assert check_filename_safe("C:\\abs.pdf") == "absolute_filename"
    assert check_filename_safe("ok.pdf") is None


def test_reject_javascript_pdf(tmp_path: Path):
    path = write_fixture(tmp_path / "js.pdf", pdf_with_javascript_token())
    vr = validate_uploaded_file(
        path, original_filename="js.pdf", declared_mime="application/pdf", limits=IngestionLimits()
    )
    assert vr.ok is False
    assert "pdf" in (vr.reason or "")


def test_reject_xlsx_macro(tmp_path: Path):
    path = write_fixture(tmp_path / "m.xlsx", minimal_xlsx_bytes(with_vba=True))
    vr = validate_uploaded_file(
        path, original_filename="m.xlsx", declared_mime=None, limits=IngestionLimits()
    )
    assert vr.ok is False
    assert vr.reason in ("xlsx_active_or_external", "xlsx_macro")


def test_reject_xlsx_external(tmp_path: Path):
    path = write_fixture(tmp_path / "e.xlsx", minimal_xlsx_bytes(external_rel=True))
    vr = validate_uploaded_file(
        path, original_filename="e.xlsx", declared_mime=None, limits=IngestionLimits()
    )
    assert vr.ok is False
    assert "external" in (vr.reason or "")


def test_reject_empty_and_spoof(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    r = cmd.upload_files(
        db,
        batch_id=batch.id,
        actor_id="1",
        files=[cmd.FileUploadInput("empty.pdf", "application/pdf", io.BytesIO(b""))],
        quarantine_path=quarantine,
        limits=IngestionLimits(),
        pending_files=[],
    )
    assert r.items[0].occurrence.status == "REJECTED"
    assert r.items[0].occurrence.rejection_reason == "empty_file"

    r2 = cmd.upload_files(
        db,
        batch_id=batch.id,
        actor_id="1",
        files=[cmd.FileUploadInput("fake.pdf", "application/pdf", io.BytesIO(b"PK\x03\x04fake"))],
        quarantine_path=quarantine,
        limits=IngestionLimits(),
        pending_files=[],
    )
    assert r2.items[0].occurrence.status == "REJECTED"


def test_cleanup_temp_on_reject(db: Session, quarantine: Path):
    batch = cmd.create_batch(db, actor_id="1")
    cmd.upload_files(
        db,
        batch_id=batch.id,
        actor_id="1",
        files=[cmd.FileUploadInput("bad.pdf", "application/pdf", io.BytesIO(b"nope"))],
        quarantine_path=quarantine,
        limits=IngestionLimits(),
        pending_files=[],
    )
    tmp = quarantine / "_tmp"
    leftovers = list(tmp.glob("*.part")) if tmp.exists() else []
    assert leftovers == []


def test_good_pdf_passes_validation(tmp_path: Path):
    path = write_fixture(tmp_path / "ok.pdf", minimal_pdf_bytes("good"))
    vr = validate_uploaded_file(
        path, original_filename="ok.pdf", declared_mime="application/pdf", limits=IngestionLimits()
    )
    assert vr.ok is True
