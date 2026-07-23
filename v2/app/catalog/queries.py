from sqlalchemy.orm import Session

from app.catalog import repository as repo
from app.catalog.errors import ProductNotFound, SupplierNotFound
from app.catalog.models import Product, Supplier


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    row = repo.get_supplier(db, supplier_id)
    if not row:
        raise SupplierNotFound(supplier_id)
    return row


def list_suppliers(
    db: Session, *, q: str | None = None, active_only: bool = False, limit: int = 50, offset: int = 0
) -> list[Supplier]:
    return repo.list_suppliers(db, q=q, active_only=active_only, limit=limit, offset=offset)


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


def list_products(
    db: Session, *, q: str | None = None, active_only: bool = False, limit: int = 50, offset: int = 0
) -> list[Product]:
    return repo.list_products(db, q=q, active_only=active_only, limit=limit, offset=offset)


def resolve_product(db: Session, *, product_id: int | None = None, sku: str | None = None) -> Product:
    if product_id is not None:
        return get_product(db, product_id)
    if sku:
        return get_product_by_sku(db, sku)
    raise ProductNotFound("?")
