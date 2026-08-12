"""DEF-RUX-TX-01 / H-EXEC-06 — Ordine commit Modelo B (savepoints + honest PARTIAL)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.commit_commands import (
    _compute_attempt_status,
    _should_run_op,
    execute_commit,
)
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field(key: str, value: str | None):
    f = MagicMock()
    f.field_key = key
    f.raw_value = value
    f.normalized_value = value
    f.corrected_value = None
    f.review_status = "PENDING"
    return f


def _make_ordine_doc(
    *,
    supplier_id: int | None = None,
    pending_supplier: dict | None = None,
    order_number: str = "589",
):
    doc = MagicMock()
    doc.id = 10
    doc.occurrence_id = 5
    doc.issues = []
    doc.rows = [
        MagicMock(
            row_index=0,
            cells_json=json.dumps(
                {
                    "sku": {"normalized": "SKU1"},
                    "product_id_catalog": {"normalized": "100"},
                    "quantity": {"normalized": "10"},
                    "unit_price": {"normalized": "5.00"},
                }
            ),
        ),
    ]
    fields = [
        _field("order_number", order_number),
        _field("order_date", "2026-06-04"),
        _field("currency", "EUR"),
    ]
    if supplier_id is not None:
        fields.append(_field("supplier_id_catalog", str(supplier_id)))
    if pending_supplier is not None:
        fields.append(
            _field("pending_create_supplier", json.dumps(pending_supplier))
        )
    doc.fields = fields
    return doc


def _make_occurrence():
    occ = MagicMock()
    occ.blob = MagicMock()
    occ.blob.physical_status = "PRESENT"
    occ.blob.storage_path = "ab/cd"
    occ.original_filename = "ordine.pdf"
    occ.detected_mime = "application/pdf"
    return occ


def _preview_ok():
    preview = MagicMock()
    preview.readiness_derived = True
    preview.can_commit = True
    return preview


def _ledger_op(op_key: str, status: str, entity_id: str | None = None):
    op = MagicMock(spec=IngestionCommitOperation)
    op.op_key = op_key
    op.status = status
    op.entity_id = entity_id
    op.details_json = None
    return op


def _query_router(existing_attempt=None, ledger_ops: list | None = None):
    ledger_ops = ledger_ops or []

    def query_side_effect(model):
        q = MagicMock()
        if model is IngestionCommitAttempt:
            q.filter.return_value.first.return_value = existing_attempt
        elif model is IngestionCommitOperation:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.all.return_value = ledger_ops
        return q

    return query_side_effect


def _make_db(existing_attempt=None, ledger_ops: list | None = None):
    db = MagicMock()
    db.query.side_effect = _query_router(existing_attempt, ledger_ops)
    nested = MagicMock()
    db.begin_nested.return_value = nested
    nested.__enter__ = MagicMock(return_value=None)
    nested.__exit__ = MagicMock(return_value=False)
    return db


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------


def test_compute_attempt_status_partial_when_mixed():
    assert (
        _compute_attempt_status(
            succeeded=["store_document"], failed=["create_supplier"], unknown=[]
        )
        == "PARTIAL"
    )


def test_compute_attempt_status_failed_when_only_failures():
    assert (
        _compute_attempt_status(succeeded=[], failed=["store_document"], unknown=[])
        == "FAILED"
    )


def test_compute_attempt_status_unknown_when_indeterminate():
    assert (
        _compute_attempt_status(
            succeeded=["store_document"], failed=[], unknown=["create_order"]
        )
        == "UNKNOWN"
    )


def test_should_run_op_skips_succeeded():
    ledger = {"store_document": _ledger_op("store_document", "SUCCEEDED", "42")}
    assert _should_run_op(ledger, "store_document") is False
    assert _should_run_op(ledger, "create_supplier") is True


def test_should_run_op_retries_failed_and_unknown():
    ledger = {
        "create_supplier": _ledger_op("create_supplier", "FAILED"),
        "create_order": _ledger_op("create_order", "UNKNOWN"),
    }
    assert _should_run_op(ledger, "create_supplier") is True
    assert _should_run_op(ledger, "create_order") is True


# ---------------------------------------------------------------------------
# execute_commit — PARTIAL honesty
# ---------------------------------------------------------------------------


class TestOrdineCommitModeloB:
    def test_create_supplier_failure_after_store_is_partial_not_failed(self):
        doc = _make_ordine_doc(
            pending_supplier={"name": "New Supplier", "code": "NS"},
        )
        db = _make_db()

        with patch(
            "app.ingestion.commit_commands.get_document_detail", return_value=doc
        ), patch(
            "app.ingestion.commit_commands.preview_commit", return_value=_preview_ok()
        ), patch(
            "app.ingestion.commit_commands._compute_fingerprint", return_value="fp1"
        ), patch(
            "app.ingestion.commit_commands.quarantine_storage.resolve_quarantine_path",
            return_value=Path("/tmp/blob.pdf"),
        ), patch(
            "pathlib.Path.is_file", return_value=True
        ), patch(
            "pathlib.Path.read_bytes", return_value=b"%PDF"
        ), patch.object(
            db, "get", return_value=_make_occurrence()
        ), patch(
            "app.ingestion.commit_commands.documents_public.store_document"
        ) as mock_store, patch(
            "app.ingestion.commit_commands.catalog_public.create_supplier",
            side_effect=Exception("Catalog down"),
        ), patch(
            "app.ingestion.commit_commands.audit_public.record_event"
        ):
            mock_store.return_value = MagicMock(id=200)

            result = execute_commit(
                db,
                document_id=10,
                operation_key="op-partial-supplier",
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        assert result.status == "PARTIAL"
        mock_store.assert_called_once()
        db.begin_nested.assert_called()

    def test_resume_skips_succeeded_store_document(self):
        doc = _make_ordine_doc(
            pending_supplier={"name": "New Supplier", "code": "NS"},
        )
        store_op = _ledger_op("store_document", "SUCCEEDED", "200")
        supplier_op = _ledger_op("create_supplier", "FAILED")

        existing = MagicMock()
        existing.id = 99
        existing.status = "PARTIAL"
        existing.payload_fingerprint = "fp1"

        db = _make_db(existing_attempt=existing, ledger_ops=[store_op, supplier_op])
        created_supplier = MagicMock(id=55)

        with patch(
            "app.ingestion.commit_commands.get_document_detail", return_value=doc
        ), patch(
            "app.ingestion.commit_commands.preview_commit", return_value=_preview_ok()
        ), patch(
            "app.ingestion.commit_commands._compute_fingerprint", return_value="fp1"
        ), patch(
            "app.ingestion.commit_commands.documents_public.store_document"
        ) as mock_store, patch(
            "app.ingestion.commit_commands.catalog_public.create_supplier",
            return_value=created_supplier,
        ) as mock_create_supplier, patch(
            "app.ingestion.commit_commands.orders_public.create_order",
            return_value=MagicMock(id=300, version=1, code="ING-589"),
        ), patch(
            "app.ingestion.commit_commands.orders_public.get_order",
            return_value=MagicMock(version=1),
        ), patch(
            "app.ingestion.commit_commands.orders_public.add_item"
        ), patch(
            "app.ingestion.commit_commands.documents_public.link_document"
        ), patch(
            "app.ingestion.commit_commands.audit_public.record_event"
        ):
            execute_commit(
                db,
                document_id=10,
                operation_key="op-resume",
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        mock_store.assert_not_called()
        mock_create_supplier.assert_called_once()

    def test_succeeded_attempt_returns_without_rerunning(self):
        doc = _make_ordine_doc(supplier_id=1)
        existing = MagicMock()
        existing.id = 77
        existing.status = "SUCCEEDED"
        existing.payload_fingerprint = "fp1"

        db = _make_db(existing_attempt=existing)

        with patch(
            "app.ingestion.commit_commands.get_document_detail", return_value=doc
        ), patch(
            "app.ingestion.commit_commands.preview_commit", return_value=_preview_ok()
        ), patch(
            "app.ingestion.commit_commands._compute_fingerprint", return_value="fp1"
        ), patch(
            "app.ingestion.commit_commands.documents_public.store_document"
        ) as mock_store:
            result = execute_commit(
                db,
                document_id=10,
                operation_key="op-done",
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        assert result is existing
        mock_store.assert_not_called()
        db.add.assert_not_called()
