from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import PERM_RUN_MIGRATION
from app.database import get_db
from app.dependencies import require_permission
from app.models import User
from app.services.demo_seed import run_demo_seed

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
def seed_demo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_RUN_MIGRATION)),
):
    return run_demo_seed(db, user_id=current_user.id)
