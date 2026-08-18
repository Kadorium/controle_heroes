from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.identity.models import Role, User, UserSession

SEED_ROLE_NAMES = ("admin", "comprador", "aduana", "estoque")


def get_user(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id)
        .first()
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_role(db: Session, role_id: int) -> Role | None:
    return db.get(Role, role_id)


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).first()


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).filter(Role.name.in_(SEED_ROLE_NAMES)).order_by(Role.name).all()


def list_users(db: Session, *, q: str | None, limit: int, offset: int) -> list[User]:
    query = db.query(User).options(joinedload(User.role))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((User.email.ilike(like)) | (User.name.ilike(like)))
    return query.order_by(User.name).offset(offset).limit(limit).all()


def count_users(db: Session, *, q: str | None) -> int:
    query = db.query(func.count(User.id))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((User.email.ilike(like)) | (User.name.ilike(like)))
    return int(query.scalar() or 0)


def count_active_admins(db: Session) -> int:
    return int(
        db.query(func.count(User.id))
        .join(Role, User.role_id == Role.id)
        .filter(Role.name == "admin", User.is_active.is_(True))
        .scalar()
        or 0
    )


def add_user(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    return user


def revoke_sessions_for_user(db: Session, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    q = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
    )
    n = 0
    for session in q.all():
        session.revoked_at = now
        n += 1
    db.flush()
    return n
