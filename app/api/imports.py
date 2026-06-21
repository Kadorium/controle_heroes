import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.enums import DEFAULT_HEROES_COLUMN_MAPPING, ReviewQueueStatus
from app.core.permissions import PERM_IMPORTS_APPROVE, PERM_IMPORTS_READ, PERM_IMPORTS_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import HeroesImportMapping, ReviewQueueItem, StagingImportRow, User
from app.schemas_docs import (
    HeroesMappingCreate,
    HeroesMappingResponse,
    RawImportFileResponse,
    ReviewQueueResponse,
    StagingRowResponse,
)
from app.services.heroes_import import approve_staging_row, import_heroes_csv

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/mappings/default")
def default_mapping(_: User = Depends(require_permission(PERM_IMPORTS_READ))):
    return DEFAULT_HEROES_COLUMN_MAPPING


@router.post("/mappings", response_model=HeroesMappingResponse, status_code=status.HTTP_201_CREATED)
def create_mapping(
    payload: HeroesMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_WRITE)),
):
    if payload.is_default:
        db.query(HeroesImportMapping).update({HeroesImportMapping.is_default: False})
    mapping = HeroesImportMapping(
        name=payload.name,
        column_mapping=payload.column_mapping,
        is_default=payload.is_default,
        created_by_id=current_user.id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/mappings", response_model=list[HeroesMappingResponse])
def list_mappings(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTS_READ)),
):
    return db.query(HeroesImportMapping).order_by(HeroesImportMapping.name).all()


@router.post("/heroes/upload", response_model=RawImportFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_heroes(
    file: UploadFile = File(...),
    column_mapping_json: str | None = Form(None),
    mapping_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_WRITE)),
):
    content = await file.read()
    mapping = json.loads(column_mapping_json) if column_mapping_json else None
    try:
        raw = import_heroes_csv(
            db,
            file,
            content,
            user_id=current_user.id,
            column_mapping=mapping,
            mapping_id=mapping_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return raw


@router.get("/raw", response_model=list[RawImportFileResponse])
def list_raw_files(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTS_READ)),
):
    from app.models import RawImportFile

    return db.query(RawImportFile).order_by(RawImportFile.created_at.desc()).all()


@router.get("/staging", response_model=list[StagingRowResponse])
def list_staging(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTS_READ)),
    raw_file_id: int | None = None,
    status: str | None = None,
):
    q = db.query(StagingImportRow)
    if raw_file_id is not None:
        q = q.filter(StagingImportRow.raw_file_id == raw_file_id)
    if status:
        q = q.filter(StagingImportRow.status == status)
    return q.order_by(StagingImportRow.row_number).all()


@router.get("/review-queue", response_model=list[ReviewQueueResponse])
def list_review_queue(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTS_READ)),
    status: str | None = ReviewQueueStatus.OPEN.value,
):
    q = db.query(ReviewQueueItem)
    if status:
        q = q.filter(ReviewQueueItem.status == status)
    items = q.order_by(ReviewQueueItem.priority.desc(), ReviewQueueItem.created_at).all()
    result = []
    for item in items:
        staging = db.query(StagingImportRow).filter(StagingImportRow.id == item.staging_row_id).first()
        result.append(
            ReviewQueueResponse(
                id=item.id,
                staging_row_id=item.staging_row_id,
                status=item.status,
                reason=item.reason,
                priority=item.priority,
                created_at=item.created_at,
                staging_row=StagingRowResponse.model_validate(staging) if staging else None,
            )
        )
    return result


@router.post("/staging/{staging_id}/approve", response_model=StagingRowResponse)
def approve_staging(
    staging_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_APPROVE)),
):
    try:
        return approve_staging_row(db, staging_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
