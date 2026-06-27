from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.permissions import PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import Product, User
from app.schemas_import import (
    CancelRequest,
    ProductBulkActionResponse,
    ProductBulkIdsRequest,
    ProductBulkArchiveRequest,
    ProductBulkCancelRequest,
    ProductBulkStatusRequest,
    ProductCatalogResponse,
    ProductCatalogRow,
    ProductCostHistoryResponse,
    ProductCostHistoryRow,
    ProductCreate,
    ProductDetailResponse,
    ProductImportCommitRequest,
    ProductImportPreviewResponse,
    ProductImportPreviewRow,
    ProductOrdersResponse,
    ProductOrderRow,
    ProductReadinessResponse,
    ProductResponse,
    ProductUpdate,
    ProductAuditRow,
)
from app.services.auth import write_audit_log
from app.services.product_catalog import (
    archive_product,
    bulk_archive_products,
    bulk_cancel_products,
    bulk_restore_products,
    bulk_set_lifecycle_status,
    cancel_product_record,
    compute_product_readiness,
    get_product_detail,
    list_product_audit,
    list_product_catalog,
    list_product_cost_history,
    list_product_groups,
    list_product_orders,
    list_products_for_combobox,
    product_used_in_importations,
    restore_product,
)
from app.services.product_import import commit_product_import, export_products_xlsx, preview_product_import

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/groups", response_model=list[str])
def product_groups(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    visibility: str = Query("active", pattern="^(active|archived|cancelled|all)$"),
) -> list[str]:
    return list_product_groups(db, visibility=visibility)


@router.get("/catalog", response_model=ProductCatalogResponse)
def catalog_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    q: str | None = None,
    visibility: str = Query("active", pattern="^(active|archived|cancelled|all)$"),
    lifecycle_status: str | None = None,
    product_group: str | None = None,
    quick_filter: str | None = None,
    sort: str = "sku_code",
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items, total = list_product_catalog(
        db,
        q=q,
        visibility=visibility,
        lifecycle_status=lifecycle_status,
        product_group=product_group,
        quick_filter=quick_filter,
        sort=sort,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    return ProductCatalogResponse(items=[ProductCatalogRow(**i) for i in items], total=total)


@router.get("/export")
def export_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    visibility: str = Query("active", pattern="^(active|archived|cancelled|all)$"),
):
    items, _ = list_product_catalog(db, visibility=visibility, limit=5000, offset=0)
    if format == "xlsx":
        data = export_products_xlsx(items)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="produtos.xlsx"'},
        )
    header = [
        "sku_code", "description", "product_group", "lifecycle_status", "ncm",
        "supplier_code", "default_supplier_name", "country_of_origin", "weight_kg", "volume_m3",
    ]
    lines = [
        ",".join(f'"{str(row.get(h, "")).replace(chr(34), chr(34)*2)}"' for h in header)
        for row in items
    ]
    body = "\uFEFF" + ",".join(header) + "\n" + "\n".join(lines)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="produtos.csv"'},
    )


@router.post("/import/preview", response_model=ProductImportPreviewResponse)
async def import_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    content = await file.read()
    result = preview_product_import(content, filename=file.filename or "")
    return ProductImportPreviewResponse(
        valid_count=result["valid_count"],
        invalid_count=result["invalid_count"],
        rows=[ProductImportPreviewRow(**r) for r in result["rows"]],
    )


@router.post("/import/commit")
def import_commit(
    payload: ProductImportCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    try:
        result = commit_product_import(
            db, payload.rows, user_id=current_user.id, confirm=payload.confirm
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result


@router.post("/bulk/archive", response_model=ProductBulkActionResponse)
def bulk_archive(
    payload: ProductBulkArchiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    result = bulk_archive_products(
        db, payload.product_ids, user_id=current_user.id, reason=payload.reason
    )
    for pid in result.succeeded:
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="product",
            entity_id=str(pid),
            action="archive",
            justification=payload.reason,
        )
    db.commit()
    return ProductBulkActionResponse(**result.to_dict())


@router.post("/bulk/restore", response_model=ProductBulkActionResponse)
def bulk_restore(
    payload: ProductBulkIdsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    result = bulk_restore_products(db, payload.product_ids)
    for pid in result.succeeded:
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="product",
            entity_id=str(pid),
            action="restore",
        )
    db.commit()
    return ProductBulkActionResponse(**result.to_dict())


@router.post("/bulk/status", response_model=ProductBulkActionResponse)
def bulk_status(
    payload: ProductBulkStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    result = bulk_set_lifecycle_status(
        db, payload.product_ids, payload.lifecycle_status, user_id=current_user.id
    )
    for pid in result.succeeded:
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="product",
            entity_id=str(pid),
            action="lifecycle_change",
            new_value=payload.lifecycle_status,
        )
    db.commit()
    return ProductBulkActionResponse(**result.to_dict())


@router.post("/bulk/cancel", response_model=ProductBulkActionResponse)
def bulk_cancel(
    payload: ProductBulkCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    result = bulk_cancel_products(
        db, payload.product_ids, user_id=current_user.id, reason=payload.reason
    )
    for pid in result.succeeded:
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="product",
            entity_id=str(pid),
            action="cancel",
            justification=payload.reason,
        )
    db.commit()
    return ProductBulkActionResponse(**result.to_dict())


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    include_inactive: bool = False,
    for_combobox: bool = False,
):
    if for_combobox:
        return list_products_for_combobox(db)
    q = db.query(Product)
    if not include_inactive:
        q = q.filter(Product.is_active.is_(True))
    return q.order_by(Product.sku_code).all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    if db.query(Product).filter(Product.sku_code == payload.sku_code).first():
        raise HTTPException(status_code=409, detail="SKU já existe")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="create",
    )
    return product


@router.get("/{product_id}/detail", response_model=ProductDetailResponse)
def product_detail(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    detail = get_product_detail(db, product_id)
    if not detail:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    return ProductDetailResponse(**detail)


@router.get("/{product_id}/readiness", response_model=ProductReadinessResponse)
def product_readiness(
    product_id: int,
    context: str = Query("importation"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    data = compute_product_readiness(product, context)
    return ProductReadinessResponse(**data)


@router.get("/{product_id}/audit", response_model=list[ProductAuditRow])
def product_audit(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    rows = list_product_audit(db, product_id)
    user_ids = {r.user_id for r in rows if r.user_id}
    users: dict[int, str] = {}
    if user_ids:
        users = {
            u.id: u.name
            for u in db.query(User).filter(User.id.in_(user_ids)).all()
        }
    return [
        ProductAuditRow(
            id=r.id,
            action=r.action,
            timestamp=r.timestamp,
            field_changed=r.field_changed,
            old_value=r.old_value,
            new_value=r.new_value,
            justification=r.justification,
            user_name=users.get(r.user_id) if r.user_id else None,
        )
        for r in rows
    ]


@router.get("/{product_id}/orders", response_model=ProductOrdersResponse)
def product_orders(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items, total = list_product_orders(
        db, product_id, q=q, status=status_filter, limit=limit, offset=offset
    )
    return ProductOrdersResponse(
        items=[ProductOrderRow(**i) for i in items],
        total=total,
    )


@router.get("/{product_id}/cost-history", response_model=ProductCostHistoryResponse)
def product_cost_history(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    limit: int = Query(50, ge=1, le=200),
):
    items = list_product_cost_history(db, product_id, limit=limit)
    return ProductCostHistoryResponse(items=[ProductCostHistoryRow(**i) for i in items])


@router.post("/{product_id}/archive", response_model=ProductDetailResponse)
def archive_product_endpoint(
    product_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    archive_product(db, product, user_id=current_user.id, reason=payload.reason)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="archive",
        justification=payload.reason,
    )
    db.commit()
    detail = get_product_detail(db, product_id)
    return ProductDetailResponse(**detail)


@router.post("/{product_id}/restore", response_model=ProductDetailResponse)
def restore_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    restore_product(db, product)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="restore",
    )
    db.commit()
    detail = get_product_detail(db, product_id)
    return ProductDetailResponse(**detail)


@router.post("/{product_id}/cancel", response_model=ProductResponse)
def cancel_product(
    product_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    cancel_product_record(db, product, user_id=current_user.id, reason=payload.reason)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="cancel",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")

    data = payload.model_dump(exclude_unset=True)
    ncm_reason = data.pop("ncm_change_reason", None)
    if "ncm" in data and data["ncm"] != product.ncm and product_used_in_importations(db, product_id):
        if not ncm_reason or len(ncm_reason.strip()) < 3:
            raise HTTPException(
                status_code=422,
                detail="Alteração de NCM em produto já usado exige ncm_change_reason (mín. 3 caracteres).",
            )
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="product",
            entity_id=str(product.id),
            action="update",
            field_changed="ncm",
            old_value=str(product.ncm) if product.ncm else None,
            new_value=str(data["ncm"]) if data["ncm"] else None,
            justification=ncm_reason,
        )

    for field, value in data.items():
        old = getattr(product, field)
        setattr(product, field, value)
        if field != "ncm" and old != value:
            write_audit_log(
                db,
                user_id=current_user.id,
                entity_type="product",
                entity_id=str(product.id),
                action="update",
                field_changed=field,
                old_value=str(old) if old is not None else None,
                new_value=str(value) if value is not None else None,
            )

    db.commit()
    db.refresh(product)
    return product
