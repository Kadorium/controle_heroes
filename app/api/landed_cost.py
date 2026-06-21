from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_LANDED_COST_READ, PERM_LANDED_COST_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import LandedCostVersion, ReasonCode, User
from app.schemas_phase789 import LandedCostCreate, LandedCostVersionResponse
from app.services.landed_cost import LandedCostError, create_landed_cost_version

router = APIRouter(prefix="/landed-cost", tags=["landed-cost"])


def _version_response(db: Session, version: LandedCostVersion) -> LandedCostVersionResponse:
    from app.models import LandedCostComponent, LandedCostSkuAllocation

    components = (
        db.query(LandedCostComponent).filter(LandedCostComponent.landed_cost_version_id == version.id).all()
    )
    allocations = (
        db.query(LandedCostSkuAllocation).filter(LandedCostSkuAllocation.landed_cost_version_id == version.id).all()
    )
    return LandedCostVersionResponse(
        id=version.id,
        importation_id=version.importation_id,
        version_number=version.version_number,
        version_type=version.version_type,
        is_current_version=version.is_current_version,
        previous_version_id=version.previous_version_id,
        total_cost=version.total_cost,
        trigger_event=version.trigger_event,
        created_at=version.created_at,
        components=components,
        allocations=allocations,
    )


@router.get("/importations/{importation_id}/versions", response_model=list[LandedCostVersionResponse])
def list_versions(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_LANDED_COST_READ)),
):
    versions = (
        db.query(LandedCostVersion)
        .filter(LandedCostVersion.importation_id == importation_id)
        .order_by(LandedCostVersion.version_number)
        .all()
    )
    return [_version_response(db, v) for v in versions]


@router.post("/versions", response_model=LandedCostVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    payload: LandedCostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_LANDED_COST_WRITE)),
):
    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
        reason_code_id = rc.id if rc else None
    try:
        version = create_landed_cost_version(
            db,
            importation_id=payload.importation_id,
            version_type=payload.version_type,
            allocation_method=payload.allocation_method,
            user_id=current_user.id,
            trigger_event=payload.trigger_event,
            trigger_notes=payload.trigger_notes,
            manual_allocations=payload.manual_allocations,
            manual_reason_code_id=reason_code_id,
            manual_justification=payload.justification,
        )
    except LandedCostError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _version_response(db, version)
