from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginRequest, MessageResponse, UserResponse
from app.services.auth import (
    authenticate_user,
    create_session,
    log_login_failure,
    revoke_session,
    write_audit_log,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.name,
        permissions=list(user.role.permissions or []),
        last_login=user.last_login,
        is_active=user.is_active,
    )


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        log_login_failure(db, payload.email, request.client.host if request.client else None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token, _session = create_session(
        db,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    write_audit_log(
        db,
        user_id=user.id,
        entity_type="user",
        entity_id=str(user.id),
        action="login",
        ip_or_machine_info=request.client.host if request.client else None,
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        secure=settings.app_env.lower() == "production",
    )
    return _user_response(user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    token = request.cookies.get(settings.session_cookie_name, "")
    revoke_session(db, token)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="user",
        entity_id=str(current_user.id),
        action="logout",
    )
    response.delete_cookie(settings.session_cookie_name)
    return MessageResponse(message="Logout realizado")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)
