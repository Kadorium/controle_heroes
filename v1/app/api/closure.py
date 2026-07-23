from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_CLOSE_IMPORTATION, PERM_IMPORTATION_READ, PERM_REOPEN_IMPORTATION
from app.database import get_db
from app.dependencies import require_permission
from app.models import ImportationClosure, ImportationOrder, ReasonCode, User
from app.schemas_phase101112 import (
    CloseChecklistItem,
    CloseImportationRequest,
    ClosureResponse,
    ReopenImportationRequest,
    TimelineEvent,
)
from app.services.closure import ClosureError, close_importation, get_close_checklist, get_timeline, reopen_importation

router = APIRouter(prefix="/closure", tags=["closure"])


@router.get("/importations/{importation_id}/checklist", response_model=list[CloseChecklistItem])
def close_checklist(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    try:
        return get_close_checklist(db, importation_id)
    except ClosureError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/importations/{importation_id}/close", response_model=ClosureResponse, status_code=status.HTTP_201_CREATED)
def close_importation_endpoint(
    importation_id: int,
    payload: CloseImportationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CLOSE_IMPORTATION)),
):
    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
        reason_code_id = rc.id if rc else None
    try:
        return close_importation(
            db,
            importation_id,
            user_id=current_user.id,
            landed_cost_version_id=payload.landed_cost_version_id,
            approved_reconciliation_ids=payload.approved_reconciliation_ids,
            reason_code_id=reason_code_id,
            justification=payload.justification,
        )
    except ClosureError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/importations/{importation_id}/reopen", response_model=dict)
def reopen_importation_endpoint(
    importation_id: int,
    payload: ReopenImportationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_REOPEN_IMPORTATION)),
):
    rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
    if not rc:
        raise HTTPException(status_code=400, detail="Reason code inválido")
    try:
        imp = reopen_importation(
            db,
            importation_id,
            user_id=current_user.id,
            reason_code_id=rc.id,
            justification=payload.justification,
        )
        return {"id": imp.id, "current_status": imp.current_status, "reopened_at": imp.reopened_at}
    except ClosureError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/importations/{importation_id}/history", response_model=list[ClosureResponse])
def closure_history(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return (
        db.query(ImportationClosure)
        .filter(ImportationClosure.importation_id == importation_id)
        .order_by(ImportationClosure.closure_version)
        .all()
    )


@router.get("/importations/{importation_id}/timeline", response_model=list[TimelineEvent])
def timeline(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return get_timeline(db, importation_id)
