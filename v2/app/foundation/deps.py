from __future__ import annotations

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.foundation.database import get_db
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.identity import public as identity_public
from app.identity.models import User


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    permissions: list[str]


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.name,
        permissions=identity_public.permissions_for(user),
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    user = identity_public.get_user_by_session_token(db, token or "")
    if not user:
        raise AppError("Não autenticado", code="unauthorized", status_code=401)
    return user


def enforce_permission(user: User, permission: str) -> None:
    try:
        identity_public.require_permission(user, permission)
    except PermissionError as exc:
        raise AppError("Permissão insuficiente", code="forbidden", status_code=403) from exc
