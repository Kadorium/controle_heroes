"""Administração de usuários — update, guards, revoke sessions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Role, User, UserSession
from app.services.auth import write_audit_log

ADMIN_ROLE = "admin"


class UserAdminError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def count_active_admins(db: Session) -> int:
    return (
        db.query(User)
        .join(Role, Role.id == User.role_id)
        .filter(User.is_active.is_(True), Role.name == ADMIN_ROLE)
        .count()
    )


def ensure_not_last_admin(db: Session, user: User, *, action: str) -> None:
    if user.role.name != ADMIN_ROLE:
        return
    if count_active_admins(db) <= 1:
        raise UserAdminError(f"Não é possível {action} o último administrador ativo.", code="last_admin")


def revoke_user_sessions(db: Session, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .all()
    )
    for session in sessions:
        session.revoked_at = now
    return len(sessions)


def update_user(
    db: Session,
    user: User,
    *,
    actor_id: int,
    name: str | None = None,
    role: Role | None = None,
    password: str | None = None,
) -> User:
    if not user.is_active:
        raise UserAdminError("Usuário anulado não pode ser editado.", code="cancelled")

    if name is not None and name != user.name:
        old_name = user.name
        user.name = name
        write_audit_log(
            db,
            user_id=actor_id,
            entity_type="user",
            entity_id=str(user.id),
            action="update",
            field_changed="name",
            old_value=old_name,
            new_value=name,
        )

    if role is not None and role.id != user.role_id:
        if user.role.name == ADMIN_ROLE and role.name != ADMIN_ROLE:
            ensure_not_last_admin(db, user, action="alterar o papel de")
        old_role = user.role.name
        user.role_id = role.id
        db.flush()
        write_audit_log(
            db,
            user_id=actor_id,
            entity_type="user",
            entity_id=str(user.id),
            action="update",
            field_changed="role",
            old_value=old_role,
            new_value=role.name,
        )

    if password is not None:
        user.password_hash = hash_password(password)
        revoke_user_sessions(db, user.id)
        write_audit_log(
            db,
            user_id=actor_id,
            entity_type="user",
            entity_id=str(user.id),
            action="password_reset",
        )

    db.commit()
    db.refresh(user)
    return user
