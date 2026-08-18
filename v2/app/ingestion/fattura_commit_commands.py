"""Fattura commit commands — J3-I4.

Policy A/B/C1/C2 para Fattura → Invoice DRAFT via billing.public.

Regras rígidas:
- NUNCA criar Invoice com Order DRAFT (policy A só funciona com CONFIRMED)
- NUNCA confirmar Order silenciosamente (policy B bloqueia e retorna ORDER_DRAFT_MUST_CONFIRM)
- NUNCA criar Payment automático
- NUNCA inferir ACCONTO (DEC-ACCONTO-INVOICE pendente — criar FINAL por padrão)
- NUNCA emitir Invoice além de DRAFT no commit
- C2 requer: c2_confirm=True + c2_reason não-vazio + Audit + dual-auth billing:write

Policy:
  A — Order CONFIRMED existe → Invoice DRAFT criado
  B — Order DRAFT existe    → bloqueia, retorna ORDER_DRAFT_MUST_CONFIRM (422)
  C1 — Nenhuma Order        → cria reconstruction Order DRAFT, status PENDING_CONFIRM
  C2 — Sem Order + confirm  → cria reconstruction Order DRAFT + confirma + Invoice DRAFT
       (ONLY as explicit exception, com warning, reason, Audit, dual-auth)

Idempotência: mesma operation_key + mesmo fingerprint → retorna attempt existente.
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
from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.documents import public as documents_public
from app.ingestion.commit_failure import (
    CommitFailureTrail,
    CommitOperationFailed,
    reset_attempt_ledger,
)
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError
from app.ingestion.ir_models import IngestionDocument, IngestionRow
from app.ingestion.staging_queries import get_document_detail
from app.orders import public as orders_public
from app.ingestion import storage as quarantine_storage
from app.ingestion.fattura_line_match import (
    FatturaLinePlan,
    notes_with_price_divergence,
    plan_fattura_lines,
)
from app.ingestion.fattura_order_candidates import (
    FatturaOrderSuggestion,
    suggest_fattura_orders,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FatturaOrderDraftMustConfirm(IngestionError):
    """Policy B: Order DRAFT existe mas não pode ser faturada sem confirmação explícita."""
    def __init__(self, order_id: int) -> None:
        super().__init__(
            f"Order {order_id} está em DRAFT — confirme explicitamente antes de criar Invoice",
            code="order_draft_must_confirm",
        )
        self.order_id = order_id


class FatturaOrderPendingConfirm(IngestionError):
    """Policy C1: Order reconstruction DRAFT criada — aguarda confirmação humana."""
    def __init__(self, order_id: int) -> None:
        super().__init__(
            f"Order reconstruction DRAFT criada (id={order_id}) — "
            "aguarda confirmação explícita antes de criar Invoice",
            code="order_pending_confirm",
        )
        self.order_id = order_id


class FatturaC2MissingReason(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "Policy C2 requer c2_reason não-vazio (dual-auth exception)",
            code="c2_missing_reason",
        )


class FatturaOrderIdRequired(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "order_id é obrigatório para policy A/B — "
            "matching automático por número da fatura foi desativado.",
            code="order_id_required",
        )


class FatturaInvoiceConflict(IngestionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="fattura_invoice_conflict")


class FatturaCommitConflictFingerprint(IngestionError):
    def __init__(self, operation_key: str) -> None:
        super().__init__(
            f"operation_key '{operation_key}' já existe com fingerprint diferente — 409",
            code="commit_conflict_fingerprint",
        )


class FatturaCommitBlockedByIssues(IngestionError):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} issue(s) OPEN com severity ERROR bloqueiam o commit",
            code="commit_blocked_by_issues",
        )


class FatturaNoBillableLines(IngestionError):
    def __init__(self) -> None:
        super().__init__("nenhuma linha faturável", code="fattura_no_billable_lines")


class FatturaSkuNotOnOrder(IngestionError):
    def __init__(self, messages: list[str]) -> None:
        super().__init__(
            " ".join(messages) if messages else "SKU do PDF não está no pedido.",
            code="fattura_sku_not_on_order",
        )


class FatturaQtyExceedsRemaining(IngestionError):
    def __init__(self, messages: list[str]) -> None:
        super().__init__(
            " ".join(messages) if messages else "Quantidade do PDF excede o saldo a faturar.",
            code="fattura_qty_exceeds_remaining",
        )


class FatturaLineAmbiguous(IngestionError):
    def __init__(self, messages: list[str]) -> None:
        super().__init__(
            " ".join(messages) if messages else "Linha da Fattura ambígua — escolha explícita.",
            code="fattura_line_ambiguous",
        )


class FatturaLineChoiceInvalid(IngestionError):
    def __init__(self, messages: list[str]) -> None:
        super().__init__(
            " ".join(messages) if messages else "Escolha de linha inválida.",
            code="fattura_line_choice_invalid",
        )


def _choices_map(line_choices: list | None) -> dict[int, int] | None:
    if not line_choices:
        return None
    out: dict[int, int] = {}
    for raw in line_choices:
        if isinstance(raw, dict):
            row_index = int(raw["row_index"])
            order_item_id = int(raw["order_item_id"])
        else:
            row_index = int(raw.row_index)
            order_item_id = int(raw.order_item_id)
        if row_index in out and out[row_index] != order_item_id:
            raise FatturaLineChoiceInvalid(
                [f"Escolhas conflitantes para a linha PDF {row_index}."]
            )
        out[row_index] = order_item_id
    return out


def _raise_line_plan_blockers(plan: FatturaLinePlan) -> None:
    if plan.commitment_only:
        raise FatturaNoBillableLines()
    sku_msgs = [b.message for b in plan.blockers if b.code == "fattura_sku_not_on_order"]
    qty_msgs = [b.message for b in plan.blockers if b.code == "fattura_qty_exceeds_remaining"]
    amb_msgs = [b.message for b in plan.blockers if b.code == "fattura_line_ambiguous"]
    choice_msgs = [b.message for b in plan.blockers if b.code == "fattura_line_choice_invalid"]
    if sku_msgs:
        raise FatturaSkuNotOnOrder(sku_msgs)
    if qty_msgs:
        raise FatturaQtyExceedsRemaining(qty_msgs)
    if amb_msgs:
        raise FatturaLineAmbiguous(amb_msgs)
    if choice_msgs:
        raise FatturaLineChoiceInvalid(choice_msgs)
    if plan.blockers:
        first = plan.blockers[0]
        raise IngestionError(first.message, code=first.code)


def _preview_ops_for_line_plan(plan: FatturaLinePlan) -> list[FatturaPreviewOperation]:
    ops: list[FatturaPreviewOperation] = []
    if plan.commitment_only:
        ops.append(
            FatturaPreviewOperation(
                op_key="blocked_no_billable_lines",
                description=(
                    "BLOQUEADO: nenhuma linha faturável — este pedido só tem "
                    "linhas de compromisso. A Fattura com EAN real contra compromisso "
                    "é reconciliação (fora desta fatia)."
                ),
                params={"code": "fattura_no_billable_lines"},
            )
        )
        return ops
    for b in plan.blockers:
        ops.append(
            FatturaPreviewOperation(
                op_key=f"blocked_{b.code}",
                description=f"BLOQUEADO ({b.code}): {b.message}",
                params={"code": b.code, "sku": b.sku},
            )
        )
    if plan.ok:
        ops.append(
            FatturaPreviewOperation(
                op_key="map_invoice_items",
                description=(
                    f"Faturar {len(plan.items_payload)} linha(s) do PDF "
                    "(quantidade e preço do documento, não do pedido)"
                ),
                entity_type="invoice_item",
                params={"lines": [m.as_params() for m in plan.matches]},
            )
        )
    for m in plan.matches:
        if m.status == "ambiguous":
            continue
        if m.candidate_count > 1 and m.order_item_id is not None:
            ops.append(
                FatturaPreviewOperation(
                    op_key="match_choice",
                    description=(
                        f"Linha PDF {m.row_index} SKU {m.sku}: "
                        f"operador escolheu item #{m.order_item_id} "
                        f"(preço pedido {m.order_unit_price}, saldo {m.remaining_before})"
                    ),
                    params=m.as_params(),
                )
            )
    if plan.price_divergence_lines:
        ops.append(
            FatturaPreviewOperation(
                op_key="warn_price_divergence",
                description=(
                    "Divergência de preço (não bloqueia; a fatura segue o documento): "
                    + "; ".join(plan.price_divergence_lines)
                ),
                params={"lines": plan.price_divergence_lines},
            )
        )
    if plan.draft_overcommit:
        ops.append(
            FatturaPreviewOperation(
                op_key="warn_draft_overcommit",
                description=(
                    "Há rascunhos de fatura que, somados a esta Fattura, ultrapassam "
                    "o saldo do pedido. Rascunho não reserva saldo; o bloqueio ocorre na emissão."
                ),
            )
        )
    return ops


# ---------------------------------------------------------------------------
# Policy enum-like constants
# ---------------------------------------------------------------------------

POLICY_A = "A"   # Order CONFIRMED exists
POLICY_B = "B"   # Order DRAFT exists (must confirm separately)
POLICY_C1 = "C1"  # No Order → create reconstruction DRAFT
POLICY_C2 = "C2"  # No Order → reconstruct + confirm + Invoice (explicit exception)

VALID_POLICIES = {POLICY_A, POLICY_B, POLICY_C1, POLICY_C2}


# ---------------------------------------------------------------------------
# Fingerprint (reuses commit_commands logic; import to avoid duplication)
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
# Helpers to read IR fields
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


# ---------------------------------------------------------------------------
# Order matching
# ---------------------------------------------------------------------------


def _find_matching_order(
    db: Session,
    *,
    supplier_id: int,
    external_ref: str | None,
    order_id: int | None,
    policy: str,
):
    """Find an Order matching this Fattura.

    Returns the Order object or None.
    Priority:
    1. If order_id given → use it (all policies)
    2. For policies A/B only: auto-search by supplier_id + external_ref
    3. For C1/C2: user explicitly chose reconstruction — do NOT auto-search
    """
    if order_id is not None:
        try:
            return orders_public.get_order(db, order_id)
        except Exception:
            return None

    # A/B: matching automático por supplier+external_ref desativado (FIN-3).
    # C1/C2: reconstruction — não busca Order existente.
    _ = (supplier_id, external_ref, policy)
    return None


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


@dataclass
class FatturaPolicyMatch:
    policy: str
    order_id: int | None
    order_status: str | None
    order_code: str | None
    invoice_will_be_created: bool
    warning: str | None


@dataclass
class FatturaPreviewOperation:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class FatturaPreviewResult:
    document_id: int
    fingerprint: str
    policy_match: FatturaPolicyMatch
    operations: list[FatturaPreviewOperation]
    open_error_count: int
    can_commit: bool
    order_candidates: list[dict] = field(default_factory=list)
    order_candidates_reason: str | None = None
    line_matches: list[dict] = field(default_factory=list)
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_invoice_id: int | None = None


def preview_commit_fattura(
    db: Session,
    document_id: int,
    *,
    policy: str,
    order_id: int | None = None,
    c2_confirm: bool = False,
    c2_reason: str | None = None,
    line_choices: list | None = None,
) -> FatturaPreviewResult:
    """Calcula digest e lista de operações sem escrever nada nos owners."""
    if policy not in VALID_POLICIES:
        raise IngestionError(
            f"Policy inválida: '{policy}'. Valores permitidos: {sorted(VALID_POLICIES)}",
            code="invalid_policy",
        )

    doc = get_document_detail(db, document_id)
    fingerprint = _compute_fingerprint(db, document_id)
    choices = _choices_map(line_choices)

    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )

    existing_ok = (
        db.query(IngestionCommitAttempt)
        .filter(
            IngestionCommitAttempt.document_id == document_id,
            IngestionCommitAttempt.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitAttempt.id.desc())
        .first()
    )
    if existing_ok is not None:
        inv_id = None
        for op in existing_ok.operations or []:
            if op.entity_type == "invoice" and op.entity_id:
                try:
                    inv_id = int(op.entity_id)
                except (TypeError, ValueError):
                    continue
                break
        return FatturaPreviewResult(
            document_id=document_id,
            fingerprint=existing_ok.payload_fingerprint or fingerprint,
            policy_match=FatturaPolicyMatch(
                policy=policy,
                order_id=None,
                order_status=None,
                order_code=None,
                invoice_will_be_created=False,
                warning=None,
            ),
            operations=[
                FatturaPreviewOperation(
                    op_key=op.op_key,
                    description=op.op_key.replace("_", " "),
                    entity_type=op.entity_type,
                    params={"entity_id": op.entity_id} if op.entity_id else {},
                )
                for op in (existing_ok.operations or [])
            ],
            open_error_count=open_errors,
            can_commit=False,
            already_committed=True,
            last_succeeded_attempt_id=existing_ok.id,
            last_succeeded_invoice_id=inv_id,
        )

    supplier_id_str = _field_value(doc, "supplier_id_catalog")
    supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None

    invoice_number = _field_value(doc, "invoice_number")

    suggestion: FatturaOrderSuggestion | None = None
    if policy == POLICY_A:
        suggestion = suggest_fattura_orders(db, doc)

    # --- policy match analysis ---
    matched_order = None
    explicit_order_missing = policy in (POLICY_A, POLICY_B) and order_id is None
    if explicit_order_missing:
        extra = ""
        if suggestion is not None:
            n = len(suggestion.candidates)
            if n == 0:
                extra = " " + (suggestion.reason or "Nenhum pedido candidato.")
            elif n == 1:
                c = suggestion.candidates[0]
                extra = (
                    f" Pedido sugerido #{c.order_id} ({c.order_code}) — "
                    "confirme explicitamente; não há auto-commit."
                )
            else:
                extra = (
                    f" {n} pedidos candidatos — escolha um explicitamente; "
                    "o sistema não escolhe em silêncio."
                )
        policy_match = FatturaPolicyMatch(
            policy=policy,
            order_id=None,
            order_status=None,
            order_code=None,
            invoice_will_be_created=False,
            warning=(
                "order_id é obrigatório para policy A/B — "
                "informe o pedido explicitamente."
                + extra
            ),
        )
    else:
        if supplier_id or order_id is not None:
            matched_order = _find_matching_order(
                db,
                supplier_id=supplier_id or 0,
                external_ref=invoice_number,
                order_id=order_id,
                policy=policy,
            )
        policy_match = _analyze_policy(policy, matched_order, c2_confirm, c2_reason)

    ops: list[FatturaPreviewOperation] = []

    ops.append(FatturaPreviewOperation(
        op_key="store_document",
        description="Promover bytes da quarantine para Documents",
        entity_type="document",
        params={"occurrence_id": doc.occurrence_id},
    ))

    if suggestion is not None:
        ops.append(
            FatturaPreviewOperation(
                op_key="order_candidates",
                description=(
                    suggestion.reason
                    if not suggestion.candidates
                    else (
                        f"{len(suggestion.candidates)} pedido(s) candidato(s) — "
                        "o operador confirma o order_id."
                    )
                ),
                params={
                    "count": len(suggestion.candidates),
                    "reason": suggestion.reason,
                    "supplier_used": suggestion.supplier_used,
                    "supplier_unreliable": suggestion.supplier_unreliable,
                },
            )
        )

    will_create_invoice = (
        policy in (POLICY_A, POLICY_C2)
        and not explicit_order_missing
        and (
            policy == POLICY_C2
            or (matched_order is not None and matched_order.status == "CONFIRMED")
        )
    )

    if will_create_invoice:
        # Will create Invoice DRAFT
        ops.append(FatturaPreviewOperation(
            op_key="create_invoice",
            description=f"Criar Invoice DRAFT invoice_number={invoice_number} (policy={policy})",
            entity_type="invoice",
            params={
                "invoice_number": invoice_number,
                "policy": policy,
                "order_id": matched_order.id if matched_order else "(reconstruction)",
            },
        ))
        ops.append(FatturaPreviewOperation(
            op_key="set_terms",
            description="Aplicar scadenze e condições de pagamento na Invoice",
            entity_type="invoice_terms",
            params={},
        ))
        ops.append(FatturaPreviewOperation(
            op_key="link_document",
            description="Vincular Document à Invoice",
            entity_type="document_link",
            params={"entity_type": "invoice"},
        ))
    elif policy == POLICY_C1:
        ops.append(FatturaPreviewOperation(
            op_key="create_order_reconstruction",
            description="Criar Order reconstruction DRAFT (aguarda confirmação humana)",
            entity_type="order",
            params={"code": f"RECON-{invoice_number}", "note": "Policy C1"},
        ))
        ops.append(FatturaPreviewOperation(
            op_key="skip_invoice_pending_confirm",
            description="Invoice não criada — Order DRAFT aguarda confirmação (policy C1)",
            entity_type=None,
            params={},
        ))
    elif policy == POLICY_B:
        if matched_order and matched_order.status == "DRAFT":
            ops.append(FatturaPreviewOperation(
                op_key="blocked_order_draft",
                description=(
                    f"BLOQUEADO: Order {matched_order.id} está DRAFT. "
                    "Confirme explicitamente antes de criar Invoice."
                ),
                entity_type=None,
                params={"order_id": matched_order.id, "order_status": "DRAFT"},
            ))
        else:
            ops.append(FatturaPreviewOperation(
                op_key="policy_b_no_match",
                description="Policy B: nenhuma Order DRAFT encontrada para este fornecedor/ref",
                entity_type=None,
                params={},
            ))
    elif policy == POLICY_C2 and not explicit_order_missing:
        ops.append(FatturaPreviewOperation(
            op_key="c2_confirm_order",
            description="Policy C2: confirmar reconstruction Order na mesma sessão (EXCEPTION)",
            entity_type="order",
            params={"warning": "Dual-auth exception — c2_confirm=True required", "reason": c2_reason},
        ))

    line_plan_ok = True
    line_matches: list[dict] = []
    if (
        policy == POLICY_A
        and matched_order is not None
        and matched_order.status == "CONFIRMED"
    ):
        line_plan = plan_fattura_lines(db, doc, matched_order, line_choices=choices)
        ops.extend(_preview_ops_for_line_plan(line_plan))
        line_plan_ok = line_plan.ok
        line_matches = [m.as_params() for m in line_plan.matches]

    can_commit = (
        open_errors == 0
        and policy in (POLICY_A, POLICY_C1, POLICY_C2)
        and not explicit_order_missing
        and line_plan_ok
    )

    return FatturaPreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        policy_match=policy_match,
        operations=ops,
        open_error_count=open_errors,
        can_commit=can_commit,
        order_candidates=(
            [c.as_dict() for c in suggestion.candidates] if suggestion else []
        ),
        order_candidates_reason=suggestion.reason if suggestion else None,
        line_matches=line_matches,
    )


def _analyze_policy(
    policy: str,
    matched_order,
    c2_confirm: bool,
    c2_reason: str | None,
) -> FatturaPolicyMatch:
    if matched_order is None:
        if policy == POLICY_A:
            return FatturaPolicyMatch(
                policy=policy,
                order_id=None,
                order_status=None,
                order_code=None,
                invoice_will_be_created=False,
                warning="Policy A selecionada mas nenhuma Order CONFIRMED encontrada",
            )
        elif policy == POLICY_B:
            return FatturaPolicyMatch(
                policy=policy,
                order_id=None,
                order_status=None,
                order_code=None,
                invoice_will_be_created=False,
                warning="Policy B selecionada mas nenhuma Order DRAFT encontrada",
            )
        elif policy == POLICY_C1:
            return FatturaPolicyMatch(
                policy=policy,
                order_id=None,
                order_status=None,
                order_code=None,
                invoice_will_be_created=False,
                warning=None,
            )
        elif policy == POLICY_C2:
            return FatturaPolicyMatch(
                policy=policy,
                order_id=None,
                order_status=None,
                order_code=None,
                invoice_will_be_created=c2_confirm and bool(c2_reason),
                warning=(
                    "EXCEPTION C2: reconstruct+confirm na mesma sessão. "
                    "Dual-auth obrigatória. Auditado."
                ),
            )
    else:
        return FatturaPolicyMatch(
            policy=policy,
            order_id=matched_order.id,
            order_status=matched_order.status,
            order_code=matched_order.code,
            invoice_will_be_created=(
                policy == POLICY_A and matched_order.status == "CONFIRMED"
            ),
            warning=(
                f"Order {matched_order.id} está {matched_order.status}"
                if matched_order.status != "CONFIRMED" and policy == POLICY_A
                else None
            ),
        )


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------


def execute_commit_fattura(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    policy: str,
    order_id: int | None,
    c2_confirm: bool,
    c2_reason: str | None,
    attachments_path: Path,
    quarantine_path: Path,
    pending_files: list[Path] | None = None,
    line_choices: list | None = None,
) -> IngestionCommitAttempt:
    """Executa commit idempotente: promote document + Invoice DRAFT via policy A/B/C1/C2.

    Regras de produto:
    - A: Order CONFIRMED → Invoice DRAFT
    - B: Order DRAFT → bloqueia (FatturaOrderDraftMustConfirm)
    - C1: Sem Order → cria reconstruction DRAFT, retorna PENDING_CONFIRM
    - C2: Sem Order, c2_confirm=True → cria reconstruction + confirma + Invoice DRAFT
         (dual-auth obrigatória, Audit, aviso)

    Tudo-ou-nada (RUX-2R-b): a route só faz ``uow.commit()`` se o attempt sair
    SUCCEEDED; qualquer outro estado reverte a transação e vira trilha de falha.
    O arquivo é escrito em área temporária e promovido depois do commit.
    """
    from app.ingestion.models import IngestionOccurrence

    if policy not in VALID_POLICIES:
        raise IngestionError(
            f"Policy inválida: '{policy}'. Valores permitidos: {sorted(VALID_POLICIES)}",
            code="invalid_policy",
        )

    existing_ok = (
        db.query(IngestionCommitAttempt)
        .filter(
            IngestionCommitAttempt.document_id == document_id,
            IngestionCommitAttempt.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitAttempt.id.desc())
        .first()
    )
    if existing_ok is not None:
        return existing_ok

    if policy == POLICY_C2:
        if not c2_confirm:
            raise IngestionError(
                "Policy C2 requer c2_confirm=true explícito",
                code="c2_missing_confirm",
            )
        if not c2_reason or not c2_reason.strip():
            raise FatturaC2MissingReason()

    if policy in (POLICY_A, POLICY_B) and order_id is None:
        raise FatturaOrderIdRequired()

    doc = get_document_detail(db, document_id)
    choices = _choices_map(line_choices)

    # Check for blocker issues
    open_errors = [i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"]
    if open_errors:
        raise FatturaCommitBlockedByIssues(len(open_errors))

    line_plan: FatturaLinePlan | None = None
    if policy == POLICY_A and order_id is not None:
        early_order = _find_matching_order(
            db,
            supplier_id=0,
            external_ref=None,
            order_id=order_id,
            policy=policy,
        )
        if early_order is None:
            pass
        elif early_order.status == "DRAFT":
            raise FatturaOrderDraftMustConfirm(early_order.id)
        elif early_order.status == "CONFIRMED":
            line_plan = plan_fattura_lines(db, doc, early_order, line_choices=choices)
            _raise_line_plan_blockers(line_plan)

    fingerprint = _compute_fingerprint(db, document_id)

    # --- idempotency check ---
    existing = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    attempt: IngestionCommitAttempt
    if existing is not None:
        if existing.payload_fingerprint != fingerprint:
            raise FatturaCommitConflictFingerprint(operation_key)
        if existing.status == "SUCCEEDED":
            return existing
        # Tentativa anterior não persistiu nada (rollback) — reexecuta do zero.
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
            if existing is None or existing.payload_fingerprint != fingerprint:
                raise FatturaCommitConflictFingerprint(operation_key)
            if existing.status == "SUCCEEDED":
                return existing
            attempt = existing
            attempt.actor_id = actor_id
            reset_attempt_ledger(db, attempt)

    succeeded_ops: list[str] = []

    def _fail(op_key: str, error: Exception | str) -> None:
        message = (str(error)[:512] or error.__class__.__name__) if isinstance(
            error, Exception
        ) else error[:512]
        trail = CommitFailureTrail(
            document_id=document_id,
            operation_key=operation_key,
            payload_fingerprint=fingerprint,
            actor_id=actor_id,
            failed_op_key=op_key,
            error_message=message,
            rolled_back_ops=list(succeeded_ops),
            context={"doc_type": "FATTURA", "policy": policy},
        )
        if isinstance(error, Exception):
            raise CommitOperationFailed(op_key, message, trail=trail) from error
        raise CommitOperationFailed(op_key, message, trail=trail)

    # --- IR fields ---
    supplier_id_str = _field_value(doc, "supplier_id_catalog")
    supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None

    invoice_number = _field_value(doc, "invoice_number")
    invoice_date_str = _field_value(doc, "invoice_date")
    invoice_date = None
    if invoice_date_str:
        try:
            invoice_date = date.fromisoformat(invoice_date_str)
        except ValueError:
            invoice_date = None

    payment_terms_text = _field_value(doc, "payment_terms_text")
    scadenze_json_str = _field_value(doc, "scadenze_json")
    scadenze_data: list[dict] = []
    if scadenze_json_str:
        try:
            scadenze_data = json.loads(scadenze_json_str)
        except (json.JSONDecodeError, TypeError):
            scadenze_data = []

    # --- Op 1: store_document ---
    promoted_doc_id: int | None = None
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
        promoted = documents_public.store_document_pending(
            db,
            attachments_path=attachments_path,
            actor_id=actor_id,
            filename=occ.original_filename or f"fattura_{document_id}.pdf",
            content=pdf_bytes,
            mime_type=occ.detected_mime or "application/pdf",
            pending_files=pending_files if pending_files is not None else [],
        )
        promoted_doc_id = promoted.id
    except Exception as exc:
        _fail("store_document", exc)
    _record_op(
        db, attempt, "store_document",
        status="SUCCEEDED",
        entity_type="document",
        entity_id=str(promoted_doc_id),
    )
    succeeded_ops.append("store_document")

    # --- Op 2: match_or_create_order (policies A/B/C1/C2) ---
    target_order_id: int | None = None
    target_order_version: int = 1

    if supplier_id is None and order_id is None:
        _record_op(
            db, attempt, "match_order",
            status="SKIPPED",
            details_json=json.dumps({"reason": "supplier_id ausente no IR"}),
        )
    else:
        matched_order = _find_matching_order(
            db,
            supplier_id=supplier_id or 0,
            external_ref=invoice_number,
            order_id=order_id,
            policy=policy,
        )

        if policy == POLICY_A:
            # Must have CONFIRMED order
            if matched_order is None:
                _fail(
                    "match_order",
                    "Policy A: nenhuma Order encontrada para este fornecedor/ref",
                )
            elif matched_order.status == "DRAFT":
                # Policy A + DRAFT → same violation as B: must not invoice DRAFT
                raise FatturaOrderDraftMustConfirm(matched_order.id)
            elif matched_order.status == "CONFIRMED":
                target_order_id = matched_order.id
                target_order_version = matched_order.version
                _record_op(
                    db, attempt, "match_order",
                    status="SUCCEEDED",
                    entity_type="order",
                    entity_id=str(matched_order.id),
                    details_json=json.dumps({
                        "policy": "A", "order_status": "CONFIRMED",
                    }),
                )
                succeeded_ops.append("match_order")
            else:
                _fail(
                    "match_order",
                    f"Policy A: Order {matched_order.id} status={matched_order.status}",
                )

        elif policy == POLICY_B:
            # Signal: order DRAFT exists, must confirm separately
            if matched_order and matched_order.status == "DRAFT":
                raise FatturaOrderDraftMustConfirm(matched_order.id)
            else:
                _record_op(
                    db, attempt, "match_order",
                    status="SKIPPED",
                    details_json=json.dumps({
                        "reason": "Policy B: nenhuma Order DRAFT encontrada",
                        "policy": "B",
                    }),
                )

        elif policy == POLICY_C1:
            # Create reconstruction DRAFT, do NOT invoice
            if matched_order is not None:
                _record_op(
                    db, attempt, "match_order",
                    status="SKIPPED",
                    details_json=json.dumps({
                        "reason": "Policy C1 mas Order já existe — use A ou B",
                        "order_id": matched_order.id,
                        "order_status": matched_order.status,
                    }),
                )
            else:
                recon_code = f"RECON-{invoice_number or document_id}-{document_id}"
                try:
                    recon_order = orders_public.create_order(
                        db,
                        code=recon_code,
                        supplier_id=supplier_id,
                        created_by_actor_id=actor_id,
                        currency="EUR",
                        order_date=invoice_date or date.today(),
                        source_system="INGESTION",
                        notes=(
                            f"Reconstruction DRAFT via ingestão Fattura {invoice_number} "
                            f"(IR doc={document_id}, policy=C1)"
                        ),
                        external_ref=invoice_number,
                    )
                    target_order_id = recon_order.id
                    _record_op(
                        db, attempt, "create_order_reconstruction",
                        status="SUCCEEDED",
                        entity_type="order",
                        entity_id=str(recon_order.id),
                        details_json=json.dumps({
                            "policy": "C1",
                            "code": recon_code,
                        }),
                    )
                    succeeded_ops.append("create_order_reconstruction")
                    audit_public.record_event(
                        db,
                        actor_id=actor_id,
                        entity_type="ingestion_commit_attempt",
                        entity_id=str(attempt.id),
                        action="order_reconstruction_created",
                        reason_code="INGEST_FATTURA_C1_RECON",
                        details=json.dumps({
                            "document_id": document_id,
                            "order_id": recon_order.id,
                            "order_code": recon_code,
                            "policy": "C1",
                        }),
                    )
                except Exception as exc:
                    _fail("create_order_reconstruction", exc)

            # C1: link document to reconstruction order then return PENDING_CONFIRM
            if promoted_doc_id is not None and target_order_id is not None:
                try:
                    documents_public.link_document(
                        db,
                        document_id=promoted_doc_id,
                        entity_type="order",
                        entity_id=str(target_order_id),
                        role="source",
                    )
                except Exception as exc:
                    _fail("link_document_to_order", exc)
                _record_op(
                    db, attempt, "link_document_to_order",
                    status="SUCCEEDED",
                    entity_type="document_link",
                )
                succeeded_ops.append("link_document_to_order")

            attempt.status = "SUCCEEDED"
            db.flush()
            audit_public.record_event(
                db,
                actor_id=actor_id,
                entity_type="ingestion_commit_attempt",
                entity_id=str(attempt.id),
                action="commit_completed",
                reason_code="INGEST_FATTURA_C1_PENDING",
                details=json.dumps({
                    "document_id": document_id,
                    "status": "PENDING_CONFIRM",
                    "policy": "C1",
                    "order_id": target_order_id,
                }),
            )
            return attempt

        elif policy == POLICY_C2:
            # Create reconstruction DRAFT, confirm it, then create Invoice
            if matched_order is not None:
                _record_op(
                    db, attempt, "match_order",
                    status="SKIPPED",
                    details_json=json.dumps({
                        "reason": "Policy C2 mas Order já existe — use A ou B",
                        "order_id": matched_order.id,
                    }),
                )
                # Fallback to matched order if CONFIRMED
                if matched_order.status == "CONFIRMED":
                    target_order_id = matched_order.id
                    target_order_version = matched_order.version
            else:
                recon_code = f"RECON-C2-{invoice_number or document_id}-{document_id}"
                try:
                    recon_order = orders_public.create_order(
                        db,
                        code=recon_code,
                        supplier_id=supplier_id,
                        created_by_actor_id=actor_id,
                        currency="EUR",
                        order_date=invoice_date or date.today(),
                        source_system="INGESTION",
                        notes=(
                            f"Reconstruction via ingestão Fattura {invoice_number} "
                            f"(IR doc={document_id}, policy=C2, EXCEPTION) — reason: {c2_reason}"
                        ),
                        external_ref=invoice_number,
                    )
                    _record_op(
                        db, attempt, "create_order_reconstruction",
                        status="SUCCEEDED",
                        entity_type="order",
                        entity_id=str(recon_order.id),
                        details_json=json.dumps({"policy": "C2", "code": recon_code}),
                    )
                    succeeded_ops.append("create_order_reconstruction")
                except Exception as exc:
                    _fail("create_order_reconstruction", exc)

                # Populate reconstruction order from IR line items (needed to allow confirmation)
                current_order_version = recon_order.version
                for row in (doc.rows or []):
                    cells = _row_cells(row)
                    product_id_str = _cell_value(cells, "product_id_catalog")
                    qty_str = _cell_value(cells, "quantity")
                    price_str = _cell_value(cells, "unit_price")
                    unit = _cell_value(cells, "unit") or "PZ"
                    if (
                        product_id_str
                        and product_id_str.strip().lstrip("-").isdigit()
                        and int(product_id_str) > 0
                        and qty_str
                    ):
                        try:
                            updated = orders_public.add_item(
                                db,
                                recon_order.id,
                                expected_version=current_order_version,
                                product_id=int(product_id_str),
                                quantity=qty_str,
                                unit_price=price_str,
                                unit=unit,
                            )
                            current_order_version = updated.version
                        except Exception as exc:
                            _fail(f"add_item_{row.row_index}", exc)

                # Confirm reconstruction
                try:
                    orders_public.confirm_order(
                        db, recon_order.id, expected_version=current_order_version
                    )
                    recon_order = orders_public.get_order(db, recon_order.id)
                    target_order_id = recon_order.id
                    target_order_version = recon_order.version
                    _record_op(
                        db, attempt, "confirm_order_c2",
                        status="SUCCEEDED",
                        entity_type="order",
                        entity_id=str(recon_order.id),
                        details_json=json.dumps({
                            "policy": "C2",
                            "reason": c2_reason,
                            "WARNING": "EXCEPTION — dual-auth required",
                        }),
                    )
                    succeeded_ops.append("confirm_order_c2")
                    audit_public.record_event(
                        db,
                        actor_id=actor_id,
                        entity_type="ingestion_commit_attempt",
                        entity_id=str(attempt.id),
                        action="order_confirmed_c2_exception",
                        reason_code="INGEST_FATTURA_C2_CONFIRM",
                        details=json.dumps({
                            "document_id": document_id,
                            "order_id": target_order_id,
                            "c2_reason": c2_reason,
                            "WARNING": (
                                "Policy C2 exception — reconstruct+confirm same session. "
                                "Dual-auth required. Reviewed by: " + actor_id
                            ),
                        }),
                    )
                except Exception as exc:
                    _fail("confirm_order_c2", exc)

    # --- Op 3: create_invoice (if CONFIRMED order available) ---
    invoice_id: int | None = None
    invoice_version: int = 1

    if target_order_id is not None and policy in (POLICY_A, POLICY_C2):
        try:
            if line_plan is None:
                target_order = orders_public.get_order(db, target_order_id)
                line_plan = plan_fattura_lines(
                    db, doc, target_order, line_choices=choices
                )
                _raise_line_plan_blockers(line_plan)
            if not line_plan.items_payload:
                raise FatturaNoBillableLines()
            base_notes = (
                f"Criada via ingestão Fattura {invoice_number} "
                f"(IR doc={document_id}, policy={policy})"
            )
            invoice = billing_public.create_invoice(
                db,
                order_id=target_order_id,
                invoice_number=invoice_number or f"INV-{document_id}",
                created_by_actor_id=actor_id,
                invoice_type="FINAL",
                invoice_date=invoice_date,
                notes=base_notes,
                order_item_ids=line_plan.order_item_ids,
            )
            invoice_id = invoice.id
            invoice_version = invoice.version
            invoice = billing_public.replace_items(
                db,
                invoice_id=invoice.id,
                expected_version=invoice_version,
                items=line_plan.items_payload,
            )
            invoice_version = invoice.version
            dest_iban = _field_value(doc, "destination_iban")
            dest_bank = _field_value(doc, "destination_bank")
            notes = notes_with_price_divergence(base_notes, line_plan)
            invoice = billing_public.update_invoice_header(
                db,
                invoice.id,
                expected_version=invoice_version,
                destination_iban=dest_iban,
                destination_bank=dest_bank,
                terms_from_document=True,
                notes=notes,
            )
            invoice_version = invoice.version
            if line_plan.price_divergence_lines:
                details = json.dumps({
                    "invoice_id": invoice.id,
                    "invoice_number": invoice_number,
                    "order_id": target_order_id,
                    "lines": line_plan.price_divergence_lines,
                })
                audit_public.record_event(
                    db,
                    actor_id=actor_id,
                    entity_type="invoice",
                    entity_id=str(invoice.id),
                    action="invoice_price_divergence",
                    reason_code="FATTURA_PRICE_DIVERGENCE",
                    details=details,
                )
                audit_public.record_event(
                    db,
                    actor_id=actor_id,
                    entity_type="order",
                    entity_id=str(target_order_id),
                    action="invoice_price_divergence",
                    reason_code="FATTURA_PRICE_DIVERGENCE",
                    details=details,
                )
            _record_op(
                db, attempt, "create_invoice",
                status="SUCCEEDED",
                entity_type="invoice",
                entity_id=str(invoice.id),
                details_json=json.dumps({
                    "invoice_number": invoice_number,
                    "invoice_type": "FINAL",
                    "status": "DRAFT",
                    "policy": policy,
                    "pdf_line_count": len(line_plan.items_payload),
                    "price_divergence": bool(line_plan.price_divergence_lines),
                }),
            )
            succeeded_ops.append("create_invoice")
        except IngestionError:
            raise
        except Exception as exc:
            _fail("create_invoice", exc)
    elif target_order_id is None and policy in (POLICY_A, POLICY_C2):
        _record_op(
            db, attempt, "skip_invoice",
            status="SKIPPED",
            details_json=json.dumps({"reason": "Sem order_id — Invoice não criada"}),
        )

    # --- Op 4: set_terms (payment terms + scadenze) ---
    if invoice_id is not None and scadenze_data:
        try:
            terms = [
                {"due_date": s["due_date_iso"] or s["due_date_raw"], "amount": s["amount"]}
                for s in scadenze_data
                if s.get("due_date_iso") or s.get("due_date_raw")
            ]
            if terms:
                billing_public.set_terms(
                    db,
                    invoice_id=invoice_id,
                    expected_version=invoice_version,
                    mode="AMOUNT",
                    terms=terms,
                )
                _record_op(
                    db, attempt, "set_terms",
                    status="SUCCEEDED",
                    entity_type="invoice_terms",
                    entity_id=str(invoice_id),
                    details_json=json.dumps({
                        "mode": "AMOUNT",
                        "count": len(terms),
                        "payment_terms_text": payment_terms_text,
                    }),
                )
                succeeded_ops.append("set_terms")
        except Exception as exc:
            _fail("set_terms", exc)

    # --- Op 5: link_document to Invoice ---
    if promoted_doc_id is not None and invoice_id is not None:
        try:
            documents_public.link_document(
                db,
                document_id=promoted_doc_id,
                entity_type="invoice",
                entity_id=str(invoice_id),
                role="source",
            )
            _record_op(
                db, attempt, "link_document",
                status="SUCCEEDED",
                entity_type="document_link",
                entity_id=f"{promoted_doc_id}→invoice:{invoice_id}",
            )
            succeeded_ops.append("link_document")
        except Exception as exc:
            _fail("link_document", exc)

    # --- also link ingestion document to promoted document ---
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

    # --- final status ---
    attempt.status = "SUCCEEDED"
    db.flush()

    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_completed",
        reason_code="INGEST_FATTURA_COMMIT_DONE",
        details=json.dumps({
            "document_id": document_id,
            "status": attempt.status,
            "policy": policy,
            "order_id": target_order_id,
            "invoice_id": invoice_id,
            "succeeded_ops": succeeded_ops,
        }),
    )
    return attempt
