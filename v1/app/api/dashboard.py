from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import PERM_IMPORTATION_READ
from app.database import get_db
from app.dependencies import require_permission
from app.models import User
from app.schemas_dashboard import DashboardImportationsResponse, DashboardSummaryResponse
from app.services.dashboard import get_dashboard_importations, get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return get_dashboard_summary(db)


@router.get("/importations", response_model=DashboardImportationsResponse)
def dashboard_importations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    limit: int = Query(default=100, ge=1, le=500),
):
    return get_dashboard_importations(db, list_limit=limit)
