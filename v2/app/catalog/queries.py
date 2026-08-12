from sqlalchemy.orm import Session

from app.catalog import repository as repo
from app.catalog.errors import ProductNotFound, SupplierNotFound
from app.catalog.models import Product, Supplier


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    row = repo.get_supplier(db, supplier_id)
    if not row:
        raise SupplierNotFound(supplier_id)
    return row


def get_suppliers_bulk(db: Session, supplier_ids: list[int] | set[int]) -> dict[int, Supplier]:
    """Resolve fornecedores em lote. Ids ausentes simplesmente não entram no mapa."""
    return {s.id: s for s in repo.get_suppliers_by_ids(db, supplier_ids)}


def list_suppliers(
    db: Session, *, q: str | None = None, active_only: bool = False, limit: int = 50, offset: int = 0
) -> list[Supplier]:
    return repo.list_suppliers(db, q=q, active_only=active_only, limit=limit, offset=offset)


def get_supplier_by_code(db: Session, code: str) -> Supplier | None:
    """Lookup exato por código (sem raise). Usado pelo commit de ingestão."""
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
