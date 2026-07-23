"""Rotas HTTP de autenticação orquestradas pela Foundation (Identity + Audit na mesma UoW)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.foundation.database import get_db
from app.foundation.deps import UserResponse, get_current_user, user_response
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
from app.identity import public as identity_public
from app.identity.models import User

router = APIRouter(tags=["identity"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    with UnitOfWork(db) as uow:
        user = identity_public.authenticate_user(uow.session, payload.email, payload.password)
        if not user:
            raise AppError("Credenciais inválidas", code="invalid_credentials", status_code=401)
        raw, _session = identity_public.create_session(
            uow.session,
            user,
            session_max_age_seconds=settings.session_max_age_seconds,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        audit_public.record_event(
            uow.session,
            actor_id=str(user.id),
            entity_type="user",
            entity_id=str(user.id),
            action="login",
            reason_code="AUTH_LOGIN",
        )
        uow.commit()
        uow.session.refresh(user)
        body = user_response(user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw,
        httponly=True,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
    )
    return body


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    with UnitOfWork(db) as uow:
        user = identity_public.get_user_by_session_token(uow.session, token or "")
        if token:
            identity_public.revoke_session(uow.session, token)
        if user:
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="user",
                entity_id=str(user.id),
                action="logout",
                reason_code="AUTH_LOGOUT",
            )
        uow.commit()
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user_response(user)
