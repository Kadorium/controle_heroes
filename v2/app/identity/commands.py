from sqlalchemy.orm import Session

from app.identity import repository as repo
from app.identity.errors import (
    EmailDuplicate,
    IdentityValidationError,
    InvalidRole,
    LastAdminGuard,
    SelfDeactivateForbidden,
    UserNotFound,
)
from app.identity.models import User
from app.identity.security import hash_password

SEED_ROLE_NAMES = repo.SEED_ROLE_NAMES
MIN_PASSWORD_LEN = 8


def _normalize_email(email: str) -> str:
    s = (email or "").strip().lower()
    if not s or "@" not in s:
        raise IdentityValidationError("E-mail inválido")
    return s


def _normalize_name(name: str) -> str:
    s = (name or "").strip()
    if not s:
        raise IdentityValidationError("Nome é obrigatório")
    return s


def _require_password(password: str) -> str:
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise IdentityValidationError(f"Senha deve ter pelo menos {MIN_PASSWORD_LEN} caracteres")
    if len(password) > 128:
        raise IdentityValidationError("Senha excede 128 caracteres")
    return password


def _role_or_raise(db: Session, role_id: int):
    role = repo.get_role(db, role_id)
    if not role or role.name not in SEED_ROLE_NAMES:
        raise InvalidRole(role_id)
    return role


def _guard_last_admin(db: Session, user: User, *, next_role_name: str | None, next_active: bool | None) -> None:
    if user.role.name != "admin":
        return
    becoming_non_admin = next_role_name is not None and next_role_name != "admin"
    becoming_inactive = next_active is False
    if not becoming_non_admin and not becoming_inactive:
        return
    if repo.count_active_admins(db) <= 1:
        raise LastAdminGuard()


def create_user(
    db: Session,
    *,
    email: str,
    name: str,
    password: str,
    role_id: int,
    is_active: bool = True,
) -> User:
    email_n = _normalize_email(email)
    name_n = _normalize_name(name)
    _require_password(password)
    role = _role_or_raise(db, role_id)
    if repo.get_user_by_email(db, email_n):
        raise EmailDuplicate(email_n)
    return repo.add_user(
        db,
        User(
            email=email_n,
            name=name_n,
            password_hash=hash_password(password),
            role_id=role.id,
            is_active=is_active,
        ),
    )


def update_user(
    db: Session,
    user_id: int,
    *,
    actor_id: int,
    name: str | None = None,
    role_id: int | None = None,
    is_active: bool | None = None,
) -> User:
    user = repo.get_user(db, user_id)
    if not user:
        raise UserNotFound(user_id)
    next_role_name = None
    if role_id is not None:
        role = _role_or_raise(db, role_id)
        next_role_name = role.name
    _guard_last_admin(db, user, next_role_name=next_role_name, next_active=is_active)
    if is_active is False:
        if actor_id == user.id:
            raise SelfDeactivateForbidden()
        user.is_active = False
        repo.revoke_sessions_for_user(db, user.id)
    elif is_active is True:
        user.is_active = True
    if name is not None:
        user.name = _normalize_name(name)
    if role_id is not None:
        user.role_id = role_id
    db.flush()
    db.refresh(user)
    return user


def set_user_password(db: Session, user_id: int, *, password: str) -> User:
    user = repo.get_user(db, user_id)
    if not user:
        raise UserNotFound(user_id)
    _require_password(password)
    user.password_hash = hash_password(password)
    repo.revoke_sessions_for_user(db, user.id)
    db.flush()
    return user
