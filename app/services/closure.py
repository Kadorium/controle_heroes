from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    RECONCILIATION_TOLERANCE_AMOUNT,
    ClosureStatus,
    ClosureType,
    CustomsDocumentStatus,
    ReconciliationStatus,
)
from app.models import (
    CustomsDocument,
    DocumentAttachment,
    ImportationClosure,
    ImportationOrder,
    LandedCostVersion,
    Reconciliation,
    StatusTransitionLog,
)
from app.services.auth import write_audit_log
from app.services.finance import importation_financial_summary
from app.services.nationalization import quantity_chain
from app.services.reconciliation import blocking_reconciliations, run_reconciliations


class ClosureError(Exception):
    pass


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


CLOSED_STATUS = "CLOSED"
REOPENED_STATUS = "REOPENED"


def get_close_checklist(db: Session, importation_id: int) -> list[dict]:
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ClosureError("Importação não encontrada")

    run_reconciliations(db, importation_id)
    checks: list[dict] = []

    invoices_ok = bool(imp.invoices) if hasattr(imp, "invoices") else True
    from app.models import Invoice

    inv_count = db.query(Invoice).filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True)).count()
    checks.append({"id": "invoices", "label": "Invoices cadastradas", "passed": inv_count > 0})

    summary = importation_financial_summary(db, imp)
    fin_ok = summary["consolidated_balance"] is None or _d(
        Decimal(str(summary["consolidated_balance"])) if summary["consolidated_balance"] is not None else None
    ).copy_abs() <= RECONCILIATION_TOLERANCE_AMOUNT
    checks.append({"id": "finance", "label": "Saldo financeiro coerente", "passed": fin_ok})

    di_ok = (
        db.query(CustomsDocument)
        .filter(
            CustomsDocument.importation_id == importation_id,
            CustomsDocument.status == CustomsDocumentStatus.OFFICIAL.value,
            CustomsDocument.is_valid.is_(True),
        )
        .count()
        > 0
    )
    checks.append({"id": "customs", "label": "DI/DUIMP oficial válida", "passed": di_ok})

    proforma = (
        db.query(DocumentAttachment)
        .filter(
            DocumentAttachment.entity_type == "importation_order",
            DocumentAttachment.entity_id == str(importation_id),
            DocumentAttachment.document_type == "PROFORMA",
            DocumentAttachment.is_current_version.is_(True),
        )
        .count()
        > 0
    )
    checks.append({"id": "proforma", "label": "Documento PROFORMA anexado", "passed": proforma})

    lc_final = (
        db.query(LandedCostVersion)
        .filter(
            LandedCostVersion.importation_id == importation_id,
            LandedCostVersion.version_type == "FINAL",
        )
        .first()
    )
    checks.append({"id": "landed_cost", "label": "Landed cost FINAL calculado", "passed": lc_final is not None})

    chain = quantity_chain(db, importation_id)
    nat_ok = any(c["quantity_nationalized"] > 0 for c in chain) if chain else False
    checks.append({"id": "nationalization", "label": "Nacionalização registrada", "passed": nat_ok})

    blocking = blocking_reconciliations(db, importation_id)
    checks.append(
        {
            "id": "reconciliations",
            "label": "Conciliações sem divergência bloqueante",
            "passed": len(blocking) == 0,
            "blocking_count": len(blocking),
        }
    )

    return checks


def build_snapshot(db: Session, importation_id: int, lc_version_id: int | None) -> dict:
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ClosureError("Importação não encontrada")

    summary = importation_financial_summary(db, imp)
    chain = quantity_chain(db, importation_id)
    reconciliations = (
        db.query(Reconciliation).filter(Reconciliation.importation_id == importation_id).all()
    )
    lc = None
    if lc_version_id:
        lc = db.query(LandedCostVersion).filter(LandedCostVersion.id == lc_version_id).first()

    return {
        "po_number": imp.po_number,
        "currency": imp.currency,
        "current_status": imp.current_status,
        "estimated_total": str(imp.estimated_total) if imp.estimated_total else None,
        "financial_summary": {
            k: str(v) if isinstance(v, Decimal) else v for k, v in summary.items() if k != "invoices"
        },
        "quantity_chain": chain,
        "landed_cost_version_id": lc_version_id,
        "landed_cost_total": str(lc.total_cost) if lc and lc.total_cost else None,
        "reconciliations": [
            {
                "id": r.id,
                "pair_type": r.pair_type,
                "status": r.status,
                "variance_value": str(r.variance_value) if r.variance_value is not None else None,
            }
            for r in reconciliations
        ],
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }


def _next_closure_version(db: Session, importation_id: int) -> int:
    last = (
        db.query(ImportationClosure)
        .filter(ImportationClosure.importation_id == importation_id)
        .order_by(ImportationClosure.closure_version.desc())
        .first()
    )
    return (last.closure_version + 1) if last else 1


def close_importation(
    db: Session,
    importation_id: int,
    *,
    user_id: int | None,
    landed_cost_version_id: int | None = None,
    approved_reconciliation_ids: list[int] | None = None,
    reason_code_id: int | None = None,
    justification: str | None = None,
) -> ImportationClosure:
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ClosureError("Importação não encontrada")
    if imp.current_status == CLOSED_STATUS:
        raise ClosureError("Importação já está fechada")

    checklist = get_close_checklist(db, importation_id)
    failed = [c for c in checklist if not c["passed"] and c["id"] != "reconciliations"]
    if failed:
        raise ClosureError(f"Pendências no checklist: {', '.join(c['label'] for c in failed)}")

    blocking = blocking_reconciliations(db, importation_id)
    approved_ids = set(approved_reconciliation_ids or [])
    closure_type = ClosureType.CLEAN.value

    if blocking:
        if approved_ids:
            if not reason_code_id and not (justification or "").strip():
                raise ClosureError(
                    "Divergências bloqueantes pendentes — aprove formalmente ou resolva antes de fechar"
                )
            closure_type = ClosureType.WITH_APPROVED_VARIANCE.value
            from app.services.reconciliation import approve_reconciliation

            for rec in blocking:
                if rec.id in approved_ids:
                    approve_reconciliation(
                        db, rec, user_id=user_id, reason_code_id=reason_code_id, justification=justification
                    )
        remaining = blocking_reconciliations(db, importation_id)
        if remaining:
            raise ClosureError(
                "Divergências bloqueantes pendentes — aprove formalmente ou resolva antes de fechar"
            )

    lc = None
    if landed_cost_version_id:
        lc = db.query(LandedCostVersion).filter(LandedCostVersion.id == landed_cost_version_id).first()
    if not lc:
        lc = (
            db.query(LandedCostVersion)
            .filter(
                LandedCostVersion.importation_id == importation_id,
                LandedCostVersion.version_type == "FINAL",
            )
            .order_by(LandedCostVersion.version_number.desc())
            .first()
        )
    if not lc:
        raise ClosureError("Fechamento exige versão de landed cost FINAL")

    prev_active = (
        db.query(ImportationClosure)
        .filter(
            ImportationClosure.importation_id == importation_id,
            ImportationClosure.status == ClosureStatus.ACTIVE.value,
        )
        .all()
    )
    for p in prev_active:
        p.status = ClosureStatus.REOPENED.value

    snapshot = build_snapshot(db, importation_id, lc.id)
    now = datetime.now(timezone.utc)
    old_status = imp.current_status
    closure = ImportationClosure(
        importation_id=importation_id,
        closure_version=_next_closure_version(db, importation_id),
        landed_cost_version_id=lc.id,
        snapshot_json=snapshot,
        closure_type=closure_type,
        status=ClosureStatus.ACTIVE.value,
        closed_by_id=user_id,
        closed_at=now,
        close_reason_code_id=reason_code_id if closure_type == ClosureType.WITH_APPROVED_VARIANCE.value else None,
        close_justification=justification,
        approved_reconciliation_ids=list(approved_ids) if approved_ids else None,
    )
    db.add(closure)

    imp.current_status = CLOSED_STATUS
    imp.closed_at = now
    imp.reopened_at = None

    db.add(
        StatusTransitionLog(
            importation_id=str(importation_id),
            from_status=old_status,
            to_status=CLOSED_STATUS,
            action="close",
            user_id=user_id,
            reason_code_id=reason_code_id,
            comment=justification,
            blocking_checks={"checklist": checklist},
        )
    )
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="importation_closure",
        entity_id=str(importation_id),
        action="close",
        new_value=f"v{closure.closure_version}:{closure_type}",
        reason_code_id=reason_code_id,
        justification=justification,
    )
    db.commit()
    db.refresh(closure)
    return closure


def reopen_importation(
    db: Session,
    importation_id: int,
    *,
    user_id: int | None,
    reason_code_id: int | None,
    justification: str | None,
) -> ImportationOrder:
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ClosureError("Importação não encontrada")
    if imp.current_status != CLOSED_STATUS:
        raise ClosureError("Importação não está fechada")
    if not reason_code_id and not (justification or "").strip():
        raise ClosureError("Reabertura exige reason_code e justificativa")

    active = (
        db.query(ImportationClosure)
        .filter(
            ImportationClosure.importation_id == importation_id,
            ImportationClosure.status == ClosureStatus.ACTIVE.value,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if active:
        active.status = ClosureStatus.REOPENED.value
        active.reopened_by_id = user_id
        active.reopened_at = now
        active.reopen_reason_code_id = reason_code_id
        active.reopen_justification = justification

    old_status = imp.current_status
    imp.current_status = REOPENED_STATUS
    imp.reopened_at = now

    db.add(
        StatusTransitionLog(
            importation_id=str(importation_id),
            from_status=old_status,
            to_status=REOPENED_STATUS,
            action="reopen",
            user_id=user_id,
            reason_code_id=reason_code_id,
            comment=justification,
        )
    )
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="importation_order",
        entity_id=str(importation_id),
        action="reopen",
        field_changed="current_status",
        old_value=CLOSED_STATUS,
        new_value=REOPENED_STATUS,
        reason_code_id=reason_code_id,
        justification=justification,
    )
    db.commit()
    db.refresh(imp)
    return imp


def _timeline_entity_label(entity_type: str) -> str:
    labels = {
        "importation_order": "Importação",
        "importation_closure": "Fechamento",
        "nationalization": "Nacionalização",
        "stock_entry": "Entrada em estoque",
        "payment": "Pagamento",
        "discount": "Desconto",
        "credit": "Crédito",
        "expense": "Despesa",
    }
    return labels.get(entity_type, entity_type.replace("_", " ").title())


def _timeline_summary(action: str, entity_type: str, field_changed: str | None, new_value: str | None) -> str:
    entity = _timeline_entity_label(entity_type)
    if action == "create":
        return f"{entity} registrado(a)"
    if action == "cancel":
        return f"{entity} anulado(a)"
    if field_changed == "current_status" and new_value:
        return f"Status alterado para {new_value}"
    if field_changed and new_value:
        return f"{entity}: {field_changed} atualizado"
    return f"{entity} — {action}"


def get_timeline(db: Session, importation_id: int) -> list[dict]:
    from app.models import AuditLog, User

    audit = (
        db.query(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .filter(
            AuditLog.entity_type.in_(
                [
                    "importation_order",
                    "importation_closure",
                    "nationalization",
                    "stock_entry",
                    "payment",
                    "discount",
                    "credit",
                    "expense",
                ]
            ),
            AuditLog.entity_id == str(importation_id),
        )
        .order_by(AuditLog.timestamp)
        .all()
    )
    transitions = (
        db.query(StatusTransitionLog)
        .filter(StatusTransitionLog.importation_id == str(importation_id))
        .order_by(StatusTransitionLog.timestamp)
        .all()
    )
    events = []
    for t in transitions:
        events.append(
            {
                "type": "status_transition",
                "timestamp": t.timestamp.isoformat(),
                "action": t.action,
                "from_status": t.from_status,
                "to_status": t.to_status,
                "comment": t.comment,
                "user_name": None,
                "entity_label": "Status",
                "summary": f"Status: {t.from_status or '—'} → {t.to_status}",
            }
        )
    for a, user_name in audit:
        events.append(
            {
                "type": "audit",
                "timestamp": a.timestamp.isoformat(),
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_label": _timeline_entity_label(a.entity_type),
                "field_changed": a.field_changed,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "user_name": user_name,
                "justification": a.justification,
                "summary": _timeline_summary(a.action, a.entity_type, a.field_changed, a.new_value),
            }
        )
    events.sort(key=lambda e: e["timestamp"])
    return events
