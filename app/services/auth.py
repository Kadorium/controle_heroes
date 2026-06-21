from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.security import hash_password, verify_password
from app.models import AuditLog, TechnicalLog, User, UserSession


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(
    db: Session,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, UserSession]:
    s = settings or get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=s.session_max_age_seconds)
    session = UserSession(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    user.last_login = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    return raw_token, session


def get_user_by_session_token(db: Session, token: str) -> User | None:
    if not token:
        return None
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .first()
    )
    if not session:
        return None
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    return user


def revoke_session(db: Session, token: str) -> None:
    token_hash = _hash_token(token)
    session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    if session:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()


def write_audit_log(
    db: Session,
    *,
    user_id: int | None,
    entity_type: str,
    entity_id: str,
    action: str,
    field_changed: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason_code_id: int | None = None,
    justification: str | None = None,
    attachment_id: str | None = None,
    impact_estimate: str | None = None,
    ip_or_machine_info: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        reason_code_id=reason_code_id,
        justification=justification,
        attachment_id=attachment_id,
        impact_estimate=impact_estimate,
        ip_or_machine_info=ip_or_machine_info,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def write_technical_log(
    db: Session,
    *,
    category: str,
    message: str,
    level: str = "ERROR",
    details: dict | None = None,
    user_id: int | None = None,
) -> TechnicalLog:
    entry = TechnicalLog(
        category=category,
        message=message,
        level=level,
        details=details,
        user_id=user_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def log_login_failure(db: Session, email: str, ip: str | None = None) -> TechnicalLog:
    return write_technical_log(
        db,
        category="login",
        message="Falha de login",
        details={"email": email, "ip": ip},
    )


def soft_cancel_user(
    db: Session,
    user: User,
    *,
    actor_id: int,
    reason: str,
    reason_code_id: int | None = None,
) -> User:
    if not reason.strip():
        raise ValueError("Motivo obrigatório para anulação")

    old_active = str(user.is_active)
    user.is_active = False
    user.cancelled_at = datetime.now(timezone.utc)
    user.cancelled_by_id = actor_id
    user.cancellation_reason = reason

    write_audit_log(
        db,
        user_id=actor_id,
        entity_type="user",
        entity_id=str(user.id),
        action="cancel",
        field_changed="is_active",
        old_value=old_active,
        new_value="False",
        reason_code_id=reason_code_id,
        justification=reason,
    )
    db.commit()
    db.refresh(user)
    return user
