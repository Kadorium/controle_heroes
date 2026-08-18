"""CRUD HTTP de usuários — Foundation orquestra Identity + Audit (Identity ↛ Audit)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.identity import public as identity_public
from app.identity.errors import IdentityError
from app.identity.models import Role, User

router = APIRouter(tags=["identity"])


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class UserAdminOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    role_id: int
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime | None = None
    permissions: list[str]


class UserListOut(BaseModel):
    items: list[UserAdminOut]
    total: int
    limit: int
    offset: int


class UserCreateIn(BaseModel):
    email: EmailStr
    name: str
    password: str
    role_id: int
    is_active: bool = True


class UserPatchIn(BaseModel):
    name: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class SetPasswordIn(BaseModel):
    password: str


def _map_identity_error(exc: IdentityError) -> AppError:
    status = 400
    if exc.code == "user_not_found":
        status = 404
    elif exc.code == "email_duplicate":
        status = 409
    elif exc.code in ("last_admin_guard", "self_deactivate"):
        status = 409
    elif exc.code == "validation_error":
        status = 422
    elif exc.code == "invalid_role":
        status = 422
    return AppError(exc.message, code=exc.code, status_code=status)


def _user_out(user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.name,
        role_id=user.role_id,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        permissions=identity_public.permissions_for(user),
    )


@router.get("/roles", response_model=list[RoleOut])
def http_list_roles(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "users:read")
    return [_role_out(r) for r in identity_public.list_roles(db)]


def _role_out(role: Role) -> RoleOut:
    return RoleOut(id=role.id, name=role.name, description=role.description)


@router.get("/users", response_model=UserListOut)
def http_list_users(
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "users:read")
    items, total = identity_public.list_users_page(db, q=q, limit=limit, offset=offset)
    return UserListOut(
        items=[_user_out(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/users", response_model=UserAdminOut, status_code=201)
def http_create_user(
    payload: UserCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "users:write")
    try:
        with UnitOfWork(db) as uow:
            row = identity_public.create_user(
                uow.session,
                email=str(payload.email),
                name=payload.name,
                password=payload.password,
                role_id=payload.role_id,
                is_active=payload.is_active,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="user",
                entity_id=str(row.id),
                action="create",
                reason_code="IDENTITY_USER_CREATE",
            )
            uow.commit()
            uow.session.refresh(row)
            return _user_out(row)
    except IdentityError as e:
        raise _map_identity_error(e) from e


@router.get("/users/{user_id}", response_model=UserAdminOut)
def http_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "users:read")
    try:
        return _user_out(identity_public.get_user(db, user_id))
    except IdentityError as e:
        raise _map_identity_error(e) from e


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def http_patch_user(
    user_id: int,
    payload: UserPatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "users:write")
    dumped = payload.model_dump(exclude_unset=True)
    if not dumped:
        raise AppError("Nenhum campo para atualizar", code="validation_error", status_code=422)
    try:
        with UnitOfWork(db) as uow:
            row = identity_public.update_user(
                uow.session,
                user_id,
                actor_id=user.id,
                name=dumped.get("name"),
                role_id=dumped.get("role_id"),
                is_active=dumped.get("is_active"),
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="user",
                entity_id=str(row.id),
                action="update",
                reason_code="IDENTITY_USER_UPDATE",
                details=",".join(sorted(dumped.keys())),
            )
            uow.commit()
            uow.session.refresh(row)
            return _user_out(row)
    except IdentityError as e:
        raise _map_identity_error(e) from e


@router.post("/users/{user_id}/password", response_model=UserAdminOut)
def http_set_password(
    user_id: int,
    payload: SetPasswordIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "users:write")
    try:
        with UnitOfWork(db) as uow:
            row = identity_public.set_user_password(
                uow.session, user_id, password=payload.password
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="user",
                entity_id=str(row.id),
                action="set_password",
                reason_code="IDENTITY_USER_SET_PASSWORD",
            )
            uow.commit()
            uow.session.refresh(row)
            return _user_out(row)
    except IdentityError as e:
        raise _map_identity_error(e) from e
