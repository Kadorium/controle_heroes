"""Staging IR commands — J3-I1 (sem commit; Audit na mesma UoW)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.ingestion.errors import (
    DocumentAlreadyExists,
    DocumentDeleteBlocked,
    DocumentLocked,
    DocumentNotFound,
    DocumentRejectBlocked,
    DocumentSetNotFound,
    FieldNotFound,
    IssueJustificationRequired,
    IssueNotFound,
    OccurrenceNotFound,
    OccurrenceNotStored,
    ReextractBlocked,
    RowNotFound,
    SectionNotFound,
    VersionConflict,
)
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.ir_models import (
    DOC_REVIEW_STATUSES,
    ISSUE_SEVERITIES,
    ISSUE_STATUSES,
    ISSUE_TARGET_TYPES,
    TARGET_REVIEW_STATUSES,
    IngestionDocument,
    IngestionDocumentSet,
    IngestionDocumentSetMember,
    IngestionField,
    IngestionIssue,
    IngestionReviewChange,
    IngestionRow,
    IngestionSection,
)
from app.ingestion.models import IngestionOccurrence


def effective_field_value(field: IngestionField) -> str | None:
    if field.review_status == "CORRECTED":
        return field.corrected_value
    if field.normalized_value is not None:
        return field.normalized_value
    return field.raw_value


def _require_doc(db: Session, document_id: int) -> IngestionDocument:
    doc = db.get(IngestionDocument, document_id)
    if doc is None:
        raise DocumentNotFound(document_id)
    return doc


def _assert_unlocked_or_holder(doc: IngestionDocument, actor_id: str) -> None:
    if doc.locked_by_actor_id and doc.locked_by_actor_id != actor_id:
        raise DocumentLocked()


def _bump_doc(doc: IngestionDocument) -> None:
    doc.version = int(doc.version) + 1


def seed_document_from_occurrence(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str,
    doc_type: str = "UNKNOWN",
    adapter_id: str = "contract_stub_v1",
    adapter_version: str = "1",
    fields: list[dict] | None = None,
    rows: list[dict] | None = None,
    sections: list[dict] | None = None,
    issues: list[dict] | None = None,
) -> IngestionDocument:
    occ = db.get(IngestionOccurrence, occurrence_id)
    if occ is None:
        raise OccurrenceNotFound(occurrence_id)
    if occ.status != "STORED":
        raise OccurrenceNotStored(occurrence_id)

    existing = (
        db.query(IngestionDocument)
        .filter(IngestionDocument.occurrence_id == occurrence_id)
        .first()
    )
    if existing is not None:
        raise DocumentAlreadyExists(occurrence_id)

    doc = IngestionDocument(
        occurrence_id=occurrence_id,
        batch_id=occ.batch_id,
        doc_type=doc_type,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        ir_schema_version="1",
        review_status="DRAFT",
        version=1,
        created_by_actor_id=actor_id,
    )
    db.add(doc)
    db.flush()

    section_by_key: dict[str, IngestionSection] = {}
    for i, sec in enumerate(sections or []):
        key = sec["section_key"]
        s = IngestionSection(
            document_id=doc.id,
            section_key=key,
            title=sec.get("title"),
            ordinal=int(sec.get("ordinal", i)),
            review_status="PENDING",
            version=1,
        )
        db.add(s)
        db.flush()
        section_by_key[key] = s

    for fdef in fields or []:
        sk = fdef.get("section_key")
        section_id = section_by_key[sk].id if sk and sk in section_by_key else fdef.get("section_id")
        # Pass-through: None / "" / "0" preserved — never coerce empty→zero
        field = IngestionField(
            document_id=doc.id,
            section_id=section_id,
            field_key=fdef["field_key"],
            value_type=fdef.get("value_type", "string"),
            raw_value=fdef.get("raw_value", None),
            normalized_value=fdef.get("normalized_value", None),
            corrected_value=None,
            locator_json=fdef.get("locator_json"),
            provenance_json=fdef.get("provenance_json"),
            review_status="PENDING",
            version=1,
        )
        db.add(field)

    for rdef in rows or []:
        sk = rdef.get("section_key")
        section_id = section_by_key[sk].id if sk and sk in section_by_key else rdef.get("section_id")
        cells = rdef.get("cells_json")
        if cells is None and "cells" in rdef:
            cells = json.dumps(rdef["cells"], ensure_ascii=False)
        if cells is None:
            cells = "{}"
        row = IngestionRow(
            document_id=doc.id,
            section_id=section_id,
            row_index=int(rdef["row_index"]),
            row_key=rdef.get("row_key"),
            cells_json=cells if isinstance(cells, str) else json.dumps(cells),
            review_status="PENDING",
            version=1,
        )
        db.add(row)

    for idef in issues or []:
        issue = IngestionIssue(
            document_id=doc.id,
            severity=idef.get("severity", "ERROR"),
            code=idef["code"],
            message=idef["message"],
            target_type=idef.get("target_type", "DOCUMENT"),
            target_id=idef.get("target_id"),
            status="OPEN",
            locator_json=idef.get("locator_json"),
        )
        db.add(issue)

    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(doc.id),
        action="document_seeded",
        reason_code="INGEST_IR_SEED",
        details=json.dumps(
            {"occurrence_id": occurrence_id, "doc_type": doc_type, "adapter_id": adapter_id}
        ),
    )
    return doc


def correct_field(
    db: Session,
    *,
    field_id: int,
    actor_id: str,
    corrected_value: str | None,
    expected_version: int,
    reason: str | None = None,
) -> IngestionField:
    field = db.get(IngestionField, field_id)
    if field is None:
        raise FieldNotFound(field_id)
    doc = _require_doc(db, field.document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(field.version) != int(expected_version):
        raise VersionConflict()

    prev = field.corrected_value
    prev_status = field.review_status
    # raw_value and normalized_value untouched
    field.corrected_value = corrected_value
    field.review_status = "CORRECTED"
    field.version = int(field.version) + 1
    _bump_doc(doc)
    if doc.review_status == "DRAFT":
        doc.review_status = "IN_REVIEW"

    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="FIELD",
            target_id=field.id,
            actor_id=actor_id,
            previous_value=prev,
            new_value=corrected_value,
            previous_review_status=prev_status,
            new_review_status="CORRECTED",
            reason=reason,
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_field",
        entity_id=str(field.id),
        action="field_corrected",
        reason_code="INGEST_FIELD_CORRECT",
        details=json.dumps({"document_id": doc.id, "field_key": field.field_key}),
    )
    return field


def restore_field(
    db: Session,
    *,
    field_id: int,
    actor_id: str,
    expected_version: int,
    reason: str | None = None,
) -> IngestionField:
    field = db.get(IngestionField, field_id)
    if field is None:
        raise FieldNotFound(field_id)
    doc = _require_doc(db, field.document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(field.version) != int(expected_version):
        raise VersionConflict()

    prev = field.corrected_value
    prev_status = field.review_status
    field.corrected_value = None
    field.review_status = "PENDING"
    field.version = int(field.version) + 1
    _bump_doc(doc)

    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="FIELD",
            target_id=field.id,
            actor_id=actor_id,
            previous_value=prev,
            new_value=None,
            previous_review_status=prev_status,
            new_review_status="PENDING",
            reason=reason or "restore",
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_field",
        entity_id=str(field.id),
        action="field_restored",
        reason_code="INGEST_FIELD_RESTORE",
        details=json.dumps({"document_id": doc.id}),
    )
    return field


MATH_LINE_EDIT_DIVERGENCE = "MATH_LINE_EDIT_DIVERGENCE"
_MATH_EDIT_TOL = Decimal("0.02")


def _cell_part(cells: dict, key: str, part: str) -> str | None:
    raw = cells.get(key)
    if not isinstance(raw, dict):
        if raw is None:
            return None
        return str(raw).strip() or None
    val = raw.get(part)
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _parse_cell_number(value: str | None) -> Decimal | None:
    if value is None:
        return None
    from app.ingestion.parse_it import parse_it_number

    parsed = parse_it_number(value)
    if parsed is not None:
        return parsed
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _fmt_dec(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def sync_math_line_edit_divergence(
    db: Session,
    *,
    doc: IngestionDocument,
    row: IngestionRow,
    actor_id: str,
) -> None:
    """RUX-3F-POST-3: aviso WARNING se qty×price ≠ line_total impresso no PDF.

    Não bloqueia commit (só ERROR bloqueia). Resolve automaticamente quando
    a matemática volta a bater com o total impresso (raw do PDF).
    """
    try:
        cells = json.loads(row.cells_json or "{}")
    except Exception:
        cells = {}
    if not isinstance(cells, dict):
        return

    qty = _parse_cell_number(_cell_part(cells, "quantity", "normalized"))
    price = _parse_cell_number(_cell_part(cells, "unit_price", "normalized"))
    # Total impresso: raw preservado na extração (UI pode recalcular normalized).
    pdf_total = _parse_cell_number(_cell_part(cells, "line_total", "raw"))
    if pdf_total is None:
        pdf_total = _parse_cell_number(_cell_part(cells, "line_total", "normalized"))

    existing = (
        db.query(IngestionIssue)
        .filter(
            IngestionIssue.document_id == doc.id,
            IngestionIssue.code == MATH_LINE_EDIT_DIVERGENCE,
            IngestionIssue.target_type == "ROW",
            IngestionIssue.target_id == row.id,
            IngestionIssue.status == "OPEN",
        )
        .first()
    )

    if qty is None or price is None or pdf_total is None:
        return

    computed = (qty * price).quantize(Decimal("0.01"))
    diverges = abs(computed - pdf_total) > _MATH_EDIT_TOL

    if diverges:
        message = (
            f"Quantidade editada ({_fmt_dec(qty)}) × preço ({_fmt_dec(price)}) = "
            f"{_fmt_dec(computed)}, difere do total de linha impresso no PDF "
            f"({_fmt_dec(pdf_total)}). Verifique se a correção é intencional."
        )
        if existing is not None:
            existing.message = message
            existing.severity = "WARNING"
            db.flush()
            return
        create_issue(
            db,
            document_id=doc.id,
            actor_id=actor_id,
            severity="WARNING",
            code=MATH_LINE_EDIT_DIVERGENCE,
            message=message,
            target_type="ROW",
            target_id=row.id,
        )
        return

    if existing is not None:
        resolve_issue(
            db,
            issue_id=existing.id,
            actor_id=actor_id,
            status="RESOLVED",
            justification="qty×price alinhado ao total impresso no PDF",
        )


def correct_row(
    db: Session,
    *,
    row_id: int,
    actor_id: str,
    cells_json: str,
    expected_version: int,
    reason: str | None = None,
) -> IngestionRow:
    row = db.get(IngestionRow, row_id)
    if row is None:
        raise RowNotFound(row_id)
    doc = _require_doc(db, row.document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(row.version) != int(expected_version):
        raise VersionConflict()

    prev = row.cells_json
    prev_status = row.review_status
    row.cells_json = cells_json
    row.review_status = "CORRECTED"
    row.version = int(row.version) + 1
    _bump_doc(doc)
    if doc.review_status == "DRAFT":
        doc.review_status = "IN_REVIEW"

    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="ROW",
            target_id=row.id,
            actor_id=actor_id,
            previous_value=prev,
            new_value=cells_json,
            previous_review_status=prev_status,
            new_review_status="CORRECTED",
            reason=reason,
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_row",
        entity_id=str(row.id),
        action="row_corrected",
        reason_code="INGEST_ROW_CORRECT",
        details=json.dumps({"document_id": doc.id}),
    )
    sync_math_line_edit_divergence(db, doc=doc, row=row, actor_id=actor_id)
    return row


def add_row(
    db: Session,
    *,
    document_id: int,
    actor_id: str,
    cells_json: str,
    expected_document_version: int,
    section_id: int | None = None,
    row_key: str | None = None,
    reason: str | None = None,
) -> IngestionRow:
    doc = _require_doc(db, document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(doc.version) != int(expected_document_version):
        raise VersionConflict()

    max_idx = (
        db.query(IngestionRow.row_index)
        .filter(IngestionRow.document_id == doc.id)
        .order_by(IngestionRow.row_index.desc())
        .limit(1)
        .scalar()
    )
    if max_idx is None:
        max_idx = -1
    row = IngestionRow(
        document_id=doc.id,
        section_id=section_id,
        row_index=int(max_idx) + 1,
        row_key=row_key,
        cells_json=cells_json or "{}",
        review_status="CORRECTED",
        version=1,
    )
    db.add(row)
    _bump_doc(doc)
    if doc.review_status == "DRAFT":
        doc.review_status = "IN_REVIEW"
    db.flush()

    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="ROW",
            target_id=row.id,
            actor_id=actor_id,
            previous_value=None,
            new_value=cells_json,
            previous_review_status=None,
            new_review_status="CORRECTED",
            reason=reason or "row_added",
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_row",
        entity_id=str(row.id),
        action="row_added",
        reason_code="INGEST_ROW_ADD",
        details=json.dumps({"document_id": doc.id}),
    )
    return row


def remove_row(
    db: Session,
    *,
    row_id: int,
    actor_id: str,
    expected_version: int,
    reason: str | None = None,
) -> None:
    row = db.get(IngestionRow, row_id)
    if row is None:
        raise RowNotFound(row_id)
    doc = _require_doc(db, row.document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(row.version) != int(expected_version):
        raise VersionConflict()

    prev = row.cells_json
    prev_status = row.review_status
    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="ROW",
            target_id=row.id,
            actor_id=actor_id,
            previous_value=prev,
            new_value=None,
            previous_review_status=prev_status,
            new_review_status="REJECTED",
            reason=reason or "row_removed",
        )
    )
    db.delete(row)
    _bump_doc(doc)
    if doc.review_status == "DRAFT":
        doc.review_status = "IN_REVIEW"
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_row",
        entity_id=str(row_id),
        action="row_removed",
        reason_code="INGEST_ROW_REMOVE",
        details=json.dumps({"document_id": doc.id}),
    )


def review_section(
    db: Session,
    *,
    section_id: int,
    actor_id: str,
    review_status: str,
    expected_version: int,
    reason: str | None = None,
) -> IngestionSection:
    if review_status not in TARGET_REVIEW_STATUSES:
        raise VersionConflict(f"review_status inválido: {review_status}")
    section = db.get(IngestionSection, section_id)
    if section is None:
        raise SectionNotFound(section_id)
    doc = _require_doc(db, section.document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(section.version) != int(expected_version):
        raise VersionConflict()

    prev_status = section.review_status
    section.review_status = review_status
    section.version = int(section.version) + 1
    _bump_doc(doc)

    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="SECTION",
            target_id=section.id,
            actor_id=actor_id,
            previous_value=None,
            new_value=None,
            previous_review_status=prev_status,
            new_review_status=review_status,
            reason=reason,
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_section",
        entity_id=str(section.id),
        action="section_reviewed",
        reason_code="INGEST_SECTION_REVIEW",
        details=json.dumps({"document_id": doc.id, "review_status": review_status}),
    )
    return section


def set_document_review_status(
    db: Session,
    *,
    document_id: int,
    actor_id: str,
    review_status: str,
    expected_version: int,
) -> IngestionDocument:
    if review_status not in DOC_REVIEW_STATUSES:
        raise VersionConflict(f"review_status inválido: {review_status}")
    doc = _require_doc(db, document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(doc.version) != int(expected_version):
        raise VersionConflict()

    if review_status == "REJECTED" and _has_succeeded_create_order(db, document_id):
        raise DocumentRejectBlocked(
            "Esta importação já criou um pedido. Não pode aparecer como rejeitada — "
            "abra o pedido vinculado."
        )

    prev = doc.review_status
    doc.review_status = review_status
    _bump_doc(doc)
    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="DOCUMENT",
            target_id=doc.id,
            actor_id=actor_id,
            previous_review_status=prev,
            new_review_status=review_status,
            reason="set_review_status",
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(doc.id),
        action="document_review_status",
        reason_code="INGEST_DOC_REVIEW",
        details=json.dumps({"review_status": review_status}),
    )
    return doc


def set_order_code_override(
    db: Session,
    *,
    document_id: int,
    actor_id: str,
    order_code: str,
    expected_version: int,
    reason: str | None = None,
) -> IngestionField:
    """Define código interno do pedido (campo IR ``order_code``) sem alterar ``order_number``."""
    code = (order_code or "").strip()
    if not code:
        raise VersionConflict("código do pedido vazio")
    doc = _require_doc(db, document_id)
    _assert_unlocked_or_holder(doc, actor_id)
    if int(doc.version) != int(expected_version):
        raise VersionConflict()

    existing = (
        db.query(IngestionField)
        .filter(
            IngestionField.document_id == document_id,
            IngestionField.field_key == "order_code",
        )
        .first()
    )
    if existing is not None:
        return correct_field(
            db,
            field_id=existing.id,
            actor_id=actor_id,
            corrected_value=code,
            expected_version=existing.version,
            reason=reason or "order_code_override",
        )

    field = IngestionField(
        document_id=doc.id,
        section_id=None,
        field_key="order_code",
        value_type="string",
        raw_value=None,
        normalized_value=None,
        corrected_value=code,
        review_status="CORRECTED",
        version=1,
    )
    db.add(field)
    _bump_doc(doc)
    if doc.review_status == "DRAFT":
        doc.review_status = "IN_REVIEW"
    db.flush()
    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="FIELD",
            target_id=field.id,
            actor_id=actor_id,
            previous_value=None,
            new_value=code,
            previous_review_status=None,
            new_review_status="CORRECTED",
            reason=reason or "order_code_override",
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_field",
        entity_id=str(field.id),
        action="field_corrected",
        reason_code="INGEST_FIELD_CORRECT",
        details=json.dumps({"document_id": doc.id, "field_key": "order_code"}),
    )
    return field


def repair_rejected_with_order(
    db: Session,
    *,
    document_id: int,
    actor_id: str = "system",
) -> IngestionDocument | None:
    """Corrige status desonesto REJECTED quando já existe create_order SUCCEEDED."""
    doc = db.get(IngestionDocument, document_id)
    if doc is None:
        return None
    if doc.review_status != "REJECTED":
        return doc
    if not _has_succeeded_create_order(db, document_id):
        return doc
    prev = doc.review_status
    doc.review_status = "READY"
    _bump_doc(doc)
    db.add(
        IngestionReviewChange(
            document_id=doc.id,
            target_type="DOCUMENT",
            target_id=doc.id,
            actor_id=actor_id,
            previous_review_status=prev,
            new_review_status="READY",
            reason="repair_rejected_after_create_order",
        )
    )
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(doc.id),
        action="document_review_status",
        reason_code="INGEST_DOC_REVIEW_REPAIR",
        details=json.dumps({"review_status": "READY", "from": "REJECTED"}),
    )
    return doc


def lock_document(db: Session, *, document_id: int, actor_id: str) -> IngestionDocument:
    doc = _require_doc(db, document_id)
    if doc.locked_by_actor_id and doc.locked_by_actor_id != actor_id:
        raise DocumentLocked()
    doc.locked_by_actor_id = actor_id
    doc.locked_at = datetime.now(timezone.utc)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(doc.id),
        action="document_locked",
        reason_code="INGEST_DOC_LOCK",
    )
    return doc


def unlock_document(db: Session, *, document_id: int, actor_id: str) -> IngestionDocument:
    doc = _require_doc(db, document_id)
    if doc.locked_by_actor_id and doc.locked_by_actor_id != actor_id:
        raise DocumentLocked("Somente o detentor do lock pode liberar")
    doc.locked_by_actor_id = None
    doc.locked_at = None
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(doc.id),
        action="document_unlocked",
        reason_code="INGEST_DOC_UNLOCK",
    )
    return doc


def create_issue(
    db: Session,
    *,
    document_id: int,
    actor_id: str,
    severity: str,
    code: str,
    message: str,
    target_type: str = "DOCUMENT",
    target_id: int | None = None,
    locator_json: str | None = None,
) -> IngestionIssue:
    if severity not in ISSUE_SEVERITIES:
        raise VersionConflict(f"severity inválida: {severity}")
    if target_type not in ISSUE_TARGET_TYPES:
        raise VersionConflict(f"target_type inválido: {target_type}")
    doc = _require_doc(db, document_id)
    issue = IngestionIssue(
        document_id=doc.id,
        severity=severity,
        code=code,
        message=message,
        target_type=target_type,
        target_id=target_id,
        status="OPEN",
        locator_json=locator_json,
    )
    db.add(issue)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_issue",
        entity_id=str(issue.id),
        action="issue_created",
        reason_code="INGEST_ISSUE_CREATE",
        details=json.dumps({"document_id": doc.id, "code": code}),
    )
    return issue


def resolve_issue(
    db: Session,
    *,
    issue_id: int,
    actor_id: str,
    status: str = "RESOLVED",
    justification: str | None = None,
) -> IngestionIssue:
    from app.ingestion.errors import IssueJustificationRequired

    if status not in ("RESOLVED", "DISMISSED"):
        raise VersionConflict(f"status inválido para resolução: {status}")
    issue = db.get(IngestionIssue, issue_id)
    if issue is None:
        raise IssueNotFound(issue_id)
    if status not in ISSUE_STATUSES:
        raise VersionConflict()

    reason = (justification or "").strip()
    # Dispensar ERROR exige justificativa auditável (RUX-3B-2b).
    if status == "DISMISSED" and issue.severity == "ERROR" and not reason:
        raise IssueJustificationRequired()

    issue.status = status
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_issue",
        entity_id=str(issue.id),
        action="issue_resolved",
        reason_code="INGEST_ISSUE_RESOLVE",
        details=json.dumps(
            {
                "status": status,
                "severity": issue.severity,
                "code": issue.code,
                "justification": reason or None,
            }
        ),
    )
    return issue


def create_document_set(
    db: Session,
    *,
    actor_id: str,
    batch_id: int | None = None,
    projection_key: str | None = None,
    label: str | None = None,
) -> IngestionDocumentSet:
    ds = IngestionDocumentSet(
        batch_id=batch_id,
        projection_key=projection_key,
        label=label,
        created_by_actor_id=actor_id,
    )
    db.add(ds)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document_set",
        entity_id=str(ds.id),
        action="document_set_created",
        reason_code="INGEST_SET_CREATE",
        details=json.dumps({"projection_key": projection_key}),
    )
    return ds


def add_document_to_set(
    db: Session,
    *,
    document_set_id: int,
    document_id: int,
    role: str | None = None,
) -> IngestionDocumentSetMember:
    ds = db.get(IngestionDocumentSet, document_set_id)
    if ds is None:
        raise DocumentSetNotFound(document_set_id)
    doc = _require_doc(db, document_id)
    member = IngestionDocumentSetMember(
        document_set_id=ds.id,
        document_id=doc.id,
        role=role,
    )
    db.add(member)
    doc.document_set_id = ds.id
    db.flush()
    return member


def _has_succeeded_create_order(db: Session, document_id: int) -> bool:
    return get_succeeded_create_order(db, document_id) is not None


def get_succeeded_create_order(
    db: Session, document_id: int
) -> tuple[int, str | None] | None:
    """Retorna (order_id, order_code) se create_order SUCCEEDED; senão None."""
    from app.orders import public as orders_public

    op = (
        db.query(IngestionCommitOperation)
        .join(
            IngestionCommitAttempt,
            IngestionCommitOperation.attempt_id == IngestionCommitAttempt.id,
        )
        .filter(
            IngestionCommitAttempt.document_id == document_id,
            IngestionCommitOperation.op_key == "create_order",
            IngestionCommitOperation.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitOperation.id.desc())
        .first()
    )
    if op is None or not op.entity_id:
        return None
    try:
        order_id = int(op.entity_id)
    except (TypeError, ValueError):
        return None
    order = orders_public.get_order(db, order_id)
    code = order.code if order is not None else None
    return order_id, code


def get_succeeded_create_orders_map(
    db: Session, document_ids: list[int]
) -> dict[int, tuple[int, str | None]]:
    if not document_ids:
        return {}
    from app.orders import public as orders_public

    rows = (
        db.query(
            IngestionCommitAttempt.document_id,
            IngestionCommitOperation.entity_id,
            IngestionCommitOperation.id,
        )
        .join(
            IngestionCommitOperation,
            IngestionCommitOperation.attempt_id == IngestionCommitAttempt.id,
        )
        .filter(
            IngestionCommitAttempt.document_id.in_(document_ids),
            IngestionCommitOperation.op_key == "create_order",
            IngestionCommitOperation.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitOperation.id.desc())
        .all()
    )
    out: dict[int, tuple[int, str | None]] = {}
    for doc_id, entity_id, _op_id in rows:
        if doc_id in out:
            continue
        try:
            order_id = int(entity_id)
        except (TypeError, ValueError):
            continue
        order = orders_public.get_order(db, order_id)
        out[int(doc_id)] = (order_id, order.code if order is not None else None)
    return out


def _supersede_open_issues(
    db: Session,
    doc: IngestionDocument,
    actor_id: str,
) -> list[int]:
    superseded_ids: list[int] = []
    for issue in doc.issues or []:
        if issue.status != "OPEN":
            continue
        issue.status = "RESOLVED"
        superseded_ids.append(issue.id)
    if superseded_ids:
        audit_public.record_event(
            db,
            actor_id=actor_id,
            entity_type="ingestion_document",
            entity_id=str(doc.id),
            action="issues_superseded",
            reason_code="INGEST_REEXTRACT_SUPERSEDE",
            details=json.dumps(
                {
                    "document_id": doc.id,
                    "issue_ids": superseded_ids,
                    "reason": "superseded_by_reextract",
                }
            ),
        )
    return superseded_ids


def _upsert_sections(
    db: Session,
    doc: IngestionDocument,
    sections: list[dict],
) -> dict[str, IngestionSection]:
    existing_by_key = {s.section_key: s for s in doc.sections or []}
    section_by_key: dict[str, IngestionSection] = {}
    for i, sec in enumerate(sections):
        key = sec["section_key"]
        existing = existing_by_key.get(key)
        if existing is not None:
            existing.title = sec.get("title")
            existing.ordinal = int(sec.get("ordinal", i))
            section_by_key[key] = existing
        else:
            s = IngestionSection(
                document_id=doc.id,
                section_key=key,
                title=sec.get("title"),
                ordinal=int(sec.get("ordinal", i)),
                review_status="PENDING",
                version=1,
            )
            db.add(s)
            db.flush()
            section_by_key[key] = s
    return section_by_key


def _apply_field_reextract(
    db: Session,
    doc: IngestionDocument,
    existing: IngestionField,
    fdef: dict,
    actor_id: str,
    section_by_key: dict[str, IngestionSection],
) -> None:
    sk = fdef.get("section_key")
    section_id = (
        section_by_key[sk].id
        if sk and sk in section_by_key
        else fdef.get("section_id", existing.section_id)
    )
    new_raw = fdef.get("raw_value", None)
    raw_unchanged = new_raw == existing.raw_value

    existing.section_id = section_id
    existing.value_type = fdef.get("value_type", existing.value_type)
    existing.raw_value = new_raw
    existing.normalized_value = fdef.get("normalized_value", None)
    existing.locator_json = fdef.get("locator_json")
    existing.provenance_json = fdef.get("provenance_json")

    if raw_unchanged:
        return

    prev_status = existing.review_status
    prev_corrected = existing.corrected_value
    if prev_status in ("CORRECTED", "APPROVED") and prev_corrected is not None:
        existing.review_status = "PENDING"
        existing.version = int(existing.version) + 1
        db.add(
            IngestionReviewChange(
                document_id=doc.id,
                target_type="FIELD",
                target_id=existing.id,
                actor_id=actor_id,
                previous_value=prev_corrected,
                new_value=prev_corrected,
                previous_review_status=prev_status,
                new_review_status="PENDING",
                reason="reextract_raw_changed",
            )
        )
    else:
        existing.corrected_value = None
        existing.review_status = "PENDING"
        existing.version = int(existing.version) + 1


def _merge_row_cells(
    existing_cells: dict,
    new_cells: dict,
) -> tuple[dict, bool]:
    merged: dict = {}
    needs_reconfirm = False
    for col, new_cell in new_cells.items():
        old_cell = existing_cells.get(col, {}) if isinstance(existing_cells.get(col), dict) else {}
        new_raw = new_cell.get("raw")
        old_raw = old_cell.get("raw")
        merged_cell = dict(new_cell)
        if new_raw == old_raw:
            if "corrected" in old_cell:
                merged_cell["corrected"] = old_cell["corrected"]
        else:
            if old_cell.get("corrected") is not None:
                merged_cell["corrected"] = old_cell["corrected"]
                needs_reconfirm = True
    return merged, needs_reconfirm


def replace_document_ir(
    db: Session,
    doc: IngestionDocument,
    actor_id: str,
    *,
    sections: list[dict],
    fields: list[dict],
    rows: list[dict],
    issues: list[dict],
) -> IngestionDocument:
    """Substitui conteúdo IR in-place preservando document id e review_changes."""
    section_by_key = _upsert_sections(db, doc, sections)
    existing_fields = {f.field_key: f for f in doc.fields or []}

    for fdef in fields:
        key = fdef["field_key"]
        existing = existing_fields.get(key)
        if existing is not None:
            _apply_field_reextract(db, doc, existing, fdef, actor_id, section_by_key)
        else:
            sk = fdef.get("section_key")
            section_id = (
                section_by_key[sk].id if sk and sk in section_by_key else fdef.get("section_id")
            )
            field = IngestionField(
                document_id=doc.id,
                section_id=section_id,
                field_key=key,
                value_type=fdef.get("value_type", "string"),
                raw_value=fdef.get("raw_value", None),
                normalized_value=fdef.get("normalized_value", None),
                corrected_value=None,
                locator_json=fdef.get("locator_json"),
                provenance_json=fdef.get("provenance_json"),
                review_status="PENDING",
                version=1,
            )
            db.add(field)

    existing_rows = {r.row_index: r for r in doc.rows or []}
    new_indices = {int(rdef["row_index"]) for rdef in rows}
    for idx, row in existing_rows.items():
        if idx not in new_indices:
            db.delete(row)

    for rdef in rows:
        row_index = int(rdef["row_index"])
        sk = rdef.get("section_key")
        section_id = (
            section_by_key[sk].id if sk and sk in section_by_key else rdef.get("section_id")
        )
        cells = rdef.get("cells_json")
        if cells is None and "cells" in rdef:
            cells = json.dumps(rdef["cells"], ensure_ascii=False)
        if cells is None:
            cells = "{}"
        if not isinstance(cells, str):
            cells = json.dumps(cells, ensure_ascii=False)

        existing = existing_rows.get(row_index)
        if existing is not None:
            try:
                old_cells = json.loads(existing.cells_json or "{}")
            except json.JSONDecodeError:
                old_cells = {}
            try:
                new_cells = json.loads(cells)
            except json.JSONDecodeError:
                new_cells = {}
            merged_cells, needs_reconfirm = _merge_row_cells(old_cells, new_cells)
            prev_status = existing.review_status
            existing.section_id = section_id
            existing.row_key = rdef.get("row_key")
            existing.cells_json = json.dumps(merged_cells, ensure_ascii=False)
            if needs_reconfirm and prev_status in ("CORRECTED", "APPROVED"):
                existing.review_status = "PENDING"
                existing.version = int(existing.version) + 1
                db.add(
                    IngestionReviewChange(
                        document_id=doc.id,
                        target_type="ROW",
                        target_id=existing.id,
                        actor_id=actor_id,
                        previous_value=existing.cells_json,
                        new_value=existing.cells_json,
                        previous_review_status=prev_status,
                        new_review_status="PENDING",
                        reason="reextract_raw_changed",
                    )
                )
        else:
            row = IngestionRow(
                document_id=doc.id,
                section_id=section_id,
                row_index=row_index,
                row_key=rdef.get("row_key"),
                cells_json=cells,
                review_status="PENDING",
                version=1,
            )
            db.add(row)

    for idef in issues or []:
        issue = IngestionIssue(
            document_id=doc.id,
            severity=idef.get("severity", "ERROR"),
            code=idef["code"],
            message=idef["message"],
            target_type=idef.get("target_type", "DOCUMENT"),
            target_id=idef.get("target_id"),
            status="OPEN",
            locator_json=idef.get("locator_json"),
        )
        db.add(issue)

    _bump_doc(doc)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(doc.id),
        action="document_reextracted",
        reason_code="INGEST_REEXTRACT",
        details=json.dumps({"document_id": doc.id}),
    )
    return doc


def reextract_document(
    db: Session,
    *,
    document_id: int,
    actor_id: str,
    quarantine_path: Path,
) -> IngestionDocument:
    """Re-extrai IR do blob original, substituindo conteúdo in-place (RUX-2R)."""
    from app.ingestion import adapter_registry

    doc = _require_doc(db, document_id)
    _assert_unlocked_or_holder(doc, actor_id)

    if _has_succeeded_create_order(db, document_id):
        raise ReextractBlocked(
            document_id,
            "create_order já SUCCEEDED em commit attempt (incl. PARTIAL)",
        )

    entry = adapter_registry.get_adapter(doc.adapter_id)
    if entry.build_payload is None:
        raise ReextractBlocked(
            document_id,
            f"adapter {doc.adapter_id} não suporta reextract",
        )

    _supersede_open_issues(db, doc, actor_id)
    payload = entry.build_payload(
        db,
        occurrence_id=doc.occurrence_id,
        quarantine_path=quarantine_path,
    )

    return replace_document_ir(
        db,
        doc,
        actor_id,
        sections=payload.get("sections") or [],
        fields=payload.get("fields") or [],
        rows=payload.get("rows") or [],
        issues=payload.get("issues") or [],
    )


def hard_delete_document(
    db: Session,
    *,
    document_id: int,
    actor_id: str,
) -> None:
    """Exclui definitivamente a importação (IR) se ainda não criou pedido."""
    doc = _require_doc(db, document_id)
    _assert_unlocked_or_holder(doc, actor_id)

    if _has_succeeded_create_order(db, document_id):
        raise DocumentDeleteBlocked(
            "Esta importação já criou um pedido. O vínculo com o pedido precisa "
            "sobreviver — não é possível excluir."
        )

    # Ledger de tentativas (FAILED/UNKNOWN) — remover para liberar FK RESTRICT
    attempts = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.document_id == document_id)
        .all()
    )
    for attempt in attempts:
        db.delete(attempt)

    # review_changes / set memberships cascade via FK where present
    from app.ingestion.ir_models import IngestionReviewChange, IngestionDocumentSetMember

    db.query(IngestionReviewChange).filter(
        IngestionReviewChange.document_id == document_id
    ).delete(synchronize_session=False)
    db.query(IngestionDocumentSetMember).filter(
        IngestionDocumentSetMember.document_id == document_id
    ).delete(synchronize_session=False)

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_document",
        entity_id=str(document_id),
        action="document_hard_deleted",
        reason_code="INGEST_DOC_HARD_DELETE",
        details=json.dumps({"occurrence_id": doc.occurrence_id, "doc_type": doc.doc_type}),
    )
    db.delete(doc)
    db.flush()
