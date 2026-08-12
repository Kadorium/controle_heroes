"""XLSX commit commands — J3-I7.

Preview + Commit para ORDINE_COMPRA_XLSX.
Reutiliza o padrão do commit_commands.py (ordine_heroes_v1).

Regras hard preservadas:
- NEVER Order além de DRAFT
- NEVER auto-confirm Order
- NEVER silent SKU match
- Idempotência por operation_key + fingerprint
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.catalog import public as catalog_public
from app.documents import public as documents_public
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.ir_models import IngestionDocument, IngestionField, IngestionRow
from app.ingestion.staging_queries import get_document_detail
from app.orders import public as orders_public
from app.ingestion import storage as quarantine_storage


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class XlsxCommitConflictFingerprint(IngestionError):
    def __init__(self, operation_key: str) -> None:
        super().__init__(
            f"operation_key '{operation_key}' já existe com fingerprint diferente",
            code="commit_conflict_fingerprint",
        )


class XlsxCommitBlockedByIssues(IngestionError):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} issue(s) OPEN com severity ERROR bloqueiam o commit",
            code="commit_blocked_by_issues",
        )


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def _compute_fingerprint(db: Session, document_id: int) -> str:
    doc = get_document_detail(db, document_id)
    canonical: dict = {
        "doc_type": doc.doc_type,
        "adapter_id": doc.adapter_id,
        "adapter_version": doc.adapter_version,
        "fields": sorted(
            [
                {
                    "key": f.field_key,
                    "effective": (
                        f.corrected_value
                        if f.review_status == "CORRECTED"
                        else (f.normalized_value or f.raw_value)
                    ),
                }
                for f in (doc.fields or [])
            ],
            key=lambda x: x["key"],
        ),
        "rows": sorted(
            [
                {"index": r.row_index, "key": r.row_key, "cells": r.cells_json}
                for r in (doc.rows or [])
            ],
            key=lambda x: x["index"],
        ),
    }
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# IR field reader helpers
# ---------------------------------------------------------------------------


def _field_value(doc: IngestionDocument, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _row_cells(row: IngestionRow) -> dict:
    try:
        return json.loads(row.cells_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _cell_value(cells: dict, col: str) -> str | None:
    cell = cells.get(col)
    if cell is None:
        return None
    if isinstance(cell, dict):
        if cell.get("corrected") is not None:
            return cell["corrected"]
        return cell.get("normalized") or cell.get("raw")
    return str(cell)


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


@dataclass
class XlsxPreviewOperation:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class XlsxPreviewResult:
    document_id: int
    fingerprint: str
    operations: list[XlsxPreviewOperation]
    open_error_count: int
    can_commit: bool


def preview_commit_xlsx(db: Session, document_id: int) -> XlsxPreviewResult:
    """Calcula digest e lista de operações sem escrever nada nos owners."""
    doc = get_document_detail(db, document_id)
    fingerprint = _compute_fingerprint(db, document_id)

    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )

    ops: list[XlsxPreviewOperation] = []

    ops.append(
        XlsxPreviewOperation(
            op_key="store_document",
            description="Promover bytes da quarantine para Documents",
            entity_type="document",
            params={"occurrence_id": doc.occurrence_id},
        )
    )

    supplier_id_str = _field_value(doc, "supplier_id_catalog")
    supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None
    order_number = _field_value(doc, "order_number")
    currency = _field_value(doc, "currency") or "EUR"

    if supplier_id and order_number:
        ops.append(
            XlsxPreviewOperation(
                op_key="create_order",
                description=f"Criar Order DRAFT code={order_number} supplier_id={supplier_id}",
                entity_type="order",
                params={"code": order_number, "supplier_id": supplier_id, "currency": currency},
            )
        )
        # Ship items as order items
        ship_rows = [r for r in (doc.rows or []) if r.section_id is not None or True]
        ship_rows_in_section = [r for r in (doc.rows or [])]
        for row in ship_rows_in_section:
            cells = _row_cells(row)
            sku = _cell_value(cells, "sku")
            qty_str = _cell_value(cells, "quantity")
            invoice_price_str = _cell_value(cells, "invoice_price")
            if sku and qty_str and invoice_price_str:
                ops.append(
                    XlsxPreviewOperation(
                        op_key=f"add_item_{row.row_index}",
                        description=f"Adicionar item Order: sku={sku} qty={qty_str}",
                        entity_type="order_item",
                        params={"sku": sku, "quantity": qty_str, "unit_price": invoice_price_str},
                    )
                )
        ops.append(
            XlsxPreviewOperation(
                op_key="link_document",
                description="Vincular documento à Order via Documents module",
                entity_type="document_link",
            )
        )

    return XlsxPreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        operations=ops,
        open_error_count=open_errors,
        can_commit=open_errors == 0,
    )


# ---------------------------------------------------------------------------
# Ledger helpers (reuse pattern from commit_commands.py)
# ---------------------------------------------------------------------------


def _get_or_create_attempt(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    fingerprint: str,
    actor_id: str,
) -> tuple[IngestionCommitAttempt, bool]:
    """Returns (attempt, is_existing).

    is_existing=True → idempotent return.
    Raises XlsxCommitConflictFingerprint if fingerprint mismatch.
    """
    existing = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing is not None:
        if existing.payload_fingerprint != fingerprint:
            raise XlsxCommitConflictFingerprint(operation_key)
        return existing, True

    attempt = IngestionCommitAttempt(
        document_id=document_id,
        operation_key=operation_key,
        payload_fingerprint=fingerprint,
        status="UNKNOWN",
        actor_id=actor_id,
    )
    db.add(attempt)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(IngestionCommitAttempt)
            .filter(IngestionCommitAttempt.operation_key == operation_key)
            .first()
        )
        if existing and existing.payload_fingerprint != fingerprint:
            raise XlsxCommitConflictFingerprint(operation_key)
        if existing:
            return existing, True
        raise
    return attempt, False


def _record_op(
    db: Session,
    attempt: IngestionCommitAttempt,
    op_key: str,
    status: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    error_message: str | None = None,
    details: dict | None = None,
) -> IngestionCommitOperation:
    op = IngestionCommitOperation(
        attempt_id=attempt.id,
        op_key=op_key,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        error_message=error_message,
        details_json=json.dumps(details, default=str) if details else None,
    )
    db.add(op)
    db.flush()
    return op


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------


@dataclass
class XlsxCommitResult:
    attempt_id: int
    document_id: int
    status: str
    operations: list[dict]


def commit_xlsx(
    db: Session,
    document_id: int,
    *,
    actor_id: str,
    operation_key: str | None = None,
    quarantine_path: "Path | None" = None,  # noqa: F821
) -> XlsxCommitResult:
    """Commit XLSX ordine:
    1. store_document (promote bytes)
    2. create_order DRAFT
    3. add_item(s) best-effort
    4. link_document
    Ledger idempotente por operation_key + fingerprint.
    """
    from pathlib import Path

    doc = get_document_detail(db, document_id)

    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )
    if open_errors > 0:
        raise XlsxCommitBlockedByIssues(open_errors)

    fingerprint = _compute_fingerprint(db, document_id)
    op_key = operation_key or f"xlsx_commit_{document_id}"

    attempt, is_existing = _get_or_create_attempt(
        db,
        document_id=document_id,
        operation_key=op_key,
        fingerprint=fingerprint,
        actor_id=actor_id,
    )

    if is_existing:
        ops_out = [
            {"op_key": op.op_key, "status": op.status, "entity_type": op.entity_type, "entity_id": op.entity_id}
            for op in attempt.operations
        ]
        return XlsxCommitResult(
            attempt_id=attempt.id,
            document_id=document_id,
            status=attempt.status,
            operations=ops_out,
        )

    try:
        from app.ingestion.metrics_commands import record_commit_attempt, record_commit_complete
        record_commit_attempt(
            db,
            adapter_id=doc.adapter_id,
            adapter_version=doc.adapter_version,
            document_id=document_id,
            is_retry=False,
        )
    except Exception:
        pass

    ops_out: list[dict] = []
    overall_status = "SUCCEEDED"

    # 1. store_document
    promoted_doc_id: int | None = None
    try:
        if quarantine_path:
            occ = db.query(
                __import__("app.ingestion.models", fromlist=["IngestionOccurrence"]).IngestionOccurrence
            ).get(doc.occurrence_id)
            if occ and occ.blob and occ.blob.storage_path:
                path_obj = quarantine_storage.resolve_quarantine_path(
                    quarantine_path, occ.blob.storage_path
                )
                if path_obj and path_obj.is_file():
                    pdoc = documents_public.store_document(
                        db,
                        actor_id=actor_id,
                        filename=occ.original_filename,
                        content=path_obj.read_bytes(),
                        mime_type=occ.detected_mime or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        source_ref=f"ingestion_occurrence:{doc.occurrence_id}",
                    )
                    promoted_doc_id = pdoc.id
        _record_op(db, attempt, "store_document", "SUCCEEDED", "document", str(promoted_doc_id))
        ops_out.append({"op_key": "store_document", "status": "SUCCEEDED", "entity_type": "document", "entity_id": str(promoted_doc_id)})
    except Exception as exc:
        _record_op(db, attempt, "store_document", "FAILED", error_message=str(exc))
        ops_out.append({"op_key": "store_document", "status": "FAILED"})
        # Non-critical — continue

    # 2. create_order DRAFT
    supplier_id_str = _field_value(doc, "supplier_id_catalog")
    supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None
    order_number = _field_value(doc, "order_number")
    currency = _field_value(doc, "currency") or "EUR"

    order_id: int | None = None
    if supplier_id and order_number:
        try:
            order = orders_public.create_order(
                db,
                actor_id=actor_id,
                code=order_number,
                supplier_id=supplier_id,
                currency=currency,
            )
            order_id = order.id
            _record_op(db, attempt, "create_order", "SUCCEEDED", "order", str(order_id))
            ops_out.append({"op_key": "create_order", "status": "SUCCEEDED", "entity_type": "order", "entity_id": str(order_id)})
        except Exception as exc:
            _record_op(db, attempt, "create_order", "FAILED", error_message=str(exc))
            ops_out.append({"op_key": "create_order", "status": "FAILED"})
            overall_status = "PARTIAL"
    else:
        _record_op(db, attempt, "create_order", "SKIPPED", details={"reason": "missing_supplier_or_order_number"})
        ops_out.append({"op_key": "create_order", "status": "SKIPPED"})

    # 3. add_item(s) best-effort (only if order created)
    if order_id:
        for row in (doc.rows or []):
            cells = json.loads(row.cells_json or "{}")
            sku = _cell_value(cells, "sku")
            qty_str = _cell_value(cells, "quantity")
            price_str = _cell_value(cells, "invoice_price")
            if not sku or not qty_str:
                continue
            try:
                qty = Decimal(qty_str)
                unit_price = Decimal(price_str) if price_str else Decimal("0")
                product_id_str = _cell_value(cells, "product_id_catalog")
                product_id = int(product_id_str) if product_id_str and product_id_str.isdigit() else None
                orders_public.add_order_item(
                    db,
                    actor_id=actor_id,
                    order_id=order_id,
                    product_id=product_id,
                    sku=sku,
                    description=sku,
                    quantity=qty,
                    unit_price=unit_price,
                    currency=currency,
                )
                k = f"add_item_{row.row_index}"
                _record_op(db, attempt, k, "SUCCEEDED", "order_item")
                ops_out.append({"op_key": k, "status": "SUCCEEDED"})
            except Exception as exc:
                k = f"add_item_{row.row_index}"
                _record_op(db, attempt, k, "FAILED", error_message=str(exc))
                ops_out.append({"op_key": k, "status": "FAILED"})
                # best-effort — don't change overall status for item failures

    # 4. link_document
    if order_id and promoted_doc_id:
        try:
            documents_public.link_document(
                db,
                actor_id=actor_id,
                document_id=promoted_doc_id,
                entity_type="order",
                entity_id=str(order_id),
            )
            _record_op(db, attempt, "link_document", "SUCCEEDED", "document_link")
            ops_out.append({"op_key": "link_document", "status": "SUCCEEDED"})
        except Exception as exc:
            _record_op(db, attempt, "link_document", "FAILED", error_message=str(exc))
            ops_out.append({"op_key": "link_document", "status": "FAILED"})
            if overall_status == "SUCCEEDED":
                overall_status = "PARTIAL"

    attempt.status = overall_status
    db.flush()

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(document_id),
        action="xlsx_committed",
        reason_code="INGEST_XLSX_COMMIT",
        details=json.dumps({"status": overall_status, "order_id": order_id}),
    )

    try:
        from app.ingestion.metrics_commands import record_commit_complete
        record_commit_complete(
            db,
            adapter_id=doc.adapter_id,
            adapter_version=doc.adapter_version,
            document_id=document_id,
            status=overall_status,
            op_count=len(ops_out),
            failed_ops=sum(1 for op in ops_out if op.get("status") == "FAILED"),
        )
    except Exception:
        pass

    return XlsxCommitResult(
        attempt_id=attempt.id,
        document_id=document_id,
        status=overall_status,
        operations=ops_out,
    )
