from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.catalog import public as catalog_public
from app.catalog.commands import UNSET
from app.catalog.filters import ProductListFilters
from app.catalog.models import Product, Supplier
from app.catalog.public import CatalogError
from app.catalog.schemas import (
    AttributeValuesResponse,
    CategoryResponse,
    ProductCreate,
    ProductListResponse,
    ProductListSummary,
    ProductPatch,
    ProductResponse,
    ProductTypeResponse,
    SupplierCreate,
    SupplierListResponse,
    SupplierPatch,
    SupplierResponse,
    TaxonomyResponse,
)
from app.catalog.serialize import product_dict
from app.catalog.taxonomy import SUBCATEGORIES
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.foundation.database import get_db

router = APIRouter(tags=["catalog"])

ATTR_FIELDS = (
    "size|color|country_of_origin|unit|subcategory|ean|supplier_sku|"
    "sport|model|collection_year|line|garment_kind|gender"
)


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


def _product_out(p: Product, notices: list[str] | None = None) -> ProductResponse:
    return ProductResponse.model_validate(product_dict(p, notices=notices))


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


@router.get("/catalog/taxonomy", response_model=TaxonomyResponse)
def get_taxonomy(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    cats, types = catalog_public.taxonomy_catalog(db)
    return TaxonomyResponse(
        categories=[
            CategoryResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                subcategories=list(SUBCATEGORIES.get(c.slug, ())),
            )
            for c in cats
        ],
        product_types=[
            ProductTypeResponse(
                id=t.id,
                name=t.name,
                slug=t.slug,
                recommended_attributes=list(t.recommended_attributes or []),
            )
            for t in types
        ],
    )


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
            loaded = catalog_public.get_product(uow.session, row.id)
            return _product_out(loaded)
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
    is_active: bool | None = Query(None),
    incomplete: bool = False,
    missing_ncm: bool = False,
    missing_image: bool = False,
    needs_review: bool = False,
    needs_classification_review: bool = False,
    short_generic: bool = False,
    quality_incomplete: bool = False,
    category: str | None = None,
    subcategory: str | None = None,
    product_type: str | None = None,
    sport: str | None = None,
    collection_year: str | None = None,
    color: str | None = None,
    size: str | None = None,
    origin: str | None = None,
    unit: str | None = None,
    ean: str | None = None,
    supplier_sku: str | None = None,
    model: str | None = None,
    garment_kind: str | None = None,
    gender: str | None = None,
    source_kind: str | None = None,
    sort: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "catalog:read")
    filters = ProductListFilters(
        q=q,
        active_only=active_only,
        is_active=is_active,
        incomplete=incomplete,
        missing_ncm=missing_ncm,
        missing_image=missing_image,
        needs_review=needs_review,
        needs_classification_review=needs_classification_review,
        short_generic=short_generic,
        quality_incomplete=quality_incomplete,
        category=category,
        subcategory=subcategory,
        product_type=product_type,
        sport=sport,
        collection_year=collection_year,
        color=color,
        size=size,
        origin=origin,
        unit=unit,
        ean=ean,
        supplier_sku=supplier_sku,
        model=model,
        garment_kind=garment_kind,
        gender=gender,
        source_kind=source_kind,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    items, total = catalog_public.list_products_report(db, filters)
    summary = catalog_public.product_list_summary(db)
    facets = catalog_public.product_facets(db, filters)
    return ProductListResponse(
        items=[_product_out(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
        summary=ProductListSummary(**summary),
        facets=facets,
    )


@router.get("/catalog/product-attribute-values", response_model=AttributeValuesResponse)
def product_attribute_values(
    field: str = Query(..., pattern=f"^({ATTR_FIELDS})$"),
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
    notices: list[str] = []
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
                commercial_name=dumped["commercial_name"] if "commercial_name" in dumped else UNSET,
                short_description=dumped["short_description"] if "short_description" in dumped else UNSET,
                long_description=dumped["long_description"] if "long_description" in dumped else UNSET,
                fiscal_description=dumped["fiscal_description"] if "fiscal_description" in dumped else UNSET,
                category_id=dumped["category_id"] if "category_id" in dumped else UNSET,
                product_type_id=dumped["product_type_id"] if "product_type_id" in dumped else UNSET,
                subcategory=dumped["subcategory"] if "subcategory" in dumped else UNSET,
                attributes=dumped["attributes"] if "attributes" in dumped else UNSET,
                supplier_sku=dumped["supplier_sku"] if "supplier_sku" in dumped else UNSET,
                taxonomy_status=dumped["taxonomy_status"] if "taxonomy_status" in dumped else UNSET,
                taxonomy_reason=dumped["taxonomy_reason"] if "taxonomy_reason" in dumped else UNSET,
                lifecycle_status=dumped["lifecycle_status"] if "lifecycle_status" in dumped else UNSET,
                notices=notices,
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
            loaded = catalog_public.get_product(uow.session, row.id)
            return _product_out(loaded, notices=notices)
    except CatalogError as e:
        raise _map_catalog_error(e) from e
