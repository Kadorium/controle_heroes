"""Comandos Reconciliation — persiste pares; não importa Costing."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.reconciliation.errors import PairConflict, PairNotFound
from app.reconciliation.models import ReconciliationCase, ReconciliationPair


def replace_pairs_for_version(db: Session, costing_version_id: int, pairs: list[dict]) -> ReconciliationCase:
    existing = (
        db.query(ReconciliationCase)
        .filter(ReconciliationCase.costing_version_id == costing_version_id)
        .first()
    )
    if existing:
        for p in list(existing.pairs):
            db.delete(p)
        case = existing
    else:
        case = ReconciliationCase(costing_version_id=costing_version_id, status="OPEN")
        db.add(case)
        db.flush()
    for raw in pairs:
        db.add(
            ReconciliationPair(
                case_id=case.id,
                pair_type=raw["pair_type"][:64],
                left_label=raw["left_label"][:256],
                left_value=(str(raw.get("left_value"))[:2000] if raw.get("left_value") is not None else None),
                right_label=raw["right_label"][:256],
                right_value=(str(raw.get("right_value"))[:2000] if raw.get("right_value") is not None else None),
                delta=raw.get("delta"),
                unit=raw.get("unit"),
                tolerance=raw.get("tolerance"),
                severity=raw.get("severity") or "WARNING",
                blocks_publish=bool(raw.get("blocks_publish")),
                status=raw.get("status") or "OPEN",
                reason=raw.get("reason"),
            )
        )
    open_blocking = any(
        (raw.get("blocks_publish") and (raw.get("status") or "OPEN") == "OPEN") for raw in pairs
    )
    case.status = "OPEN" if open_blocking or any((raw.get("status") or "OPEN") == "OPEN" for raw in pairs) else "RESOLVED"
    db.flush()
    return case


def list_pairs_for_version(db: Session, costing_version_id: int) -> list[ReconciliationPair]:
    case = (
        db.query(ReconciliationCase)
        .filter(ReconciliationCase.costing_version_id == costing_version_id)
        .first()
    )
    if not case:
        return []
    return list(case.pairs)


def pair_to_dict(p: ReconciliationPair) -> dict:
    return {
        "id": p.id,
        "pair_type": p.pair_type,
        "left_label": p.left_label,
        "left_value": p.left_value,
        "right_label": p.right_label,
        "right_value": p.right_value,
        "delta": p.delta,
        "unit": p.unit,
        "tolerance": p.tolerance,
        "severity": p.severity,
        "blocks_publish": p.blocks_publish,
        "status": p.status,
        "reason": p.reason,
    }


def resolve_pair(
    db: Session,
    pair_id: int,
    *,
    actor_id: str,
    reason: str,
    resolution: str = "ACCEPTED",
) -> ReconciliationPair:
    pair = db.query(ReconciliationPair).filter(ReconciliationPair.id == pair_id).first()
    if not pair:
        raise PairNotFound(pair_id)
    if pair.status != "OPEN":
        raise PairConflict("Par já resolvido")
    if not (reason or "").strip():
        raise PairConflict("reason obrigatório", code="reason_required")
    resolution = (resolution or "ACCEPTED").upper()
    if resolution not in ("ACCEPTED", "RESOLVED"):
        raise PairConflict("resolution deve ser ACCEPTED ou RESOLVED")
    pair.status = resolution
    pair.reason = reason.strip()
    remaining = (
        db.query(ReconciliationPair)
        .filter(ReconciliationPair.case_id == pair.case_id, ReconciliationPair.status == "OPEN")
        .count()
    )
    if remaining == 0:
        pair.case.status = "RESOLVED"
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="reconciliation_pair",
        entity_id=str(pair.id),
        action="resolve",
        reason_code=resolution,
        details=reason.strip()[:500],
    )
    return pair
