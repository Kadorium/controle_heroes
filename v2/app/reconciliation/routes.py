"""HTTP Reconciliation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.reconciliation import public as recon_public
from app.reconciliation.errors import ReconciliationError

router = APIRouter(tags=["reconciliation"])


def _map(exc: ReconciliationError) -> AppError:
    code = getattr(exc, "code", "reconciliation_error")
    status = 400
    if code == "not_found":
        status = 404
    elif code in ("conflict",):
        status = 409
    elif code == "reason_required":
        status = 422
    return AppError(exc.message, code=code, status_code=status)


class ResolveBody(BaseModel):
    reason: str
    resolution: str = "ACCEPTED"


@router.get("/reconciliation/versions/{version_id}")
def get_pairs(version_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_permission(user, "reconciliation:read")
    pairs = recon_public.list_pairs_for_version(db, version_id)
    return [recon_public.pair_to_dict(p) for p in pairs]


@router.post("/reconciliation/pairs/{pair_id}/resolve")
def resolve(
    pair_id: int,
    body: ResolveBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_permission(user, "reconciliation:resolve")
    try:
        with UnitOfWork(db) as uow:
            pair = recon_public.resolve_pair(
                uow.session,
                pair_id,
                actor_id=str(user.id),
                reason=body.reason,
                resolution=body.resolution,
            )
            uow.commit()
            return recon_public.pair_to_dict(pair)
    except ReconciliationError as exc:
        raise _map(exc) from exc
