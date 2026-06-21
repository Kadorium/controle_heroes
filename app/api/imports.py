import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import HeroesImportRunStatus, ReviewQueueStatus
from app.core.permissions import PERM_IMPORTS_APPROVE, PERM_IMPORTS_READ, PERM_IMPORTS_WRITE, PERM_RUN_MIGRATION
from app.database import get_db
from app.dependencies import require_permission
from app.models import HeroesImportMapping, HeroesImportRun, ImportationOrder, ReviewQueueItem, StagingImportRow, User
from app.schemas_docs import (
    HeroesMappingCreate,
    HeroesMappingResponse,
    HeroesWorkbookLocateResponse,
    HeroesWorkbookProfileResponse,
    HeroesXlsxCommitRequest,
    HeroesXlsxCommitResponse,
    HeroesXlsxExportRequest,
    HeroesXlsxPreviewRequest,
    HeroesXlsxPreviewResponse,
    HeroesXlsxUploadResponse,
    RawImportFileResponse,
    ReviewQueueResponse,
    StagingRowResponse,
)
from app.services.heroes_import import approve_staging_row, import_heroes_csv
from app.services.heroes_order_format_v1 import export_normalized_xlsx, export_normalized_zip, preview_to_canonical
from app.services.heroes_workbook_paths import heroes_workbook_search_labels, resolve_heroes_workbook_path
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_import import load_local_workbook, preview_xlsx_sheet, profile_local_workbook, upload_xlsx_file
from app.services.reset_operational_data import reset_operational_test_data

router = APIRouter(prefix="/imports", tags=["imports"])


def _read_raw_file_content(storage_path: str) -> bytes:
    settings = get_settings()
    full = settings.imports_path / storage_path
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo raw não encontrado: {storage_path}")
    return full.read_bytes()


@router.get("/mappings/default")
def default_mapping(_: User = Depends(require_permission(PERM_IMPORTS_READ))):
    from app.core.enums import DEFAULT_HEROES_COLUMN_MAPPING

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
async def upload_heroes_csv(
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


@router.get("/heroes/xlsx/locate", response_model=HeroesWorkbookLocateResponse)
def locate_heroes_workbook(_: User = Depends(require_permission(PERM_IMPORTS_READ))):
    path = resolve_heroes_workbook_path()
    return HeroesWorkbookLocateResponse(
        found=path is not None,
        resolved_path=str(path) if path else None,
        search_paths=heroes_workbook_search_labels(),
    )


@router.post("/heroes/xlsx/profile", response_model=HeroesWorkbookProfileResponse)
def profile_heroes_workbook(_: User = Depends(require_permission(PERM_IMPORTS_READ))):
    try:
        report = profile_local_workbook()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return HeroesWorkbookProfileResponse(**report)


@router.post("/heroes/xlsx/load-local", response_model=HeroesXlsxUploadResponse, status_code=status.HTTP_201_CREATED)
def load_heroes_workbook_local(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_WRITE)),
):
    try:
        result = load_local_workbook(db, user_id=current_user.id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    profile = result.get("workbook_profile")
    return HeroesXlsxUploadResponse(
        raw_file_id=result["raw_file_id"],
        file_checksum=result["file_checksum"],
        sheets=result["sheets"],
        workbook_profile=HeroesWorkbookProfileResponse(**profile) if profile else None,
        source_path=result.get("source_path"),
    )


@router.post("/heroes/xlsx/upload", response_model=HeroesXlsxUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_heroes_xlsx(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_WRITE)),
):
    content = await file.read()
    name = (file.filename or "").lower()
    if not (name.endswith(".xlsx") or name.endswith(".xlsm")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .xlsx são suportados neste endpoint")
    try:
        result = upload_xlsx_file(db, file, content, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    profile = result.get("workbook_profile")
    return HeroesXlsxUploadResponse(
        raw_file_id=result["raw_file_id"],
        file_checksum=result["file_checksum"],
        sheets=result["sheets"],
        workbook_profile=HeroesWorkbookProfileResponse(**profile) if profile else None,
        source_path=result.get("source_path"),
    )


@router.post("/heroes/xlsx/preview", response_model=HeroesXlsxPreviewResponse)
async def preview_heroes_xlsx(
    payload: HeroesXlsxPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_READ)),
):
    from app.models import RawImportFile

    raw = db.query(RawImportFile).filter(RawImportFile.id == payload.raw_file_id).first()
    if not raw:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    try:
        content = _read_raw_file_content(raw.storage_path)
        run = preview_xlsx_sheet(
            db,
            raw_file_id=raw.id,
            sheet_name=payload.sheet_name,
            content=content,
            filename=raw.original_filename,
            user_id=current_user.id,
            confirmed_order_number=payload.confirmed_order_number,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    committed = run.status == HeroesImportRunStatus.COMMITTED.value
    preview_data = run.preview_json or {}
    canonical = preview_to_canonical(preview_data, source_file=raw.original_filename)
    return HeroesXlsxPreviewResponse(
        run_id=run.id,
        status=run.status,
        sheet_name=run.sheet_name,
        sheet_type=run.sheet_type,
        order_number=run.order_number,
        order_number_from_sheet_name=preview_data.get("order_number_from_sheet_name"),
        order_number_from_content=preview_data.get("order_number_from_content"),
        order_number_divergence=bool(preview_data.get("order_number_divergence")),
        preview=preview_data,
        canonical=canonical,
        warnings=run.warnings_json,
        errors=run.errors_json,
        already_committed=committed,
        importation_id=run.importation_id,
    )


@router.post("/heroes/xlsx/commit", response_model=HeroesXlsxCommitResponse)
def commit_heroes_xlsx(
    payload: HeroesXlsxCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_APPROVE)),
):
    try:
        imp = commit_heroes_import_run(
            db,
            payload.run_id,
            user_id=current_user.id,
            category_overrides=payload.category_overrides,
            confirmed_order_number=payload.confirmed_order_number,
            confirm_sheet_match=payload.confirm_sheet_match,
            confirm_import=payload.confirm_import,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == payload.run_id).first()
    return HeroesXlsxCommitResponse(importation_id=imp.id, po_number=imp.po_number, run_id=run.id if run else payload.run_id)


@router.post("/heroes/xlsx/export")
def export_heroes_normalized(
    payload: HeroesXlsxExportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTS_READ)),
):
    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == payload.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Import run não encontrado")
    preview = run.preview_json or {}
    canonical = preview_to_canonical(preview, source_file=run.original_filename)
    if payload.format == "zip":
        data = export_normalized_zip(canonical)
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="heroes-order-v1-preview.zip"'},
        )
    data = export_normalized_xlsx(canonical)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="heroes-order-v1-preview.xlsx"'},
    )


@router.post("/reset-operational")
def reset_operational(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_RUN_MIGRATION)),
):
    try:
        return reset_operational_test_data(db)
    except RuntimeError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


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
