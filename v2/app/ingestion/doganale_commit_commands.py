"""Fattura Doganale commit — Elo 7 / DEC-E7-DOGANALE-FILL + PROCESS-TARGET.

Preview + commit: IR rows → CustomsDoganale version/lines via customs.public.
Idempotency by document_id SUCCEEDED (C6). 0/1/N for process, invoice, shipment.
Never silent second ImportProcess. Never invent SKU or Brazilian tax lines.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.billing import public as billing_public
from app.customs import public as customs_public
from app.documents import public as documents_public
from app.ingestion import staging_queries
from app.ingestion import storage as quarantine_storage
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.logistics import public as logistics_public

DOC_TYPE = "FATTURA_DOGANALE"
ADVANCED_STATUSES = frozenset({"PARTIALLY_CLEARED", "CLEARED", "IN_CLEARANCE"})


class DoganaleCommitBlocked(IngestionError):
    def __init__(self, message: str, *, code: str = "doganale_commit_blocked"):
        super().__init__(message, code=code)


class DoganaleConflictFingerprint(IngestionError):
    def __init__(self, op_key: str) -> None:
        super().__init__(
            f"operation_key '{op_key}' já existe com fingerprint diferente",
            code="commit_conflict_fingerprint",
        )


def _field_value(doc, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _dec(raw: str | None) -> Decimal | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None


def _cell(row, key: str) -> str | None:
    raw = row.cells_json
    if not raw:
        return None
    try:
        cells = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    cell = cells.get(key) or {}
    val = cell.get("normalized") or cell.get("raw")
    return str(val) if val is not None else None


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
) -> None:
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


def _last_succeeded_attempt(db: Session, document_id: int) -> IngestionCommitAttempt | None:
    row = (
        db.query(IngestionCommitAttempt)
        .filter(
            IngestionCommitAttempt.document_id == document_id,
            IngestionCommitAttempt.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitAttempt.id.desc())
        .first()
    )
    if row is None or getattr(row, "status", None) != "SUCCEEDED":
        return None
    return row


def _process_id_from_attempt(attempt: IngestionCommitAttempt) -> int | None:
    for op in attempt.operations or []:
        if (
            op.entity_type in ("import_process", "process")
            and op.status == "SUCCEEDED"
            and op.entity_id
        ):
            try:
                return int(op.entity_id)
            except (TypeError, ValueError):
                continue
    return None


def _origin_iso2(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return None


def extract_doganale_lines(doc) -> list[dict]:
    lines: list[dict] = []
    origin = _origin_iso2(_field_value(doc, "origin_country_declared"))
    currency = (_field_value(doc, "currency") or "EUR").strip()[:3] or "EUR"
    position = 0
    for row in doc.rows or []:
        if getattr(row, "section_key", None) not in (None, "lines"):
            continue
        qty = _dec(_cell(row, "quantity"))
        ncm = _cell(row, "ncm")
        desc = _cell(row, "description") or ""
        if qty is None and not ncm and not desc:
            continue
        position += 1
        ncm_s = (ncm or "").replace(" ", "")[:16] or None
        unit_price = _dec(_cell(row, "unit_price"))
        line_amount = _dec(_cell(row, "line_total"))
        lines.append(
            {
                "position": position,
                "ncm": ncm_s,
                "description": desc[:2000] if desc else None,
                "quantity": str(qty) if qty is not None else None,
                "unit": (_cell(row, "unit") or "SET")[:16],
                "currency": currency,
                "unit_price": str(unit_price) if unit_price is not None else None,
                "line_amount": str(line_amount) if line_amount is not None else None,
                "origin_country": origin,
                "document_id": None,
            }
        )
    return lines


def _compute_fingerprint(
    document_id: int,
    *,
    process_id: int | None,
    invoice_id: int | None,
    shipment_id: int | None,
) -> str:
    canonical = json.dumps(
        {
            "doc_id": document_id,
            "process_id": process_id,
            "invoice_id": invoice_id,
            "shipment_id": shipment_id,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class DoganalePreviewOp:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class DoganalePreviewResult:
    document_id: int
    fingerprint: str
    operations: list[DoganalePreviewOp]
    open_error_count: int
    can_commit: bool
    process_targets: list[dict] = field(default_factory=list)
    process_targets_reason: str | None = None
    invoice_candidates: list[dict] = field(default_factory=list)
    invoice_candidates_reason: str | None = None
    shipment_targets: list[dict] = field(default_factory=list)
    shipment_targets_reason: str | None = None
    lines: list[dict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    resolved_process_id: int | None = None
    resolved_invoice_id: int | None = None
    resolved_shipment_id: int | None = None
    will_create_process: bool = False
    reuse_reason: str | None = None
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_process_id: int | None = None
    document_number: str | None = None


def _process_target_view(process, *, evidence: list[str], compatible: bool) -> dict:
    return {
        "process_id": process.id,
        "code": process.code,
        "status": process.status,
        "compatible": compatible,
        "evidence": evidence,
    }


def _classify_process(db: Session, process) -> tuple[bool, list[str]]:
    evidence: list[str] = [f"Status {process.status}"]
    if process.status == "CANCELLED":
        return False, ["Cancelado — incompatível"]
    if process.status in ADVANCED_STATUSES:
        return False, [
            f"Processo {process.status} — reprocessar PDF não sobrescreve declaração ativa"
        ]
    current = customs_public.get_current_doganale_version(db, process.id)
    if current is not None and current.status == "ACTIVE":
        evidence.append("Já tem Doganale ACTIVE — fill exige retificação explícita")
        return False, evidence
    if process.status == "SUBMITTED":
        evidence.append("SUBMITTED: só reuso se fatura/embarque já estiverem ligados")
        return True, evidence
    return True, evidence


def collect_invoice_candidates(db: Session, doc_num: str | None) -> list[dict]:
    if not doc_num:
        return []
    try:
        invoices = billing_public.find_invoices_by_number(db, doc_num)
    except Exception:
        return []
    if not isinstance(invoices, list):
        return []
    out: list[dict] = []
    for inv in invoices:
        status = getattr(inv, "status", None)
        if status != "ISSUED":
            continue
        linked = customs_public.find_process_for_invoice(db, inv.id)
        out.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "order_id": inv.order_id,
                "linked_process_id": linked.id if linked is not None else None,
                "evidence": [f"Nº da fatura = {doc_num}"],
            }
        )
    return out


def collect_shipment_targets(db: Session, doc_num: str | None) -> list[dict]:
    if not doc_num:
        return []
    try:
        found = list(logistics_public.find_shipments_by_reference(db, "PACKING_LIST", doc_num))
    except Exception:
        return []
    out: list[dict] = []
    seen: set[int] = set()
    for s in found:
        if getattr(s, "id", None) in seen:
            continue
        seen.add(s.id)
        cancelled = getattr(s, "cancelled_at", None) is not None
        linked = customs_public.find_process_for_shipment(db, s.id)
        out.append(
            {
                "shipment_id": s.id,
                "code": s.code,
                "status": s.status,
                "compatible": not cancelled,
                "linked_process_id": linked.id if linked is not None else None,
                "evidence": ["Referência PACKING_LIST"]
                + (["Anulado"] if cancelled else []),
            }
        )
    return out


def collect_process_targets(
    db: Session,
    *,
    doc_num: str | None,
    invoice_candidates: list[dict],
    shipment_targets: list[dict],
) -> list[dict]:
    by_id: dict[int, dict] = {}

    def _add(process, extra: list[str]) -> None:
        if process is None or getattr(process, "id", None) is None:
            return
        ok, ev = _classify_process(db, process)
        prev = by_id.get(process.id)
        evidence = list(extra) + ev
        if prev:
            prev["evidence"] = list(dict.fromkeys(prev["evidence"] + evidence))
            prev["compatible"] = prev["compatible"] and ok
            return
        by_id[process.id] = _process_target_view(process, evidence=evidence, compatible=ok)

    for inv in invoice_candidates:
        pid = inv.get("linked_process_id")
        if pid:
            try:
                _add(customs_public.get_import_process(db, pid), ["Fatura ISSUED já ligada"])
            except customs_public.CustomsError:
                pass
        else:
            # invoice exists but no process yet — not a process target
            continue

    for sh in shipment_targets:
        pid = sh.get("linked_process_id")
        if pid:
            try:
                _add(customs_public.get_import_process(db, pid), ["Embarque já ligado"])
            except customs_public.CustomsError:
                pass

    return list(by_id.values())


def _resolve_process(
    targets: list[dict],
    process_id: int | None,
) -> tuple[int | None, bool, str | None, str | None]:
    """Returns (resolved_id, will_create, reason, reuse_reason)."""
    compatible = [t for t in targets if t.get("compatible")]
    if process_id is not None:
        hit = next((t for t in targets if t["process_id"] == process_id), None)
        if hit is not None and not hit["compatible"]:
            return None, False, (
                f"Processo #{process_id} não é reutilizável em silêncio "
                f"({'; '.join(hit.get('evidence') or [])})."
            ), None
        return process_id, False, None, "human_confirmed_candidate"
    if not targets:
        return None, True, None, "created_empty"
    if len(compatible) == 1 and len(targets) == 1:
        return None, False, (
            "Há 1 processo candidato — confirme explicitamente. O sistema não escolhe em silêncio."
        ), None
    if not compatible:
        return None, False, (
            "Há processo(s) com este sinal, mas nenhum é reutilizável "
            "(avançado, cancelado ou já com Doganale ACTIVE). Não criamos duplicata em silêncio."
        ), None
    return None, False, (
        f"{len(compatible)} processos candidatos — escolha o processo; "
        "o sistema não escolhe em silêncio."
    ), None


def preview_commit_doganale(
    db: Session,
    document_id: int,
    *,
    process_id: int | None = None,
    invoice_id: int | None = None,
    shipment_id: int | None = None,
) -> DoganalePreviewResult:
    doc = staging_queries.get_document_detail(db, document_id)
    if (doc.doc_type or "") != DOC_TYPE:
        raise DoganaleCommitBlocked(
            "Documento não é Fattura Doganale",
            code="doganale_wrong_doc_type",
        )
    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )
    fingerprint = _compute_fingerprint(
        document_id, process_id=process_id, invoice_id=invoice_id, shipment_id=shipment_id
    )
    existing_ok = _last_succeeded_attempt(db, document_id)
    if existing_ok is not None:
        pid = _process_id_from_attempt(existing_ok)
        ops = [
            DoganalePreviewOp(
                op_key=op.op_key,
                description=(
                    "Processo já preenchido a partir desta Doganale"
                    if op.entity_type in ("import_process", "process")
                    else op.op_key.replace("_", " ")
                ),
                entity_type=op.entity_type,
                params={"entity_id": op.entity_id} if op.entity_id else {},
            )
            for op in (existing_ok.operations or [])
        ]
        return DoganalePreviewResult(
            document_id=document_id,
            fingerprint=existing_ok.payload_fingerprint or fingerprint,
            operations=ops,
            open_error_count=open_errors,
            can_commit=False,
            already_committed=True,
            last_succeeded_attempt_id=existing_ok.id,
            last_succeeded_process_id=pid,
            resolved_process_id=pid,
            reuse_reason="already_committed_document",
            document_number=_field_value(doc, "document_number"),
        )

    doc_num = (_field_value(doc, "document_number") or "").strip() or None
    lines = extract_doganale_lines(doc)
    invoices = collect_invoice_candidates(db, doc_num)
    shipments = collect_shipment_targets(db, doc_num)
    processes = collect_process_targets(
        db, doc_num=doc_num, invoice_candidates=invoices, shipment_targets=shipments
    )

    blockers: list[str] = []
    resolved_pid, will_create, process_reason, reuse_reason = _resolve_process(
        processes, process_id
    )
    if process_reason:
        blockers.append(process_reason)

    invoice_reason = None
    resolved_invoice = invoice_id
    issued = invoices
    if invoice_id is not None:
        hit = next((i for i in issued if i["invoice_id"] == invoice_id), None)
        if hit is None:
            blockers.append(f"Fatura #{invoice_id} não é candidata ISSUED deste documento.")
            resolved_invoice = None
    elif len(issued) == 1:
        invoice_reason = (
            "1 fatura ISSUED com este número — confirme para vincular. Sem confirmação o "
            "vínculo não é criado."
        )
    elif len(issued) > 1:
        invoice_reason = (
            f"{len(issued)} faturas ISSUED com este número — escolha; o sistema não vincula em silêncio."
        )
    elif not issued:
        invoice_reason = "Nenhuma fatura ISSUED com o número da Doganale — declaração ainda pode ser preenchida."

    shipment_reason = None
    resolved_shipment = shipment_id
    compatible_ships = [s for s in shipments if s.get("compatible")]
    if shipment_id is not None:
        hit = next((s for s in shipments if s["shipment_id"] == shipment_id), None)
        if hit is None or not hit.get("compatible"):
            blockers.append(f"Embarque #{shipment_id} não é candidato compatível.")
            resolved_shipment = None
    elif len(compatible_ships) == 1 and len(shipments) == 1:
        shipment_reason = (
            "1 embarque com packing deste número — confirme para vincular."
        )
    elif len(compatible_ships) > 1:
        shipment_reason = (
            f"{len(compatible_ships)} embarques candidatos — escolha; sem vínculo silencioso."
        )
    elif not shipments:
        shipment_reason = "Nenhum embarque com referência de packing deste número."

    if open_errors:
        blockers.append(f"{open_errors} erro(s) em aberto na extração")
    if not lines:
        blockers.append("Doganale sem linhas comerciais extraídas")

    can_commit = (
        open_errors == 0
        and bool(lines)
        and not blockers
        and (will_create or resolved_pid is not None or process_id is not None)
    )
    if will_create and open_errors == 0 and lines and not process_reason:
        can_commit = True
    if process_id is not None and not process_reason and open_errors == 0 and lines:
        can_commit = True
        resolved_pid = process_id

    ops = [
        DoganalePreviewOp("store_document", "Promover PDF Doganale para Documents", "document"),
    ]
    if will_create:
        ops.append(
            DoganalePreviewOp(
                "create_import_process_draft",
                f"Criar ImportProcess DRAFT (Doganale {doc_num or document_id})",
                "import_process",
                {"reuse_reason": "created_empty"},
            )
        )
    elif resolved_pid or process_id:
        ops.append(
            DoganalePreviewOp(
                "reuse_import_process",
                f"Reutilizar ImportProcess #{resolved_pid or process_id}",
                "import_process",
                {"reuse_reason": reuse_reason or "human_confirmed_candidate"},
            )
        )
    ops.append(
        DoganalePreviewOp(
            "fill_doganale_lines",
            f"Preencher {len(lines)} linha(s) na Doganale canônica e ativar versão",
            "customs_doganale",
        )
    )
    if resolved_invoice:
        ops.append(
            DoganalePreviewOp(
                "link_invoice",
                f"Vincular Invoice ISSUED #{resolved_invoice}",
                "invoice",
                {"invoice_id": resolved_invoice},
            )
        )
    if resolved_shipment:
        ops.append(
            DoganalePreviewOp(
                "link_shipment",
                f"Vincular Shipment #{resolved_shipment}",
                "shipment",
                {"shipment_id": resolved_shipment},
            )
        )

    return DoganalePreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        operations=ops,
        open_error_count=open_errors,
        can_commit=can_commit,
        process_targets=processes,
        process_targets_reason=process_reason,
        invoice_candidates=issued,
        invoice_candidates_reason=invoice_reason,
        shipment_targets=shipments,
        shipment_targets_reason=shipment_reason,
        lines=lines,
        blockers=blockers,
        resolved_process_id=resolved_pid,
        resolved_invoice_id=resolved_invoice,
        resolved_shipment_id=resolved_shipment,
        will_create_process=will_create,
        reuse_reason=reuse_reason,
        document_number=doc_num,
    )


def _wrap_customs(exc: Exception) -> IngestionError:
    code = getattr(exc, "code", None) or "customs_error"
    msg = getattr(exc, "message", None) or str(exc)
    return IngestionError(msg, code=code)


def _reload(db: Session, process_id: int):
    return customs_public.get_import_process(db, process_id)


def commit_doganale(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
    process_id: int | None = None,
    invoice_id: int | None = None,
    shipment_id: int | None = None,
) -> IngestionCommitAttempt:
    preview = preview_commit_doganale(
        db,
        document_id,
        process_id=process_id,
        invoice_id=invoice_id,
        shipment_id=shipment_id,
    )
    if preview.already_committed:
        existing = _last_succeeded_attempt(db, document_id)
        if existing is not None:
            return existing

    if preview.open_error_count:
        raise DoganaleCommitBlocked(
            f"{preview.open_error_count} issue(s) OPEN ERROR bloqueiam o commit",
            code="commit_blocked_by_issues",
        )
    if not preview.can_commit:
        raise DoganaleCommitBlocked(
            "; ".join(preview.blockers) or "Commit Doganale bloqueado",
            code="doganale_commit_blocked",
        )

    fingerprint = _compute_fingerprint(
        document_id, process_id=process_id, invoice_id=invoice_id, shipment_id=shipment_id
    )
    existing_key = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing_key is not None:
        if getattr(existing_key, "payload_fingerprint", None) == fingerprint:
            return existing_key
        raise DoganaleConflictFingerprint(operation_key)

    doc = staging_queries.get_document_detail(db, document_id)
    attempt = IngestionCommitAttempt(
        document_id=document_id,
        operation_key=operation_key,
        payload_fingerprint=fingerprint,
        status="UNKNOWN",
        actor_id=actor_id,
    )
    db.add(attempt)
    db.flush()

    succeeded: list[str] = []
    failed: list[str] = []
    reuse_reason = preview.reuse_reason or (
        "created_empty" if preview.will_create_process else "human_confirmed_candidate"
    )

    promoted_doc_id: int | None = None
    try:
        occ = db.get(IngestionOccurrence, doc.occurrence_id)
        if occ and occ.blob and occ.blob.physical_status == "PRESENT" and occ.blob.storage_path:
            blob_path = quarantine_storage.resolve_quarantine_path(
                quarantine_path, occ.blob.storage_path
            )
            if blob_path and blob_path.is_file():
                pdf_bytes = blob_path.read_bytes()
                promoted = documents_public.store_document(
                    db,
                    attachments_path=attachments_path,
                    actor_id=actor_id,
                    filename=occ.original_filename or f"doganale_{document_id}.pdf",
                    content=pdf_bytes,
                    mime_type=occ.detected_mime or "application/pdf",
                )
                promoted_doc_id = promoted.id
        _record_op(
            db,
            attempt,
            "store_document",
            status="SUCCEEDED",
            entity_type="document",
            entity_id=str(promoted_doc_id) if promoted_doc_id else None,
        )
        succeeded.append("store_document")
    except Exception as exc:
        _record_op(
            db, attempt, "store_document", status="FAILED", error_message=str(exc)[:512]
        )
        failed.append("store_document")
        attempt.status = "FAILED"
        db.flush()
        return attempt

    process = None
    try:
        if preview.will_create_process:
            doc_num = preview.document_number
            process = customs_public.create_import_process(
                db,
                notes=(
                    f"Criado via ingestão Fattura Doganale — IR {document_id} "
                    f"ref={doc_num} reason={reuse_reason}"
                ),
            )
            reuse_reason = "created_empty"
        else:
            pid = process_id or preview.resolved_process_id
            if pid is None:
                raise DoganaleCommitBlocked(
                    "process_id obrigatório quando há candidato",
                    code="doganale_process_id_required",
                )
            process = _reload(db, pid)
            reuse_reason = "human_confirmed_candidate"
        _record_op(
            db,
            attempt,
            "resolve_import_process",
            status="SUCCEEDED",
            entity_type="import_process",
            entity_id=str(process.id),
            details_json=json.dumps(
                {
                    "process_code": process.code,
                    "status": process.status,
                    "reuse_reason": reuse_reason,
                }
            ),
        )
        succeeded.append("resolve_import_process")
        if promoted_doc_id:
            try:
                documents_public.link_document(
                    db,
                    document_id=promoted_doc_id,
                    entity_type="import_process",
                    entity_id=str(process.id),
                    role="fattura_doganale",
                )
            except Exception:
                pass
    except IngestionError:
        raise
    except Exception as exc:
        _record_op(
            db,
            attempt,
            "resolve_import_process",
            status="FAILED",
            error_message=str(exc)[:512],
        )
        failed.append("resolve_import_process")
        attempt.status = "PARTIAL"
        db.flush()
        return attempt

    assert process is not None

    def _link_if_draft(kind: str) -> None:
        nonlocal process
        process = _reload(db, process.id)
        if process.status != "DRAFT":
            return
        try:
            if kind == "invoice" and invoice_id is not None:
                existing = customs_public.find_process_for_invoice(db, invoice_id)
                if existing is not None and existing.id == process.id:
                    return
                customs_public.link_invoice(
                    db,
                    process.id,
                    expected_version=process.version,
                    invoice_id=invoice_id,
                    notes=f"Confirmado no commit Doganale IR {document_id}",
                )
                _record_op(
                    db,
                    attempt,
                    "link_invoice",
                    status="SUCCEEDED",
                    entity_type="invoice",
                    entity_id=str(invoice_id),
                )
                succeeded.append("link_invoice")
            if kind == "shipment" and shipment_id is not None:
                existing = customs_public.find_process_for_shipment(db, shipment_id)
                if existing is None or existing.id != process.id:
                    customs_public.link_shipment(
                        db,
                        process.id,
                        expected_version=process.version,
                        shipment_id=shipment_id,
                        notes=f"Confirmado no commit Doganale IR {document_id}",
                    )
                    _record_op(
                        db,
                        attempt,
                        "link_shipment",
                        status="SUCCEEDED",
                        entity_type="shipment",
                        entity_id=str(shipment_id),
                    )
                    succeeded.append("link_shipment")
                process = _reload(db, process.id)
                db.expire(process, ["shipments"])
                process = _reload(db, process.id)
                shipment = logistics_public.get_shipment(db, shipment_id)
                items = list(shipment.items or [])
                for it in items:
                    process = _reload(db, process.id)
                    db.expire(process, ["shipments"])
                    process = _reload(db, process.id)
                    customs_public.allocate_shipment_item(
                        db,
                        process.id,
                        expected_version=process.version,
                        shipment_item_id=it.id,
                        allocated_qty=str(it.quantity),
                    )
                    _record_op(
                        db,
                        attempt,
                        f"allocate_shipment_item_{it.id}",
                        status="SUCCEEDED",
                        entity_type="shipment_item",
                        entity_id=str(it.id),
                    )
                    succeeded.append("allocate_shipment_item")
        except customs_public.CustomsError as exc:
            already = {op.op_key for op in (attempt.operations or [])}
            op_fail = f"link_{kind}"
            if op_fail in already:
                op_fail = f"{op_fail}_error"
            _record_op(
                db,
                attempt,
                op_fail,
                status="FAILED",
                error_message=exc.message[:512],
            )
            failed.append(op_fail)

    _link_if_draft("invoice")
    _link_if_draft("shipment")

    try:
        process = _reload(db, process.id)
        lines = extract_doganale_lines(doc)
        for row in lines:
            row["document_id"] = promoted_doc_id
        customs_public.ensure_doganale(db, process.id)
        ver = customs_public.create_doganale_version(
            db,
            process.id,
            notes=f"Ingestão Fattura Doganale IR {document_id}",
            document_id=promoted_doc_id,
            idempotency_key=f"ingest-doganale-{document_id}",
        )
        ver = customs_public.replace_doganale_lines(
            db,
            ver.id,
            expected_version=ver.version,
            lines=lines,
        )
        ver = customs_public.activate_doganale_version(
            db, ver.id, expected_version=ver.version
        )
        customs_public.attach_provenance(
            db,
            process.id,
            entity_type="customs_doganale_version",
            entity_id=str(ver.id),
            source_kind="FATTURA_DOGANALE",
            document_id=promoted_doc_id,
            adapter_key="fattura_doganale_v1",
            notes=f"reuse_reason={reuse_reason}",
        )
        _record_op(
            db,
            attempt,
            "fill_doganale_lines",
            status="SUCCEEDED",
            entity_type="customs_doganale_version",
            entity_id=str(ver.id),
            details_json=json.dumps(
                {
                    "lines": len(lines),
                    "version_status": ver.status,
                    "reuse_reason": reuse_reason,
                }
            ),
        )
        succeeded.append("fill_doganale_lines")
    except customs_public.CustomsError as exc:
        _record_op(
            db,
            attempt,
            "fill_doganale_lines",
            status="FAILED",
            error_message=exc.message[:512],
        )
        failed.append("fill_doganale_lines")
    except Exception as exc:
        _record_op(
            db,
            attempt,
            "fill_doganale_lines",
            status="FAILED",
            error_message=str(exc)[:512],
        )
        failed.append("fill_doganale_lines")

    attempt.status = "PARTIAL" if failed else "SUCCEEDED"
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_doganale_completed",
        reason_code="INGEST_DOGANALE_COMMIT_DONE",
        details=json.dumps(
            {
                "document_id": document_id,
                "status": attempt.status,
                "succeeded": succeeded,
                "failed": failed,
                "reuse_reason": reuse_reason,
                "process_id": process.id,
            }
        ),
    )
    return attempt
