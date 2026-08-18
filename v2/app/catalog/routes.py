from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.catalog import public as catalog_public
from app.catalog.public import CatalogError
from app.catalog.models import Product, Supplier
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.foundation.database import get_db

router = APIRouter(tags=["catalog"])


class SupplierCreate(BaseModel):
    name: str
    code: str | None = None
    country_code: str | None = None
    is_active: bool = True
    tax_id: str | None = None


class SupplierPatch(BaseModel):
    name: str | None = None
    code: str | None = None
    country_code: str | None = None
    is_active: bool | None = None
    tax_id: str | None = None


class SupplierResponse(BaseModel):
    id: int
    code: str | None
    name: str
    country_code: str | None
    is_active: bool
    tax_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str
    description: str
    is_active: bool = True


class ProductPatch(BaseModel):
    description: str | None = None
    is_active: bool | None = None
    ean: str | None = None
    size: str | None = None
    color: str | None = None
    ncm: str | None = None
    country_of_origin: str | None = None
    unit: str | None = None
    net_weight_kg: Decimal | None = None


class ProductResponse(BaseModel):
    id: int
    sku: str
    description: str
    is_active: bool
    ean: str | None = None
    size: str | None = None
    color: str | None = None
    ncm: str | None = None
    country_of_origin: str | None = None
    unit: str | None = None
    net_weight_kg: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int
    limit: int
    offset: int


class AttributeValuesResponse(BaseModel):
    field: str
    values: list[str]


def _map_catalog_error(exc: CatalogError) -> AppError:
    status = 404 if exc.code.endswith("not_found") else 400
    if exc.code in ("sku_duplicate", "supplier_code_duplicate"):
        status = 409
    if exc.code == "validation_error":
        status = 422
    return AppError(exc.message, code=exc.code, status_code=status)


def _supplier_out(s: Supplier) -> SupplierResponse:
    return SupplierResponse(
        id=s.id,
        code=s.code,
        name=s.name,
        country_code=s.country_code,
        is_active=s.is_active,
        tax_id=getattr(s, "tax_id", None),
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _product_out(p: Product) -> ProductResponse:
    return ProductResponse(
        id=p.id,
        sku=p.sku,
        description=p.description,
        is_active=p.is_active,
        ean=getattr(p, "ean", None),
        size=getattr(p, "size", None),
        color=getattr(p, "color", None),
        ncm=getattr(p, "ncm", None),
        country_of_origin=getattr(p, "country_of_origin", None),
        unit=getattr(p, "unit", None),
        net_weight_kg=getattr(p, "net_weight_kg", None),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:write")
    try:
        with UnitOfWork(db) as uow:
            row = catalog_public.create_supplier(
                uow.session,
                name=payload.name,
                code=payload.code,
                country_code=payload.country_code,
                is_active=payload.is_active,
                tax_id=payload.tax_id,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="supplier",
                entity_id=str(row.id),
                action="create",
                reason_code="CATALOG_SUPPLIER_CREATE",
            )
            uow.commit()
            uow.session.refresh(row)
            return _supplier_out(row)
    except CatalogError as e:
        raise _map_catalog_error(e) from e


@router.get("/suppliers", response_model=list[SupplierResponse])
def list_suppliers(
    q: str | None = None,
    active_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    rows = catalog_public.list_suppliers(
        db, q=q, active_only=active_only, limit=limit, offset=offset
    )
    return [_supplier_out(r) for r in rows]


@router.get("/catalog/supplier-list", response_model=SupplierListResponse)
def supplier_list_report(
    q: str | None = None,
    active_only: bool = False,
    missing_tax_id: bool = False,
    sort: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    items, total = catalog_public.list_suppliers_page(
        db,
        q=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
        sort=sort,
        missing_tax_id=missing_tax_id,
    )
    return SupplierListResponse(
        items=[_supplier_out(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    try:
        return _supplier_out(catalog_public.get_supplier(db, supplier_id))
    except CatalogError as e:
        raise _map_catalog_error(e) from e


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def patch_supplier(
    supplier_id: int,
    payload: SupplierPatch,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:write")
    dumped = payload.model_dump(exclude_unset=True)
    if not dumped:
        raise AppError("Nenhum campo para atualizar", code="validation_error", status_code=422)
    try:
        with UnitOfWork(db) as uow:
            row = catalog_public.update_supplier(
                uow.session,
                supplier_id,
                name=dumped.get("name"),
                code=dumped.get("code"),
                country_code=dumped.get("country_code"),
                is_active=dumped.get("is_active"),
                tax_id=dumped.get("tax_id") if "tax_id" in dumped else None,
                tax_id_set="tax_id" in dumped,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="supplier",
                entity_id=str(row.id),
                action="update",
                reason_code="CATALOG_SUPPLIER_UPDATE",
                details=",".join(sorted(dumped.keys())),
            )
            uow.commit()
            uow.session.refresh(row)
            return _supplier_out(row)
    except CatalogError as e:
        raise _map_catalog_error(e) from e


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:write")
    try:
        with UnitOfWork(db) as uow:
            row = catalog_public.create_product(
                uow.session,
                sku=payload.sku,
                description=payload.description,
                is_active=payload.is_active,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="product",
                entity_id=str(row.id),
                action="create",
                reason_code="CATALOG_PRODUCT_CREATE",
            )
            uow.commit()
            uow.session.refresh(row)
            return _product_out(row)
    except CatalogError as e:
        raise _map_catalog_error(e) from e


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    q: str | None = None,
    active_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    rows = catalog_public.list_products(
        db, q=q, active_only=active_only, limit=limit, offset=offset
    )
    return [_product_out(p) for p in rows]


@router.get("/catalog/product-list", response_model=ProductListResponse)
def product_list_report(
    q: str | None = None,
    active_only: bool = False,
    incomplete: bool = False,
    missing_ncm: bool = False,
    size: str | None = None,
    color: str | None = None,
    sort: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    items, total = catalog_public.list_products_page(
        db,
        q=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
        sort=sort,
        incomplete=incomplete,
        missing_ncm=missing_ncm,
        size=size,
        color=color,
    )
    return ProductListResponse(
        items=[_product_out(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/catalog/product-attribute-values", response_model=AttributeValuesResponse)
def product_attribute_values(
    field: str = Query(..., pattern="^(size|color)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    return AttributeValuesResponse(field=field, values=catalog_public.distinct_product_values(db, field))


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    try:
        return _product_out(catalog_public.get_product(db, product_id))
    except CatalogError as e:
        raise _map_catalog_error(e) from e


@router.patch("/products/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: int,
    payload: ProductPatch,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:write")
    dumped = payload.model_dump(exclude_unset=True)
    if not dumped:
        raise AppError("Nenhum campo para atualizar", code="validation_error", status_code=422)
    try:
        with UnitOfWork(db) as uow:
            row = catalog_public.update_product(
                uow.session,
                product_id,
                description=dumped.get("description"),
                is_active=dumped.get("is_active"),
                ean=dumped.get("ean") if "ean" in dumped else None,
                ean_set="ean" in dumped,
                size=dumped.get("size") if "size" in dumped else None,
                size_set="size" in dumped,
                color=dumped.get("color") if "color" in dumped else None,
                color_set="color" in dumped,
                ncm=dumped.get("ncm") if "ncm" in dumped else None,
                ncm_set="ncm" in dumped,
                country_of_origin=dumped.get("country_of_origin")
                if "country_of_origin" in dumped
                else None,
                country_of_origin_set="country_of_origin" in dumped,
                unit=dumped.get("unit") if "unit" in dumped else None,
                unit_set="unit" in dumped,
                net_weight_kg=dumped.get("net_weight_kg") if "net_weight_kg" in dumped else None,
                net_weight_kg_set="net_weight_kg" in dumped,
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="product",
                entity_id=str(row.id),
                action="update",
                reason_code="CATALOG_PRODUCT_UPDATE",
                details=",".join(sorted(dumped.keys())),
            )
            uow.commit()
            uow.session.refresh(row)
            return _product_out(row)
    except CatalogError as e:
        raise _map_catalog_error(e) from e
