"""J3-I1 — Domain tests for staging IR."""

from __future__ import annotations

import io
import json

import pytest
from sqlalchemy.orm import Session

from app.foundation.settings import get_settings
from app.ingestion import commands as ingestion_commands
from app.ingestion.errors import DocumentLocked, VersionConflict
from app.ingestion.limits import limits_from_mapping
from app.ingestion.staging_commands import (
    add_document_to_set,
    correct_field,
    create_document_set,
    create_issue,
    effective_field_value,
    lock_document,
    resolve_issue,
    restore_field,
    seed_document_from_occurrence,
)
from app.ingestion.staging_queries import get_document_detail, list_review_changes
from tests.ingestion_i0_fixtures import minimal_pdf_bytes


def _stored_occurrence(db: Session, tag: str = "i1") -> tuple[int, int]:
    settings = get_settings()
    limits = limits_from_mapping(settings)
    batch = ingestion_commands.create_batch(db, actor_id="actor-1", notes="i1")
    db.flush()
    pdf = minimal_pdf_bytes(tag=tag)
    result = ingestion_commands.upload_files(
        db,
        batch_id=batch.id,
        actor_id="actor-1",
        files=[
            ingestion_commands.FileUploadInput(
                filename=f"{tag}.pdf",
                content_type="application/pdf",
                stream=io.BytesIO(pdf),
                client_upload_key=None,
            )
        ],
        quarantine_path=settings.quarantine_path,
        limits=limits,
        pending_files=[],
    )
    db.commit()
    occ = result.items[0].occurrence
    assert occ.status == "STORED"
    return batch.id, occ.id


def test_seed_document_preserves_empty_vs_zero(db: Session):
    _, occ_id = _stored_occurrence(db, "empty-zero")
    doc = seed_document_from_occurrence(
        db,
        occurrence_id=occ_id,
        actor_id="actor-1",
        doc_type="ORDINE",
        sections=[{"section_key": "header", "title": "Header", "ordinal": 0}],
        fields=[
            {"field_key": "qty_missing", "raw_value": None, "value_type": "number", "section_key": "header"},
            {"field_key": "qty_empty", "raw_value": "", "value_type": "number", "section_key": "header"},
            {"field_key": "qty_zero", "raw_value": "0", "normalized_value": "0", "value_type": "number", "section_key": "header"},
            {
                "field_key": "supplier",
                "raw_value": "ACME",
                "locator_json": None,
                "provenance_json": json.dumps({"source": "contract_stub"}),
                "section_key": "header",
            },
        ],
        rows=[
            {
                "row_index": 0,
                "section_key": "header",
                "cells": {"sku": {"raw": "I.V. 1", "normalized": None}},
            }
        ],
        issues=[
            {
                "code": "AMBIGUOUS_SKU",
                "message": "I.V. 1 não é SKU canônico",
                "severity": "WARNING",
                "target_type": "DOCUMENT",
            }
        ],
    )
    db.commit()
    detail = get_document_detail(db, doc.id)
    by_key = {f.field_key: f for f in detail.fields}
    assert by_key["qty_missing"].raw_value is None
    assert by_key["qty_empty"].raw_value == ""
    assert by_key["qty_zero"].raw_value == "0"
    assert by_key["qty_missing"].raw_value != "0"
    assert by_key["supplier"].locator_json is None
    assert len(detail.rows) == 1
    assert len(detail.issues) == 1
    assert detail.adapter_id == "contract_stub_v1"


def test_correct_preserves_raw_and_history(db: Session):
    _, occ_id = _stored_occurrence(db, "correct")
    doc = seed_document_from_occurrence(
        db,
        occurrence_id=occ_id,
        actor_id="actor-1",
        fields=[{"field_key": "total", "raw_value": "10", "normalized_value": "10"}],
    )
    db.commit()
    field = doc.fields[0]
    raw_before = field.raw_value
    corrected = correct_field(
        db,
        field_id=field.id,
        actor_id="actor-1",
        corrected_value="12",
        expected_version=field.version,
        reason="typo",
    )
    db.commit()
    assert corrected.raw_value == raw_before == "10"
    assert corrected.corrected_value == "12"
    assert corrected.review_status == "CORRECTED"
    assert effective_field_value(corrected) == "12"
    changes = list_review_changes(db, doc.id)
    assert len(changes) == 1
    assert changes[0].new_value == "12"

    restored = restore_field(
        db,
        field_id=field.id,
        actor_id="actor-1",
        expected_version=corrected.version,
    )
    db.commit()
    assert restored.corrected_value is None
    assert restored.raw_value == "10"
    assert restored.review_status == "PENDING"
    assert effective_field_value(restored) == "10"


def test_version_conflict(db: Session):
    _, occ_id = _stored_occurrence(db, "ver")
    doc = seed_document_from_occurrence(
        db,
        occurrence_id=occ_id,
        actor_id="actor-1",
        fields=[{"field_key": "x", "raw_value": "1"}],
    )
    db.commit()
    field = doc.fields[0]
    with pytest.raises(VersionConflict):
        correct_field(
            db,
            field_id=field.id,
            actor_id="actor-1",
            corrected_value="2",
            expected_version=999,
        )


def test_lock_blocks_other_actor(db: Session):
    _, occ_id = _stored_occurrence(db, "lock")
    doc = seed_document_from_occurrence(
        db,
        occurrence_id=occ_id,
        actor_id="actor-1",
        fields=[{"field_key": "x", "raw_value": "1"}],
    )
    db.commit()
    lock_document(db, document_id=doc.id, actor_id="actor-1")
    db.commit()
    field = doc.fields[0]
    with pytest.raises(DocumentLocked):
        correct_field(
            db,
            field_id=field.id,
            actor_id="actor-2",
            corrected_value="9",
            expected_version=field.version,
        )


def test_document_set_and_issue(db: Session):
    batch_id, occ_id = _stored_occurrence(db, "set")
    doc = seed_document_from_occurrence(
        db, occurrence_id=occ_id, actor_id="actor-1", doc_type="ORDINE"
    )
    db.flush()
    ds = create_document_set(
        db, actor_id="actor-1", batch_id=batch_id, projection_key="ordine:589"
    )
    add_document_to_set(db, document_set_id=ds.id, document_id=doc.id, role="primary")
    issue = create_issue(
        db,
        document_id=doc.id,
        actor_id="actor-1",
        severity="ERROR",
        code="MATH",
        message="total mismatch",
    )
    resolve_issue(db, issue_id=issue.id, actor_id="actor-1", status="RESOLVED")
    db.commit()
    detail = get_document_detail(db, doc.id)
    assert detail.document_set_id == ds.id
    assert detail.issues[0].status == "RESOLVED"


def test_dismiss_error_requires_justification_and_audits(db: Session):
    """RUX-3B-2b: Ignorar ERROR sem justificativa falha; com justificativa → Audit."""
    from app.audit import public as audit_public
    from app.ingestion.errors import IssueJustificationRequired

    _, occ_id = _stored_occurrence(db, "dismiss-err")
    doc = seed_document_from_occurrence(
        db,
        occurrence_id=occ_id,
        actor_id="actor-1",
        doc_type="ORDINE_COMPRA",
        sections=[{"section_key": "header", "title": "Header", "ordinal": 0}],
        fields=[],
        rows=[],
        issues=[],
    )
    db.flush()
    issue = create_issue(
        db,
        document_id=doc.id,
        actor_id="actor-1",
        severity="ERROR",
        code="MATH_TOTAL_MISMATCH",
        message="total mismatch",
    )
    db.flush()

    with pytest.raises(IssueJustificationRequired):
        resolve_issue(db, issue_id=issue.id, actor_id="actor-1", status="DISMISSED")

    resolve_issue(
        db,
        issue_id=issue.id,
        actor_id="actor-1",
        status="DISMISSED",
        justification="Totais conferidos no PDF original — falso positivo",
    )
    db.commit()

    events = audit_public.history_by_entity(db, "ingestion_issue", str(issue.id), limit=10)
    resolve_ev = next((e for e in events if e.action == "issue_resolved"), None)
    assert resolve_ev is not None
    details = json.loads(resolve_ev.details or "{}")
    assert details["status"] == "DISMISSED"
    assert details["severity"] == "ERROR"
    assert "falso positivo" in (details.get("justification") or "")
