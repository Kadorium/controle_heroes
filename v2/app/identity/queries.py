from sqlalchemy.orm import Session

from app.identity import repository as repo
from app.identity.errors import UserNotFound
from app.identity.models import Role, User


def get_user(db: Session, user_id: int) -> User:
    row = repo.get_user(db, user_id)
    if not row:
        raise UserNotFound(user_id)
    return row


def list_users_page(
    db: Session,
    *,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    is_active: bool | None = None,
    role: str | None = None,
) -> tuple[list[User], int]:
    return (
        repo.list_users(db, q=q, limit=limit, offset=offset, is_active=is_active, role=role),
        repo.count_users(db, q=q, is_active=is_active, role=role),
    )


def list_roles(db: Session) -> list[Role]:
    return repo.list_roles(db)
