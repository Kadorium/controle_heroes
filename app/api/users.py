from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_USERS_READ, PERM_USERS_WRITE
from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import ReasonCode, Role, User
from app.schemas import ReasonCodeResponse, UserCancelRequest, UserCreateRequest, UserResponse
from app.services.auth import soft_cancel_user, write_audit_log
from app.core.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.name,
        permissions=list(user.role.permissions or []),
        last_login=user.last_login,
    )


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_USERS_READ)),
) -> list[UserResponse]:
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.name).all()
    return [_user_response(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(PERM_USERS_WRITE)),
) -> UserResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Papel inválido")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=actor.id,
        entity_type="user",
        entity_id=str(user.id),
        action="create",
        new_value=f"email={user.email}, role={role.name}",
    )
    return _user_response(user)


@router.post("/{user_id}/cancel", response_model=UserResponse)
def cancel_user(
    user_id: int,
    payload: UserCancelRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(PERM_USERS_WRITE)),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="Não é possível anular o próprio usuário")

    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code, ReasonCode.is_active.is_(True)).first()
        if not rc:
            raise HTTPException(status_code=400, detail="Reason code inválido")
        reason_code_id = rc.id
        if rc.requires_comment and len(payload.reason.strip()) < 3:
            raise HTTPException(status_code=400, detail="Comentário obrigatório para este motivo")

    try:
        user = soft_cancel_user(
            db,
            user,
            actor_id=actor.id,
            reason=payload.reason,
            reason_code_id=reason_code_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _user_response(user)


@router.get("/reason-codes", response_model=list[ReasonCodeResponse])
def list_reason_codes(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ReasonCodeResponse]:
    codes = (
        db.query(ReasonCode)
        .filter(ReasonCode.is_active.is_(True))
        .order_by(ReasonCode.category, ReasonCode.code)
        .all()
    )
    return [ReasonCodeResponse.model_validate(c) for c in codes]
