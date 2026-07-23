from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
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


class SupplierResponse(BaseModel):
    id: int
    code: str | None
    name: str
    country_code: str | None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str
    description: str
    is_active: bool = True


class ProductResponse(BaseModel):
    id: int
    sku: str
    description: str
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


def _map_catalog_error(exc: CatalogError) -> AppError:
    status = 404 if exc.code.endswith("not_found") else 400
    if exc.code in ("sku_duplicate", "supplier_code_duplicate"):
        status = 409
    return AppError(exc.message, code=exc.code, status_code=status)


def _supplier_out(s: Supplier) -> SupplierResponse:
    return SupplierResponse.model_validate(s)


def _product_out(p: Product) -> ProductResponse:
    return ProductResponse.model_validate(p)


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
    return [_product_out(r) for r in rows]


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
