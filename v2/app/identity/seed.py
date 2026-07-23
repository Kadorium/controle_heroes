from sqlalchemy.orm import Session

from app.identity import public as identity_public


def ensure_seed(db: Session, *, email: str, password: str, name: str) -> None:
    identity_public.ensure_admin_user(db, email, password, name)
