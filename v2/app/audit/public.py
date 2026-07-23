from __future__ import annotations

from sqlalchemy.orm import Session

from app.audit.models import AuditLog


def record_event(
    db: Session,
    *,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    action: str,
    reason_code: str | None = None,
    details: str | None = None,
) -> AuditLog:
    """Append-only. Não faz commit — mesma UoW da ação crítica."""
    row = AuditLog(
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        reason_code=reason_code,
        details=details,
    )
    db.add(row)
    db.flush()
    return row


def history_by_entity(db: Session, entity_type: str, entity_id: str, *, limit: int = 100) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
