from sqlalchemy.orm import Session

from app.catalog import repository as repo
from app.catalog.errors import ProductNotFound, SupplierNotFound
from app.catalog.filters import ProductListFilters
from app.catalog.models import Product, ProductCategory, ProductType, Supplier


def get_products_bulk(db: Session, product_ids: list[int] | set[int]) -> dict[int, Product]:
    return {p.id: p for p in repo.get_products_by_ids(db, product_ids)}


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    row = repo.get_supplier(db, supplier_id)
    if not row:
        raise SupplierNotFound(supplier_id)
    return row


def get_suppliers_bulk(db: Session, supplier_ids: list[int] | set[int]) -> dict[int, Supplier]:
    return {s.id: s for s in repo.get_suppliers_by_ids(db, supplier_ids)}


def list_suppliers(
    db: Session, *, q: str | None = None, active_only: bool = False, limit: int = 50, offset: int = 0
) -> list[Supplier]:
    return repo.list_suppliers(db, q=q, active_only=active_only, limit=limit, offset=offset)


def get_supplier_by_code(db: Session, code: str) -> Supplier | None:
    code_norm = (code or "").strip()
    if not code_norm:
        return None
    return repo.get_supplier_by_code(db, code_norm)


def get_product(db: Session, product_id: int) -> Product:
    row = repo.get_product(db, product_id)
    if not row:
        raise ProductNotFound(product_id)
    return row


def get_product_by_sku(db: Session, sku: str) -> Product:
    row = repo.get_product_by_sku(db, sku.strip())
    if not row:
        raise ProductNotFound(sku)
    return row


def get_product_by_ean(db: Session, ean: str) -> Product:
    from app.catalog.normalization import normalize_ean

    ean_n = normalize_ean(ean)
    row = repo.get_product_by_ean(db, ean_n) if ean_n else None
    if not row:
        raise ProductNotFound(ean)
    return row


def lookup_product_by_sku_or_ean(db: Session, code: str) -> Product | None:
    """SKU canônico primeiro; se o código for EAN, o campo ean. sku ≠ ean."""
    token = (code or "").strip()
    if not token:
        return None
    row = repo.get_product_by_sku(db, token)
    if row:
        return row
    from app.catalog.errors import CatalogValidationError
    from app.catalog.normalization import normalize_ean

    try:
        ean_n = normalize_ean(token)
    except CatalogValidationError:
        return None
    if not ean_n:
        return None
    return repo.get_product_by_ean(db, ean_n)


def list_products(
    db: Session, *, q: str | None = None, active_only: bool = False, limit: int = 50, offset: int = 0
) -> list[Product]:
    return repo.list_products(db, q=q, active_only=active_only, limit=limit, offset=offset)


def list_products_page(
    db: Session,
    *,
    q: str | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    sort: str | None = None,
    incomplete: bool = False,
    missing_ncm: bool = False,
    size: str | None = None,
    color: str | None = None,
    origin: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[Product], int]:
    filters = ProductListFilters(
        q=q,
        active_only=active_only,
        is_active=is_active,
        incomplete=incomplete,
        missing_ncm=missing_ncm,
        size=size,
        color=color,
        origin=origin,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return list_products_report(db, filters)


def list_products_report(db: Session, filters: ProductListFilters) -> tuple[list[Product], int]:
    items = repo.list_products_filtered(db, filters)
    total = repo.count_products_filtered(db, filters)
    return items, total


def exceptions(db: Session, *, limit: int = 20) -> list[dict]:
    return repo.exceptions(db, limit=limit)


def list_suppliers_page(
    db: Session,
    *,
    q: str | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    sort: str | None = None,
    missing_tax_id: bool = False,
) -> tuple[list[Supplier], int]:
    items = repo.list_suppliers(
        db,
        q=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
        sort=sort,
        missing_tax_id=missing_tax_id,
    )
    total = repo.count_suppliers(
        db, q=q, active_only=active_only, missing_tax_id=missing_tax_id
    )
    return items, total


def resolve_product(db: Session, *, product_id: int | None = None, sku: str | None = None) -> Product:
    if product_id is not None:
        return get_product(db, product_id)
    if sku:
        return get_product_by_sku(db, sku)
    raise ProductNotFound("?")


def taxonomy_catalog(db: Session) -> tuple[list[ProductCategory], list[ProductType]]:
    from app.catalog.taxonomy import ensure_taxonomy

    ensure_taxonomy(db)
    return repo.list_categories(db), repo.list_product_types(db)
