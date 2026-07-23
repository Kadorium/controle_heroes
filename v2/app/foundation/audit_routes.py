from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.identity.models import User

router = APIRouter(tags=["audit"])


class AuditEventResponse(BaseModel):
    id: int
    actor_id: str | None
    entity_type: str
    entity_id: str
    action: str
    reason_code: str | None
    details: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/audit", response_model=list[AuditEventResponse])
def list_audit(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "audit:read")
    return audit_public.history_by_entity(db, entity_type, entity_id)
