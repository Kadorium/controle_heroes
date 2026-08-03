from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.identity.models import Role, User, UserSession
from app.identity.security import hash_password, verify_password

ADMIN_PERMISSIONS = [
    "users:read",
    "users:write",
    "documents:read",
    "documents:write",
    "audit:read",
    "catalog:read",
    "catalog:write",
    "orders:read",
    "orders:write",
    "orders:cancel",
    "billing:read",
    "billing:write",
    "billing:issue",
    "billing:issue_without_doc",
    "treasury:read",
    "treasury:write",
    "treasury:allocate",
    "treasury:cancel",
    "treasury:register_without_doc",
    "treasury:fx_read",
    "treasury:fx_write",
    "treasury:fx_supersede",
    "treasury:fx_without_document",
    "treasury:fx_quote_refresh",
    "reporting:read",
    "logistics:read",
    "logistics:write",
    "customs:read",
    "customs:write",
    "customs:clear",
    "customs:override",
    "inventory:read",
    "inventory:write",
    "inventory:adjust",
]

COMPRADOR_PERMISSIONS = [
    "catalog:read",
    "catalog:write",
    "orders:read",
    "orders:write",
    "orders:cancel",
    "documents:read",
    "documents:write",
    "audit:read",
    "billing:read",
    "billing:write",
    "billing:issue",
    "treasury:read",
    "treasury:write",
    "treasury:allocate",
    "treasury:fx_read",
    "treasury:fx_write",
    "logistics:read",
    "customs:read",
    "inventory:read",
]

# Papel operacional Aduana (I5-5) — sem usuário seed em epic_v2.
ADUANA_PERMISSIONS = [
    "customs:read",
    "customs:write",
    "customs:clear",
    "documents:read",
    "documents:write",
    "audit:read",
]

# Papel operacional Estoque (I5-5) — sem usuário seed em epic_v2.
ESTOQUE_PERMISSIONS = [
    "inventory:read",
    "inventory:write",
    "inventory:adjust",
    "documents:read",
    "audit:read",
]


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
    session_max_age_seconds: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, UserSession]:
    """Não faz commit — caller (UoW) comita junto com Audit."""
    raw = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=session_max_age_seconds),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    user.last_login = datetime.now(timezone.utc)
    db.add(session)
    db.flush()
    return raw, session


def get_user_by_session_token(db: Session, token: str) -> User | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == _hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .first()
    )
    if not session:
        return None
    return db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()


def revoke_session(db: Session, token: str) -> None:
    session = db.query(UserSession).filter(UserSession.token_hash == _hash_token(token)).first()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.flush()


def permissions_for(user: User) -> list[str]:
    try:
        return list(json.loads(user.role.permissions_json or "[]"))
    except json.JSONDecodeError:
        return []


def require_permission(user: User, permission: str) -> None:
    if user.role.name == "admin":
        return
    if permission not in permissions_for(user):
        raise PermissionError(permission)


def ensure_admin_role(db: Session) -> Role:
    role = db.query(Role).filter(Role.name == "admin").first()
    desired = json.dumps(ADMIN_PERMISSIONS)
    if role:
        if role.permissions_json != desired:
            role.permissions_json = desired
            db.flush()
        return role
    role = Role(
        name="admin",
        description="Administrador",
        permissions_json=desired,
    )
    db.add(role)
    db.flush()
    return role


def ensure_comprador_role(db: Session) -> Role:
    """Papel operacional — sem criar usuário em epic_v2."""
    role = db.query(Role).filter(Role.name == "comprador").first()
    desired = json.dumps(COMPRADOR_PERMISSIONS)
    if role:
        if role.permissions_json != desired:
            role.permissions_json = desired
            db.flush()
        return role
    role = Role(
        name="comprador",
        description="Comprador",
        permissions_json=desired,
    )
    db.add(role)
    db.flush()
    return role


def _ensure_named_role(
    db: Session,
    *,
    name: str,
    description: str,
    permissions: list[str],
) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    desired = json.dumps(permissions)
    if role:
        if role.permissions_json != desired:
            role.permissions_json = desired
            db.flush()
        return role
    role = Role(
        name=name,
        description=description,
        permissions_json=desired,
    )
    db.add(role)
    db.flush()
    return role


def ensure_aduana_role(db: Session) -> Role:
    """Papel operacional Aduana — sem criar usuário em epic_v2."""
    return _ensure_named_role(
        db,
        name="aduana",
        description="Aduana",
        permissions=ADUANA_PERMISSIONS,
    )


def ensure_estoque_role(db: Session) -> Role:
    """Papel operacional Estoque — sem criar usuário em epic_v2."""
    return _ensure_named_role(
        db,
        name="estoque",
        description="Estoque",
        permissions=ESTOQUE_PERMISSIONS,
    )


def ensure_admin_user(db: Session, email: str, password: str, name: str) -> User:
    role = ensure_admin_role(db)
    ensure_comprador_role(db)
    ensure_aduana_role(db)
    ensure_estoque_role(db)
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user
