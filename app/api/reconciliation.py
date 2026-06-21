from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import ImportationOrder, ReasonCode, Reconciliation, User
from app.schemas_phase101112 import ReconciliationApprove, ReconciliationResponse
from app.services.reconciliation import ReconciliationError, approve_reconciliation, run_reconciliations

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.get("/importations/{importation_id}", response_model=list[ReconciliationResponse])
def list_reconciliations(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return (
        db.query(Reconciliation)
        .filter(Reconciliation.importation_id == importation_id)
        .order_by(Reconciliation.pair_type)
        .all()
    )


@router.post("/importations/{importation_id}/run", response_model=list[ReconciliationResponse])
def run_importation_reconciliations(
    importation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    try:
        return run_reconciliations(db, importation_id)
    except ReconciliationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{reconciliation_id}/approve", response_model=ReconciliationResponse)
def approve_reconciliation_endpoint(
    reconciliation_id: int,
    payload: ReconciliationApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    rec = db.query(Reconciliation).filter(Reconciliation.id == reconciliation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Conciliação não encontrada")
    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
        reason_code_id = rc.id if rc else None
    try:
        return approve_reconciliation(
            db,
            rec,
            user_id=current_user.id,
            reason_code_id=reason_code_id,
            justification=payload.justification,
        )
    except ReconciliationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
