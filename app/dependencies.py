from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.permissions import role_has_permission
from app.database import get_db
from app.models import User
from app.services.auth import get_user_by_session_token


def get_session_token(
    epic_session: str | None = Cookie(default=None, alias=None),
) -> str | None:
    settings = get_settings()
    # Cookie alias resolved dynamically in route dependency wrapper below
    return epic_session


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    user = get_user_by_session_token(db, token or "")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    return user


def require_permission(permission: str):
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        perms = current_user.role.permissions or []
        if not role_has_permission(perms, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão negada: {permission}",
            )
        return current_user

    return _checker
