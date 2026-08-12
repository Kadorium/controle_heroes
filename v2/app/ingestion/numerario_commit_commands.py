"""Numerário commit commands — J3-I6.

Orquestração multi-owner para Solicitação de Numerário:
- Preview (read-only): digest + ops planejadas por process_id
- Commit: store_document + create_or_find_payee + per-process: create_funding_request (DRAFT) + replace_value_bases + replace_tax_lines + replace_expense_lines

Regras hard:
- NEVER auto-confirm FundingRequest
- NEVER create Payment
- NEVER liquidate CUSTOMS_FUNDING
- Sem compensação cross-owner (cross-owner rollback não existe na API pública)
- PARTIAL/UNKNOWN explícitos quando ops parcialmente completadas
- Retry/replay idempotente: mesma operation_key + fingerprint → retorna attempt existente
- 409 para mesma chave com fingerprint diferente
- Cada FundingRequest criado com status DRAFT; confirmação é ação humana separada
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.customs import public as customs_public
from app.documents import public as documents_public
from app.ingestion import staging_queries
from app.ingestion import storage as quarantine_storage
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class NumerarioCommitConflictFingerprint(IngestionError):
    def __init__(self, op_key: str) -> None:
        super().__init__(
            f"operation_key '{op_key}' já existe com fingerprint diferente",
            code="commit_conflict_fingerprint",
        )


class NumerarioCommitBlockedByIssues(IngestionError):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} issue(s) OPEN ERROR bloqueiam o commit do Numerário",
            code="commit_blocked_by_issues",
        )


# ---------------------------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------------------------


@dataclass
class NumerarioPreviewOp:
    op_key: str
    description: str
    entity_type: str | None = None
    process_id: int | None = None
    params: dict = field(default_factory=dict)


@dataclass
class NumerarioPreviewResult:
    document_id: int
    fingerprint: str
    invoice_refs: list[str]
    process_ids_input: list[int]
    planned_operations: list[NumerarioPreviewOp]
    open_error_count: int
    can_commit: bool


def _build_fingerprint(document_id: int, process_ids: list[int]) -> str:
    import hashlib

    canonical = json.dumps(
        {
            "doc_id": document_id,
            "doc_type": "SOLICITACAO_NUMERARIO",
            "process_ids": sorted(process_ids),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _get_field_value(doc, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _parse_invoice_refs(doc) -> list[str]:
    raw = _get_field_value(doc, "invoice_refs_json")
    if not raw:
        return []
    try:
        refs = json.loads(raw)
        if isinstance(refs, list):
            return [str(r) for r in refs]
    except Exception:
        pass
    return []


def preview_numerario(
    db: Session,
    document_id: int,
    process_ids: list[int],
) -> NumerarioPreviewResult:
    """Read-only preview — no DB writes."""
    import hashlib

    doc = staging_queries.get_document_detail(db, document_id)
    open_errors = [
        i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    ]

    invoice_refs = _parse_invoice_refs(doc)
    fingerprint = _build_fingerprint(document_id, process_ids)

    ops: list[NumerarioPreviewOp] = [
        NumerarioPreviewOp(
            op_key="store_document",
            description="Promover PDF Numerário para Documents",
            entity_type="document",
        ),
        NumerarioPreviewOp(
            op_key="create_or_find_payee",
            description="Criar ou localizar Payee (beneficiário) em Customs",
            entity_type="customs_payee",
            params={
                "payee_name": _get_field_value(doc, "payee_name"),
                "payee_cnpj": _get_field_value(doc, "payee_cnpj"),
            },
        ),
    ]

    for pid in process_ids:
        base = f"process_{pid}"
        ops.append(
            NumerarioPreviewOp(
                op_key=f"{base}_create_funding_request",
                description=f"Criar FundingRequest DRAFT para ImportProcess {pid} via customs.create_funding_request",
                entity_type="customs_funding_request",
                process_id=pid,
                params={"process_id": pid, "status": "DRAFT"},
            )
        )
        ops.append(
            NumerarioPreviewOp(
                op_key=f"{base}_replace_value_bases",
                description=f"Preencher bases de valor (FOB/CIF/Frete) no FundingRequest do processo {pid}",
                entity_type="customs_funding_request",
                process_id=pid,
            )
        )
        ops.append(
            NumerarioPreviewOp(
                op_key=f"{base}_replace_tax_lines",
                description=f"Preencher linhas de impostos (ICMS/II/IPI/PIS/COFINS/AFRMM) no processo {pid}",
                entity_type="customs_funding_request",
                process_id=pid,
            )
        )
        ops.append(
            NumerarioPreviewOp(
                op_key=f"{base}_replace_expense_lines",
                description=f"Preencher linhas de despesas (frete/armazenagem/honorários) no processo {pid}",
                entity_type="customs_funding_request",
                process_id=pid,
            )
        )

    return NumerarioPreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        invoice_refs=invoice_refs,
        process_ids_input=process_ids,
        planned_operations=ops,
        open_error_count=len(open_errors),
        can_commit=len(open_errors) == 0 and len(process_ids) > 0,
    )


# ---------------------------------------------------------------------------
# Per-document field helpers
# ---------------------------------------------------------------------------


def _build_value_bases(doc) -> list[dict]:
    """Build value_bases lines from IR fields: FOB, Additions, Deductions, Freight, Insurance, CIF."""
    bases = []
    pos = 0

    fob_currency = _get_field_value(doc, "fob_currency") or "EUR"
    fob_brl = _get_field_value(doc, "fob_brl_amount")
    if fob_brl:
        bases.append(
            {
                "position": pos,
                "label": "FOB",
                "code": "FOB",
                "amount": fob_brl,
                "currency": "BRL",
            }
        )
        pos += 1

    freight_brl = _get_field_value(doc, "freight_brl_amount")
    if freight_brl:
        bases.append(
            {
                "position": pos,
                "label": "FRETE",
                "code": "FRETE",
                "amount": freight_brl,
                "currency": "BRL",
            }
        )
        pos += 1

    insurance_brl = _get_field_value(doc, "insurance_brl")
    if insurance_brl:
        bases.append(
            {
                "position": pos,
                "label": "SEGURO",
                "code": "SEGURO",
                "amount": insurance_brl,
                "currency": "BRL",
            }
        )
        pos += 1

    cif_brl = _get_field_value(doc, "cif_brl_amount")
    if cif_brl:
        bases.append(
            {
                "position": pos,
                "label": "CIF",
                "code": "CIF",
                "amount": cif_brl,
                "currency": "BRL",
            }
        )
        pos += 1

    return bases


def _build_lines_by_category(doc) -> tuple[list[dict], list[dict]]:
    """Split IR expense rows into tax_lines and expense_lines."""
    tax_lines = []
    expense_lines = []
    tax_pos = 0
    exp_pos = 0

    TAX_CODES = {
        "AFRMM",
        "ICMS",
        "II",
        "IPI",
        "PIS",
        "COFINS",
        "SISCOMEX",
    }

    for row in doc.rows or []:
        try:
            cells = json.loads(row.cells_json or "{}")
        except Exception:
            cells = {}

        label = (cells.get("label") or {}).get("normalized") or ""
        code = (cells.get("code") or {}).get("normalized") or ""
        amount = (cells.get("amount_brl") or {}).get("normalized")
        category = (cells.get("category") or {}).get("normalized") or "expense"

        if not amount or not label:
            continue

        if category == "tax" or code in TAX_CODES:
            tax_lines.append(
                {
                    "position": tax_pos,
                    "label": label,
                    "code": code,
                    "amount": amount,
                    "currency": "BRL",
                }
            )
            tax_pos += 1
        else:
            expense_lines.append(
                {
                    "position": exp_pos,
                    "label": label,
                    "code": code,
                    "amount": amount,
                    "currency": "BRL",
                }
            )
            exp_pos += 1

    return tax_lines, expense_lines


# ---------------------------------------------------------------------------
# Record operation helper
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


# ---------------------------------------------------------------------------
# Main commit
# ---------------------------------------------------------------------------


def commit_numerario(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    process_ids: list[int],
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
) -> IngestionCommitAttempt:
    """Commit Solicitação de Numerário: promote document + create/update payee + per-process FundingRequest DRAFT.

    Multi-owner: one FundingRequest DRAFT per process_id in process_ids.
    No auto-confirm. No Payment. No cross-owner rollback (compensation limited to single-owner idempotency).
    PARTIAL if any per-process ops fail after store_document succeeded.
    UNKNOWN recorded if post-commit state cannot be verified.
    """
    doc = staging_queries.get_document_detail(db, document_id)

    open_errors = [
        i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    ]
    if open_errors:
        raise NumerarioCommitBlockedByIssues(len(open_errors))

    if not process_ids:
        raise IngestionError(
            "process_ids obrigatório para commit do Numerário",
            code="commit_blocked_by_issues",
        )

    fingerprint = _build_fingerprint(document_id, process_ids)

    # Idempotency check
    existing = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing is not None:
        if existing.payload_fingerprint == fingerprint:
            return existing
        raise NumerarioCommitConflictFingerprint(operation_key)

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

    # ---------- Op 1: store_document ----------
    promoted_doc_id: int | None = None
    try:
        occ = db.get(IngestionOccurrence, doc.occurrence_id)
        if (
            occ
            and occ.blob
            and occ.blob.physical_status == "PRESENT"
            and occ.blob.storage_path
        ):
            blob_path = quarantine_storage.resolve_quarantine_path(
                quarantine_path, occ.blob.storage_path
            )
            if blob_path and blob_path.is_file():
                pdf_bytes = blob_path.read_bytes()
                promoted = documents_public.store_document(
                    db,
                    attachments_path=attachments_path,
                    actor_id=actor_id,
                    filename=occ.original_filename or f"numerario_{document_id}.pdf",
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

    # ---------- Op 2: create_or_find_payee ----------
    payee_id: int | None = None
    payee_op_key = "create_or_find_payee"
    try:
        payee_name = _get_field_value(doc, "payee_name")
        payee_cnpj = _get_field_value(doc, "payee_cnpj")
        payee_bank = _get_field_value(doc, "payee_bank")
        payee_agency = _get_field_value(doc, "payee_agency")
        payee_account = _get_field_value(doc, "payee_account")
        payee_pix = _get_field_value(doc, "payee_pix")

        if not payee_name:
            raise ValueError("payee_name ausente no IR do documento")

        # Try to find existing payee by tax_id or name to support idempotency
        existing_payees = customs_public.list_payees(db, limit=200)
        found_payee = None
        for p in existing_payees:
            if payee_cnpj and p.tax_id == payee_cnpj:
                found_payee = p
                break
            if p.name and p.name.upper() == payee_name.upper():
                found_payee = p
                break

        if found_payee is not None:
            payee_id = found_payee.id
            _record_op(
                db,
                attempt,
                payee_op_key,
                status="SUCCEEDED",
                entity_type="customs_payee",
                entity_id=str(payee_id),
                details_json=json.dumps({"reused": True, "payee_id": payee_id}),
            )
        else:
            payee = customs_public.create_payee(
                db,
                name=payee_name,
                tax_id=payee_cnpj,
                bank_name=payee_bank,
                agency=payee_agency,
                account=payee_account,
                pix_key=payee_pix,
                notes=f"Criado via ingestão Numerário — documento IR {document_id}",
            )
            payee_id = payee.id
            _record_op(
                db,
                attempt,
                payee_op_key,
                status="SUCCEEDED",
                entity_type="customs_payee",
                entity_id=str(payee_id),
                details_json=json.dumps({"reused": False, "payee_id": payee_id}),
            )
        succeeded.append(payee_op_key)
    except Exception as exc:
        _record_op(
            db, attempt, payee_op_key, status="FAILED", error_message=str(exc)[:512]
        )
        failed.append(payee_op_key)
        # Payee failure is blocking — can't create FundingRequests without it
        attempt.status = "FAILED"
        db.flush()
        return attempt

    # ---------- Per-process ops (multi-owner) ----------
    value_bases = _build_value_bases(doc)
    tax_lines, expense_lines = _build_lines_by_category(doc)

    issue_date_str = _get_field_value(doc, "issue_date")
    due_date_str = _get_field_value(doc, "due_date")
    n_reference = _get_field_value(doc, "n_reference")
    declared_total = _get_field_value(doc, "declared_total_brl")
    awb_bl = _get_field_value(doc, "awb_bl")

    # Parse dates for funding_request
    from datetime import date as _date

    def _parse_date_safe(s: str | None) -> _date | None:
        if not s:
            return None
        try:
            return _date.fromisoformat(s)
        except Exception:
            return None

    issue_date = _parse_date_safe(issue_date_str)
    due_date = _parse_date_safe(due_date_str)

    for pid in process_ids:
        base = f"process_{pid}"

        # Op: create_funding_request DRAFT
        funding_id: int | None = None
        fr_op_key = f"{base}_create_funding_request"
        try:
            fr = customs_public.create_funding_request(
                db,
                pid,
                payee_id=payee_id,
                currency="BRL",
                declared_total=declared_total or "0",
                reference=n_reference or awb_bl,
                issue_date=issue_date,
                due_date=due_date,
                document_id=promoted_doc_id,
                notes=f"Criado via ingestão Numerário — IR {document_id}",
                idempotency_key=f"ING-NUM-{document_id}-P{pid}",
            )
            funding_id = fr.id
            _record_op(
                db,
                attempt,
                fr_op_key,
                status="SUCCEEDED",
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                details_json=json.dumps(
                    {
                        "process_id": pid,
                        "funding_status": fr.status,
                        "version": fr.version,
                    }
                ),
            )
            succeeded.append(fr_op_key)
        except Exception as exc:
            err = str(exc)[:512]
            _record_op(db, attempt, fr_op_key, status="FAILED", error_message=err)
            failed.append(fr_op_key)
            # Record remaining per-process ops as UNKNOWN (no rollback available)
            for suffix in (
                "_replace_value_bases",
                "_replace_tax_lines",
                "_replace_expense_lines",
            ):
                _record_op(
                    db,
                    attempt,
                    f"{base}{suffix}",
                    status="UNKNOWN",
                    error_message="Skipped: FundingRequest creation failed",
                )
            continue

        # Op: replace_value_bases
        vb_op_key = f"{base}_replace_value_bases"
        try:
            if value_bases:
                customs_public.replace_value_bases(
                    db,
                    funding_id,
                    expected_version=fr.version,
                    lines=value_bases,
                )
            _record_op(
                db,
                attempt,
                vb_op_key,
                status="SUCCEEDED",
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                details_json=json.dumps({"lines_count": len(value_bases)}),
            )
            succeeded.append(vb_op_key)
        except Exception as exc:
            _record_op(db, attempt, vb_op_key, status="FAILED", error_message=str(exc)[:512])
            failed.append(vb_op_key)

        # Refresh FR version after replace_value_bases
        try:
            fr = customs_public.get_funding_request(db, funding_id)
        except Exception:
            pass

        # Op: replace_tax_lines
        tx_op_key = f"{base}_replace_tax_lines"
        try:
            if tax_lines:
                customs_public.replace_tax_lines(
                    db,
                    funding_id,
                    expected_version=fr.version,
                    lines=tax_lines,
                )
            _record_op(
                db,
                attempt,
                tx_op_key,
                status="SUCCEEDED",
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                details_json=json.dumps({"lines_count": len(tax_lines)}),
            )
            succeeded.append(tx_op_key)
        except Exception as exc:
            _record_op(db, attempt, tx_op_key, status="FAILED", error_message=str(exc)[:512])
            failed.append(tx_op_key)

        # Refresh again
        try:
            fr = customs_public.get_funding_request(db, funding_id)
        except Exception:
            pass

        # Op: replace_expense_lines
        ex_op_key = f"{base}_replace_expense_lines"
        try:
            if expense_lines:
                customs_public.replace_expense_lines(
                    db,
                    funding_id,
                    expected_version=fr.version,
                    lines=expense_lines,
                )
            _record_op(
                db,
                attempt,
                ex_op_key,
                status="SUCCEEDED",
                entity_type="customs_funding_request",
                entity_id=str(funding_id),
                details_json=json.dumps({"lines_count": len(expense_lines)}),
            )
            succeeded.append(ex_op_key)
        except Exception as exc:
            _record_op(db, attempt, ex_op_key, status="FAILED", error_message=str(exc)[:512])
            failed.append(ex_op_key)

        # Link document to funding request
        if promoted_doc_id and funding_id:
            try:
                documents_public.link_document(
                    db,
                    document_id=promoted_doc_id,
                    entity_type="customs_funding_request",
                    entity_id=str(funding_id),
                    role="solicitacao_numerario",
                )
            except Exception:
                pass  # Non-fatal

    # Final status
    if not failed:
        attempt.status = "SUCCEEDED"
    elif not succeeded:
        attempt.status = "FAILED"
    else:
        attempt.status = "PARTIAL"

    db.flush()

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_numerario_completed",
        reason_code="INGEST_NUMERARIO_COMMIT_DONE",
        details=json.dumps(
            {
                "document_id": document_id,
                "process_ids": process_ids,
                "status": attempt.status,
                "succeeded": succeeded,
                "failed": failed,
            }
        ),
    )

    return attempt
