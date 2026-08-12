"""Ingestion commit commands — J3-I3 / RUX-3B-2a.

Preview: computa digest das operações que SERIAM executadas (sem escrever owners).
Commit: promove Document + cria Order DRAFT via APIs públicas + ledger idempotente.

Dual-auth na route: ingestion:commit + orders:write; se create_supplier no preview,
também catalog:write.

Tudo-ou-nada (RUX-2R-b): sem savepoint. A primeira operação que falhar levanta
``CommitOperationFailed``; a route faz rollback e grava a trilha da falha fora da
transação (``commit_failure``). Só há ``uow.commit()`` quando todas as operações
terminam SUCCEEDED — logo este caminho não produz mais PARTIAL.

Q3=(B): linhas sem Product → COMMITMENT (external_code/descrição/qty/unit/preço);
Product resolvido no IR → PRODUCT. create_supplier só com intent explícito no IR.

Regras de idempotência:
- Mesmo operation_key + mesmo fingerprint + SUCCEEDED → retorna attempt existente.
- Mesmo operation_key + mesmo fingerprint + FAILED/UNKNOWN → reexecuta do zero
  (nada de domínio sobreviveu à tentativa anterior).
- Mesmo operation_key + fingerprint diferente → CommitConflictFingerprint (409).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.catalog import public as catalog_public
from app.documents import public as documents_public
from app.ingestion.commit_failure import (
    CommitFailureTrail,
    CommitOperationFailed,
    reset_attempt_ledger,
)
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.ir_models import (
    IngestionDocument,
    IngestionField,
    IngestionReviewChange,
    IngestionRow,
)
from app.ingestion.staging_queries import get_document_detail
from app.orders import public as orders_public
from app.ingestion import storage as quarantine_storage


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class CommitConflictFingerprint(IngestionError):
    def __init__(self, operation_key: str) -> None:
        super().__init__(
            f"operation_key '{operation_key}' já existe com fingerprint diferente — 409",
            code="commit_conflict_fingerprint",
        )


class CommitBlockedByIssues(IngestionError):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} issue(s) OPEN com severity ERROR bloqueiam o commit",
            code="commit_blocked_by_issues",
        )


class CommitAttemptNotFound(IngestionError):
    def __init__(self, attempt_id: int) -> None:
        super().__init__(
            f"CommitAttempt {attempt_id} não encontrado",
            code="commit_attempt_not_found",
        )


class CommitDocumentNotReady(IngestionError):
    def __init__(self, doc_id: int) -> None:
        super().__init__(
            f"Documento {doc_id} não está em status READY para commit",
            code="commit_document_not_ready",
        )


class CommitSupplierLinkRequired(IngestionError):
    """409: fornecedor já existe no catálogo, mas o matcher não vinculou — pendência humana."""

    def __init__(self, *, name: str | None, supplier_id: int | None = None) -> None:
        detail = f"id={supplier_id}" if supplier_id is not None else f"name={name!r}"
        super().__init__(
            (
                "Fornecedor já existe no catálogo e não foi vinculado no IR — "
                f"vincule manualmente ({detail})"
            ),
            code="commit_supplier_link_required",
        )


class CommitOrderCodeExists(IngestionError):
    """409: código do pedido já existe — operador abre o existente ou muda o código."""

    def __init__(self, *, order_code: str, order_id: int) -> None:
        super().__init__(
            f"O pedido {order_code} já existe no sistema.",
            code="commit_order_code_exists",
        )
        self.order_code = order_code
        self.order_id = order_id


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------

def _compute_fingerprint(db: Session, document_id: int) -> str:
    """SHA-256 dos campos/rows efetivos do documento IR."""
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
# Helpers to read IR fields
# ---------------------------------------------------------------------------

def _field_value(doc: IngestionDocument, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _document_order_number(doc: IngestionDocument) -> str | None:
    """Número impresso no documento (fonte de external_ref / vínculo Fattura).

    Usa raw/normalized de ``order_number`` — ignora corrected_value.
    Correção de código interno vai em ``order_code``, não aqui.
    """
    for f in doc.fields or []:
        if f.field_key == "order_number":
            val = f.normalized_value or f.raw_value
            return val.strip() if val else None
    return None


def _order_code(doc: IngestionDocument) -> str | None:
    """Identificador interno Order.code — editável via campo ``order_code``."""
    override = _field_value(doc, "order_code")
    if override and str(override).strip():
        return str(override).strip()
    # Fallback: número do documento (sem correção de order_number)
    return _document_order_number(doc)


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
class PreviewOperation:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class PreviewResult:
    document_id: int
    fingerprint: str
    operations: list[PreviewOperation]
    open_error_count: int
    can_commit: bool
    can_create_order: bool = False
    blocking_reasons: list[str] = field(default_factory=list)
    human_summary: str = ""
    readiness_derived: bool = False


def _pending_create_supplier(doc) -> dict | None:
    raw = _field_value(doc, "pending_create_supplier")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict) and data.get("name"):
        return data
    return None


def preview_commit(db: Session, document_id: int) -> PreviewResult:
    """Calcula digest e lista de operações sem escrever nada nos owners.

    RUX-3B-2a: linhas sem Product viram add_item(COMMITMENT); create_supplier
    só com intent explícito no IR; ordem canônica do preview:
    create_supplier → store_document → create_order → add_item* → link_document.
    """
    doc = get_document_detail(db, document_id)

    fingerprint = _compute_fingerprint(db, document_id)

    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )

    ops: list[PreviewOperation] = []
    blocking: list[str] = []

    supplier_id_str = _field_value(doc, "supplier_id_catalog")
    supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None
    pending_supplier = _pending_create_supplier(doc)

    order_number = _document_order_number(doc)
    order_code = _order_code(doc)
    order_date_str = _field_value(doc, "order_date")
    currency = _field_value(doc, "currency") or "EUR"

    # Intent explícito: create_supplier só aparece se pending e ainda sem vínculo.
    if pending_supplier and not supplier_id:
        ops.append(
            PreviewOperation(
                op_key="create_supplier",
                description=f"Criar fornecedor '{pending_supplier.get('name')}' no catálogo",
                entity_type="supplier",
                params=dict(pending_supplier),
            )
        )

    ops.append(
        PreviewOperation(
            op_key="store_document",
            description="Promover bytes da quarantine para Documents",
            entity_type="document",
            params={"occurrence_id": doc.occurrence_id},
        )
    )

    effective_supplier = supplier_id or (True if pending_supplier else None)

    if effective_supplier and order_code and order_number:
        ops.append(
            PreviewOperation(
                op_key="create_order",
                description=(
                    f"Criar Order DRAFT code={order_code} "
                    f"external_ref={order_number} "
                    f"supplier_id={supplier_id or '(após create_supplier)'}"
                ),
                entity_type="order",
                params={
                    "code": order_code,
                    "external_ref": order_number,
                    "supplier_id": supplier_id,
                    "currency": currency,
                    "order_date": order_date_str,
                    "pending_create_supplier": bool(pending_supplier and not supplier_id),
                },
            )
        )
        add_item_count = 0
        for row in sorted(doc.rows or [], key=lambda r: r.row_index):
            cells = _row_cells(row)
            sku = _cell_value(cells, "sku")
            product_id_str = _cell_value(cells, "product_id_catalog")
            product_id = (
                int(product_id_str) if product_id_str and product_id_str.isdigit() else None
            )
            qty = _cell_value(cells, "quantity")
            price = _cell_value(cells, "unit_price")
            unit = _cell_value(cells, "unit")
            description = _cell_value(cells, "description")
            if not qty:
                ops.append(
                    PreviewOperation(
                        op_key=f"skip_item_{row.row_index}",
                        description=(
                            f"Linha {row.row_index} (SKU={sku}) ignorada: quantidade ausente"
                        ),
                        entity_type=None,
                        params={"sku": sku},
                    )
                )
                blocking.append(f"Quantidade ausente na linha {row.row_index} (SKU={sku})")
                continue

            if product_id is not None:
                # Q3=(B) exceção: EAN/SKU resolvido → PRODUCT
                ops.append(
                    PreviewOperation(
                        op_key=f"add_item_{row.row_index}",
                        description=f"Adicionar item PRODUCT SKU={sku} qty={qty}",
                        entity_type="order_item",
                        params={
                            "line_kind": "PRODUCT",
                            "product_id": product_id,
                            "quantity": qty,
                            "unit_price": price,
                            "unit": unit,
                            "external_code": sku,
                            "description": description,
                        },
                    )
                )
            else:
                # Compromisso do documento — sem Product; unit/preço do IR
                ops.append(
                    PreviewOperation(
                        op_key=f"add_item_{row.row_index}",
                        description=(
                            f"Adicionar item COMMITMENT code={sku} qty={qty} unit={unit}"
                        ),
                        entity_type="order_item",
                        params={
                            "line_kind": "COMMITMENT",
                            "product_id": None,
                            "external_code": sku,
                            "description": description,
                            "quantity": qty,
                            "unit_price": price,
                            "unit": unit,
                        },
                    )
                )
            add_item_count += 1

        ops.append(
            PreviewOperation(
                op_key="link_document",
                description="Vincular Document à Order",
                entity_type="document_link",
                params={"entity_type": "order"},
            )
        )
        if add_item_count == 0:
            blocking.append("Pedido sem linhas adicionáveis (nenhuma quantidade válida)")
    else:
        reasons = []
        if not effective_supplier:
            reasons.append("supplier_id ausente (vincular ou confirmar criar fornecedor)")
            blocking.append("Fornecedor não vinculado nem marcado para criar")
        if not order_number:
            reasons.append("order_number ausente no IR")
            blocking.append("Número do pedido ausente")
        if not order_code:
            reasons.append("código do pedido ausente")
            blocking.append("Código do pedido ausente")
        if reasons:
            if len(reasons) == 1 and not effective_supplier:
                skip_desc = "Order não criada: fornecedor ausente"
            elif len(reasons) == 1 and not order_number:
                skip_desc = "Order não criada: número do pedido ausente"
            else:
                skip_desc = "Order não criada: " + "; ".join(reasons)
            ops.append(
                PreviewOperation(
                    op_key="skip_order",
                    description=skip_desc,
                    entity_type=None,
                    params={
                        "supplier_id": supplier_id,
                        "order_number": order_number,
                        "order_code": order_code,
                        "pending_create_supplier": bool(pending_supplier),
                        "missing_supplier": not bool(effective_supplier),
                        "missing_order_number": not bool(order_number),
                    },
                )
            )

    has_skip_order = any(o.op_key == "skip_order" for o in ops)
    has_skip_item = any(o.op_key.startswith("skip_item_") for o in ops)
    has_add_item = any(o.op_key.startswith("add_item_") for o in ops)
    can_create_order = (
        (not has_skip_order)
        and open_errors == 0
        and not has_skip_item
        and has_add_item
    )
    readiness_derived = can_create_order
    can_commit = readiness_derived and open_errors == 0

    if open_errors:
        blocking.append(f"{open_errors} erro(s) matemáticos/estruturais abertos")

    if can_create_order:
        human_summary = f"Pronto para criar pedido rascunho {order_code}."
    elif has_skip_order:
        missing_supplier = not bool(effective_supplier)
        missing_number = not bool(order_number)
        if missing_supplier and missing_number:
            human_summary = "Pedido não será criado até resolver fornecedor e número."
        elif missing_supplier:
            human_summary = "Pedido não será criado até resolver o fornecedor."
        else:
            human_summary = "Pedido não será criado até informar o número do pedido."
    elif has_skip_item or not has_add_item:
        human_summary = "Há linhas sem quantidade — corrija antes de criar o pedido."
    else:
        human_summary = "Revise pendências antes de criar o pedido."

    return PreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        operations=ops,
        open_error_count=open_errors,
        can_commit=can_commit,
        can_create_order=can_create_order,
        blocking_reasons=blocking,
        human_summary=human_summary,
        readiness_derived=readiness_derived,
    )


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

def _record_op(
    db: Session,
    attempt: IngestionCommitAttempt,
    op_key: str,
    *,
    status: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    error_message: str | None = None,
    details_json: str | None = None,
) -> IngestionCommitOperation:
    existing = (
        db.query(IngestionCommitOperation)
        .filter(
            IngestionCommitOperation.attempt_id == attempt.id,
            IngestionCommitOperation.op_key == op_key,
        )
        .first()
    )
    if existing is not None:
        existing.status = status
        existing.entity_type = entity_type
        existing.entity_id = entity_id
        existing.error_message = error_message
        existing.details_json = details_json
        db.flush()
        return existing
    op = IngestionCommitOperation(
        attempt_id=attempt.id,
        op_key=op_key,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        error_message=error_message,
        details_json=details_json,
    )
    db.add(op)
    db.flush()
    return op


def execute_commit(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
    pending_files: list[Path] | None = None,
) -> IngestionCommitAttempt:
    """Executa commit tudo-ou-nada: promote document + create Order DRAFT.

    Sem savepoint: a primeira falha levanta ``CommitOperationFailed`` e a route
    reverte a transação inteira. O arquivo do documento é escrito em área
    temporária e só é promovido pela route depois do commit de banco.

    - Mesma operation_key + mesmo fingerprint + SUCCEEDED → attempt existente.
    - Mesma operation_key + mesmo fingerprint + FAILED/UNKNOWN → reexecuta do zero.
    - Mesma operation_key + fingerprint diferente → CommitConflictFingerprint.
    """
    from app.ingestion.models import IngestionOccurrence

    doc = get_document_detail(db, document_id)

    open_errors = [i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"]
    if open_errors:
        raise CommitBlockedByIssues(len(open_errors))

    preview = preview_commit(db, document_id)
    if not preview.readiness_derived or not preview.can_commit:
        raise CommitDocumentNotReady(document_id)

    fingerprint = _compute_fingerprint(db, document_id)

    existing = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing is not None:
        if existing.payload_fingerprint != fingerprint:
            raise CommitConflictFingerprint(operation_key)
        if existing.status == "SUCCEEDED":
            return existing
        attempt = existing
        attempt.actor_id = actor_id
        reset_attempt_ledger(db, attempt)
    else:
        attempt = IngestionCommitAttempt(
            document_id=document_id,
            operation_key=operation_key,
            payload_fingerprint=fingerprint,
            status="UNKNOWN",
            actor_id=actor_id,
        )
        try:
            db.add(attempt)
            db.flush()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(IngestionCommitAttempt)
                .filter(IngestionCommitAttempt.operation_key == operation_key)
                .first()
            )
            if existing is None:
                raise CommitConflictFingerprint(operation_key)
            if existing.payload_fingerprint != fingerprint:
                raise CommitConflictFingerprint(operation_key)
            if existing.status == "SUCCEEDED":
                return existing
            attempt = existing
            attempt.actor_id = actor_id
            reset_attempt_ledger(db, attempt)

    succeeded_ops: list[str] = []
    pending = pending_files if pending_files is not None else []

    def _fail(op_key: str, exc: Exception) -> None:
        message = str(exc)[:512] or exc.__class__.__name__
        trail = CommitFailureTrail(
            document_id=document_id,
            operation_key=operation_key,
            payload_fingerprint=fingerprint,
            actor_id=actor_id,
            failed_op_key=op_key,
            error_message=message,
            rolled_back_ops=list(succeeded_ops),
            context={"doc_type": "ORDINE_COMPRA"},
        )
        raise CommitOperationFailed(op_key, message, trail=trail) from exc

    promoted_doc_id: int | None = None
    order_id: int | None = None
    order_version: int = 1
    row_product_ids: dict[int, int] = {}

    supplier_id_str = _field_value(doc, "supplier_id_catalog")
    supplier_id = (
        int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None
    )
    pending_supplier = _pending_create_supplier(doc)

    # --- create_supplier antes de store_document (preview order; falha sem FS) ---
    if supplier_id is None and pending_supplier:
        supplier_id = _execute_create_supplier(
            db,
            attempt=attempt,
            pending_supplier=pending_supplier,
            succeeded_ops=succeeded_ops,
            fail=_fail,
        )

    order_number = _document_order_number(doc)
    order_code = _order_code(doc)
    # D7/RUX-3E: código interno editável (order_code); external_ref = número do PDF.
    # Colisão detectada ANTES de store_document — nada no disco.
    # Também reconhece legado ING-<n> (commits anteriores ao D7).
    if order_code:
        code_norm = order_code.strip()
        existing_order = orders_public.get_order_by_code(db, code_norm)
        if existing_order is None and not code_norm.upper().startswith("ING-"):
            existing_order = orders_public.get_order_by_code(db, f"ING-{code_norm}")
        if existing_order is not None:
            raise CommitOrderCodeExists(
                order_code=existing_order.code,
                order_id=existing_order.id,
            )

    # --- store_document ---
    try:
        occ = db.get(IngestionOccurrence, doc.occurrence_id)
        if occ is None or occ.blob is None or occ.blob.physical_status != "PRESENT":
            raise ValueError("Blob não disponível")
        blob_path = quarantine_storage.resolve_quarantine_path(
            quarantine_path, occ.blob.storage_path
        )
        if blob_path is None or not blob_path.is_file():
            raise ValueError("Arquivo de quarantine não encontrado")
        pdf_bytes = blob_path.read_bytes()
        promoted_staging = documents_public.store_document_pending(
            db,
            attachments_path=attachments_path,
            actor_id=actor_id,
            filename=occ.original_filename or f"ordine_{document_id}.pdf",
            content=pdf_bytes,
            mime_type=occ.detected_mime or "application/pdf",
            pending_files=pending,
        )
        promoted_doc_id = promoted_staging.id
    except Exception as exc:
        _fail("store_document", exc)
    _record_op(
        db,
        attempt,
        "store_document",
        status="SUCCEEDED",
        entity_type="document",
        entity_id=str(promoted_doc_id),
    )
    succeeded_ops.append("store_document")

    # Q3=(B): sem create_product; product_id resolvido → PRODUCT; senão COMMITMENT.
    for row in sorted(doc.rows or [], key=lambda r: r.row_index):
        cells = _row_cells(row)
        product_id_str = _cell_value(cells, "product_id_catalog")
        product_id = (
            int(product_id_str) if product_id_str and product_id_str.isdigit() else None
        )
        if product_id is not None:
            row_product_ids[row.row_index] = product_id

    order_number = _document_order_number(doc)
    order_code = _order_code(doc)
    currency = _field_value(doc, "currency") or "EUR"
    order_date_str = _field_value(doc, "order_date")
    order_date = None
    if order_date_str:
        try:
            order_date = date.fromisoformat(order_date_str)
        except ValueError:
            order_date = None

    # --- create_order ---
    if supplier_id is None or not order_code or not order_number:
        reasons = []
        if supplier_id is None:
            reasons.append("supplier_id ausente")
        if not order_number:
            reasons.append("order_number ausente")
        if not order_code:
            reasons.append("order_code ausente")
        if supplier_id is None and not order_number:
            skip_reason = "fornecedor e número ausentes"
        elif supplier_id is None:
            skip_reason = "fornecedor ausente"
        elif not order_number:
            skip_reason = "número do pedido ausente"
        else:
            skip_reason = "código do pedido ausente"
        _record_op(
            db,
            attempt,
            "create_order",
            status="SKIPPED",
            details_json=json.dumps(
                {
                    "reason": skip_reason,
                    "supplier_id": supplier_id,
                    "order_number": order_number,
                    "order_code": order_code,
                    "detail_codes": reasons,
                }
            ),
        )
    else:
        order = None
        try:
            order = orders_public.create_order(
                db,
                code=order_code,
                supplier_id=supplier_id,
                created_by_actor_id=actor_id,
                currency=currency,
                order_date=order_date,
                source_system="INGESTION",
                notes=f"Criada via ingestão — documento IR {document_id}",
                external_ref=order_number,
            )
            order_id = order.id
            order_version = order.version
        except Exception as exc:
            _fail("create_order", exc)
        _record_op(
            db,
            attempt,
            "create_order",
            status="SUCCEEDED",
            entity_type="order",
            entity_id=str(order_id),
            details_json=json.dumps(
                {
                    "code": order.code,
                    "external_ref": order.external_ref,
                    "version": order_version,
                }
            ),
        )
        succeeded_ops.append("create_order")

    # --- add_items (antes de link no preview; link pode vir depois) ---
    if order_id is not None:
        refreshed = orders_public.get_order(db, order_id)
        if refreshed:
            order_version = refreshed.version
        for row in sorted(doc.rows or [], key=lambda r: r.row_index):
            cells = _row_cells(row)
            sku = _cell_value(cells, "sku") or f"row_{row.row_index}"
            description = _cell_value(cells, "description") or sku
            product_id = row_product_ids.get(row.row_index)
            qty_str = _cell_value(cells, "quantity")
            price_str = _cell_value(cells, "unit_price")
            unit = _cell_value(cells, "unit")
            op_key = f"add_item_{row.row_index}"

            if not qty_str:
                _record_op(
                    db,
                    attempt,
                    op_key,
                    status="SKIPPED",
                    details_json=json.dumps({"reason": "qty ausente", "sku": sku}),
                )
                continue

            try:
                if product_id is not None:
                    orders_public.add_item(
                        db,
                        order_id,
                        expected_version=order_version,
                        product_id=product_id,
                        quantity=qty_str,
                        unit_price=price_str,
                        unit=unit,
                        line_kind="PRODUCT",
                        external_code=sku,
                    )
                    line_kind = "PRODUCT"
                else:
                    orders_public.add_item(
                        db,
                        order_id,
                        expected_version=order_version,
                        quantity=qty_str,
                        unit_price=price_str,
                        unit=unit,
                        line_kind="COMMITMENT",
                        external_code=sku,
                        description=description,
                    )
                    line_kind = "COMMITMENT"
                refreshed = orders_public.get_order(db, order_id)
                if refreshed:
                    order_version = refreshed.version
            except Exception as exc:
                _fail(op_key, exc)
            _record_op(
                db,
                attempt,
                op_key,
                status="SUCCEEDED",
                entity_type="order_item",
                details_json=json.dumps(
                    {
                        "sku": sku,
                        "product_id": product_id,
                        "line_kind": line_kind,
                        "unit": unit,
                    }
                ),
            )
            succeeded_ops.append(op_key)

    # --- link_document ---
    if promoted_doc_id is not None and order_id is not None:
        try:
            documents_public.link_document(
                db,
                document_id=promoted_doc_id,
                entity_type="order",
                entity_id=str(order_id),
                role="source",
            )
        except Exception as exc:
            _fail("link_document", exc)
        _record_op(
            db,
            attempt,
            "link_document",
            status="SUCCEEDED",
            entity_type="document_link",
            entity_id=f"{promoted_doc_id}→order:{order_id}",
        )
        succeeded_ops.append("link_document")

    # --- link ingestion IR to promoted document ---
    if promoted_doc_id is not None:
        try:
            documents_public.link_document(
                db,
                document_id=promoted_doc_id,
                entity_type="ingestion_document",
                entity_id=str(document_id),
                role="ingestion_ir",
            )
        except Exception as exc:
            _fail("link_ingestion_document", exc)
        _record_op(
            db,
            attempt,
            "link_ingestion_document",
            status="SUCCEEDED",
            entity_type="document_link",
            entity_id=f"{promoted_doc_id}→ingestion_document:{document_id}",
        )
        succeeded_ops.append("link_ingestion_document")

    attempt.status = "SUCCEEDED"
    # Documento que gerou pedido não fica REJECTED / "em aberto" desonesto.
    if "create_order" in succeeded_ops:
        doc = get_document_detail(db, document_id)
        if doc is not None and doc.review_status != "READY":
            prev = doc.review_status
            doc.review_status = "READY"
            doc.version = int(doc.version) + 1
            db.add(
                IngestionReviewChange(
                    document_id=doc.id,
                    target_type="DOCUMENT",
                    target_id=doc.id,
                    actor_id=actor_id,
                    previous_review_status=prev,
                    new_review_status="READY",
                    reason="commit_create_order_succeeded",
                )
            )
    db.flush()

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_completed",
        reason_code="INGEST_COMMIT_DONE",
        details=json.dumps(
            {
                "document_id": document_id,
                "status": attempt.status,
                "succeeded_ops": succeeded_ops,
                "order_id": order_id,
                "promoted_doc_id": promoted_doc_id,
            }
        ),
    )
    return attempt


def _execute_create_supplier(
    db: Session,
    *,
    attempt: IngestionCommitAttempt,
    pending_supplier: dict,
    succeeded_ops: list[str],
    fail,
) -> int:
    """Cria fornecedor com intent explícito; trata os dois conflitos 409.

    1) Ledger já tem create_supplier SUCCEEDED → devolve entity_id (não rechama).
    2) Fornecedor já existe (código/nome) e matcher não vinculou →
       ``CommitSupplierLinkRequired`` (pendência humana vincular).
    """
    # Caso 1: retry — ledger já gravou sucesso desta op (não rechama create).
    prior = (
        db.query(IngestionCommitOperation)
        .filter(
            IngestionCommitOperation.attempt_id == attempt.id,
            IngestionCommitOperation.op_key == "create_supplier",
            IngestionCommitOperation.status == "SUCCEEDED",
        )
        .first()
    )
    if prior is not None and prior.entity_id and str(prior.entity_id).isdigit():
        supplier_id = int(prior.entity_id)
        if "create_supplier" not in succeeded_ops:
            succeeded_ops.append("create_supplier")
        return supplier_id

    name = str(pending_supplier.get("name") or "").strip()
    code = pending_supplier.get("code")
    code_norm = code.strip() if isinstance(code, str) and code.strip() else None

    # Caso 2a: código já existe → matcher falhou; pendência humana vincular.
    if code_norm:
        existing_by_code = catalog_public.get_supplier_by_code(db, code_norm)
        if existing_by_code is not None:
            raise CommitSupplierLinkRequired(name=name, supplier_id=existing_by_code.id)

    # Caso 2b: nome exato já existe → não create silencioso; vincular.
    if name:
        candidates = catalog_public.list_suppliers(db, q=name, limit=20)
        exact = [
            s for s in candidates if (s.name or "").strip().lower() == name.lower()
        ]
        if exact:
            raise CommitSupplierLinkRequired(name=name, supplier_id=exact[0].id)

    try:
        created = catalog_public.create_supplier(
            db,
            name=name,
            code=code_norm,
            country_code=pending_supplier.get("country_code") or "IT",
        )
        supplier_id = created.id
    except catalog_public.SupplierCodeDuplicate as exc:
        existing = (
            catalog_public.get_supplier_by_code(db, code_norm) if code_norm else None
        )
        if existing is not None:
            raise CommitSupplierLinkRequired(name=name, supplier_id=existing.id) from exc
        fail("create_supplier", exc)
        raise  # unreachable — fail raises
    except CommitSupplierLinkRequired:
        raise
    except Exception as exc:
        fail("create_supplier", exc)
        raise

    _record_op(
        db,
        attempt,
        "create_supplier",
        status="SUCCEEDED",
        entity_type="supplier",
        entity_id=str(supplier_id),
        details_json=json.dumps(pending_supplier, ensure_ascii=False),
    )
    succeeded_ops.append("create_supplier")
    return supplier_id
