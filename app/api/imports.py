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
from app.schemas_import import (
    CancelledSummaryResponse,
    ProductResponse,
    PurgeCancelledRequest,
    PurgeCancelledResponse,
    ResolveStagingSkuRequest,
)
from app.services.cleanup_cancelled import build_cancelled_summary, purge_cancelled_data
from app.services.heroes_import import approve_staging_row, import_heroes_csv
from app.services.heroes_order_format_v1 import export_normalized_xlsx, export_normalized_zip, preview_to_canonical
from app.services.heroes_workbook_paths import heroes_workbook_search_labels, resolve_heroes_workbook_path
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_guard import AttachedRawFileError, assert_raw_file_not_attached_elsewhere
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
        assert_raw_file_not_attached_elsewhere(db, raw.id)
    except AttachedRawFileError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
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

    from app.services.importation_lifecycle import heroes_run_targets_active_importation

    committed = (
        run.status == HeroesImportRunStatus.COMMITTED.value
        and heroes_run_targets_active_importation(db, run)
    )
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
        review_required=run.review_required or run.status == "REVIEW_REQUIRED",
        sku_review_pending=bool(preview_data.get("sku_review_pending")),
        sku_review_open_count=int(preview_data.get("sku_review_open_count") or 0),
        sku_review_line_count=int(preview_data.get("sku_review_line_count") or 0),
        sku_review_groups=preview_data.get("sku_review_groups") or [],
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
    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == payload.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Import run não encontrado")
    if run.raw_file_id and not run.importation_id:
        try:
            assert_raw_file_not_attached_elsewhere(db, run.raw_file_id)
        except AttachedRawFileError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
    try:
        imp = commit_heroes_import_run(
            db,
            payload.run_id,
            user_id=current_user.id,
            category_overrides=payload.category_overrides,
            confirmed_order_number=payload.confirmed_order_number,
            confirm_sheet_match=payload.confirm_sheet_match,
            confirm_import=payload.confirm_import,
            confirm_financial_review=payload.confirm_financial_review,
            versato_override=payload.versato_override,
            acconto_overrides=payload.acconto_overrides,
            opening_exchange_rate=payload.opening_exchange_rate,
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


@router.get("/cancelled-summary", response_model=CancelledSummaryResponse)
def get_cancelled_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTS_READ)),
):
    data = build_cancelled_summary(db)
    return CancelledSummaryResponse(
        purge_allowed=data["purge_allowed"],
        purge_block_reason=data["purge_block_reason"],
        purge_env_var=data["purge_env_var"],
        importations=data["importations"],
        products=data["products"],
        suppliers=data["suppliers"],
        counts=data["counts"],
    )


@router.post("/purge-cancelled", response_model=PurgeCancelledResponse)
def purge_cancelled(
    payload: PurgeCancelledRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_RUN_MIGRATION)),
):
    has_targets = any(
        [
            payload.importation_ids,
            payload.product_ids,
            payload.supplier_ids,
            payload.purge_all_cancelled_importations,
            payload.purge_all_cancelled_products,
            payload.purge_all_cancelled_suppliers,
            payload.purge_orphan_artifacts,
        ]
    )
    if not has_targets:
        raise HTTPException(
            status_code=400,
            detail="Selecione ao menos um registro ou artefato para excluir",
        )
    try:
        result = purge_cancelled_data(
            db,
            importation_ids=payload.importation_ids,
            product_ids=payload.product_ids,
            supplier_ids=payload.supplier_ids,
            purge_all_cancelled_importations=payload.purge_all_cancelled_importations,
            purge_all_cancelled_products=payload.purge_all_cancelled_products,
            purge_all_cancelled_suppliers=payload.purge_all_cancelled_suppliers,
            purge_orphan_artifacts=payload.purge_orphan_artifacts,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return PurgeCancelledResponse(**result)


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


@router.patch("/staging/{staging_id}/resolve-sku", response_model=StagingRowResponse)
def resolve_staging_sku_endpoint(
    staging_id: int,
    payload: ResolveStagingSkuRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_APPROVE)),
):
    from app.services.heroes_xlsx_staging import resolve_staging_sku
    from app.services.auth import write_audit_log

    try:
        staging = resolve_staging_sku(
            db,
            staging_id,
            product_id=payload.product_id,
            user_id=current_user.id,
            save_aliases=payload.save_aliases,
            extra_aliases=payload.extra_aliases or None,
        )
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="staging_import_row",
            entity_id=str(staging.id),
            action="resolve_sku",
            new_value=str(payload.product_id),
        )
        db.commit()
        db.refresh(staging)
        return staging
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/staging/{staging_id}/create-draft", response_model=ProductResponse)
def create_draft_from_staging_endpoint(
    staging_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTS_APPROVE)),
):
    from app.services.auth import write_audit_log
    from app.services.product_draft import create_draft_from_staging

    try:
        product = create_draft_from_staging(db, staging_id, user_id=current_user.id)
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="staging_import_row",
            entity_id=str(staging_id),
            action="create_draft_product",
            new_value=str(product.id),
        )
        db.commit()
        db.refresh(product)
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
