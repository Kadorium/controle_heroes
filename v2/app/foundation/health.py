from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.foundation.database import get_db
from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION, get_applied_alembic_revision
from app.foundation.settings import get_settings

router = APIRouter(tags=["health"])


def _logical_database_name(database_url: str) -> str:
    """Path of the DB URL only — never userinfo/password."""
    try:
        path = urlparse(database_url).path or ""
        name = path.lstrip("/").split("?")[0]
        return name or "unknown"
    except Exception:
        return "unknown"


def _runtime_lane(app_env: str, db_name: str) -> str:
    env = (app_env or "").lower()
    if env in {"test", "testing"} or db_name.endswith("_test"):
        return "Teste"
    return "Operação"


class HealthResponse(BaseModel):
    status: str
    app: str
    database: str
    timestamp: datetime
    app_env: str
    runtime_lane: str
    logical_database: str
    alembic_head: str | None = None
    alembic_expected: str = EXPECTED_ALEMBIC_REVISION
    schema_ok: bool = True


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    logical = _logical_database_name(settings.database_url)
    applied = get_applied_alembic_revision(db) if db_status == "ok" else None
    schema_ok = applied == EXPECTED_ALEMBIC_REVISION
    status = "ok" if db_status == "ok" and schema_ok else "degraded"
    if db_status != "ok":
        status = "degraded"
    return HealthResponse(
        status=status,
        app=settings.app_name,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
        app_env=settings.app_env,
        runtime_lane=_runtime_lane(settings.app_env, logical),
        logical_database=logical,
        alembic_head=applied,
        alembic_expected=EXPECTED_ALEMBIC_REVISION,
        schema_ok=schema_ok,
    )
