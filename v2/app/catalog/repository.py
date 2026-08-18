from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.catalog.models import Product, Supplier

PRODUCT_SORT = {
    "sku": Product.sku.asc(),
    "-sku": Product.sku.desc(),
    "description": Product.description.asc(),
    "-description": Product.description.desc(),
    "created_at": Product.created_at.asc(),
    "-created_at": Product.created_at.desc(),
}

SUPPLIER_SORT = {
    "name": Supplier.name.asc(),
    "-name": Supplier.name.desc(),
    "code": Supplier.code.asc(),
    "-code": Supplier.code.desc(),
    "created_at": Supplier.created_at.asc(),
    "-created_at": Supplier.created_at.desc(),
}


def get_supplier(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def get_suppliers_by_ids(db: Session, supplier_ids: list[int] | set[int]) -> list[Supplier]:
    """Uma query IN (...) — ids vazios → []."""
    ids = sorted({int(i) for i in supplier_ids})
    if not ids:
        return []
    return db.query(Supplier).filter(Supplier.id.in_(ids)).all()


def get_supplier_by_code(db: Session, code: str) -> Supplier | None:
    return db.query(Supplier).filter(Supplier.code == code).first()


def get_supplier_by_tax_id(
    db: Session, *, country_code: str, tax_id: str, exclude_id: int | None = None
) -> Supplier | None:
    tax_col = getattr(Supplier, "tax_id", None)
    if tax_col is None:
        return None
    query = db.query(Supplier).filter(
        Supplier.country_code == country_code,
        tax_col == tax_id,
    )
    if exclude_id is not None:
        query = query.filter(Supplier.id != exclude_id)
    return query.first()


def _supplier_filters(query, *, q: str | None, active_only: bool, missing_tax_id: bool = False):
    if active_only:
        query = query.filter(Supplier.is_active.is_(True))
    if missing_tax_id and hasattr(Supplier, "tax_id"):
        query = query.filter(Supplier.tax_id.is_(None))
    if q:
        like = f"%{q.strip()}%"
        clauses = [Supplier.name.ilike(like), Supplier.code.ilike(like)]
        if hasattr(Supplier, "tax_id"):
            clauses.append(Supplier.tax_id.ilike(like))
        query = query.filter(or_(*clauses))
    return query


def list_suppliers(
    db: Session,
    *,
    q: str | None,
    active_only: bool,
    limit: int,
    offset: int,
    sort: str | None = None,
    missing_tax_id: bool = False,
) -> list[Supplier]:
    query = _supplier_filters(
        db.query(Supplier), q=q, active_only=active_only, missing_tax_id=missing_tax_id
    )
    order = SUPPLIER_SORT.get(sort or "name", Supplier.name.asc())
    return query.order_by(order).offset(offset).limit(limit).all()


def count_suppliers(
    db: Session,
    *,
    q: str | None,
    active_only: bool,
    missing_tax_id: bool = False,
) -> int:
    query = _supplier_filters(
        db.query(func.count(Supplier.id)),
        q=q,
        active_only=active_only,
        missing_tax_id=missing_tax_id,
    )
    return int(query.scalar() or 0)


def add_supplier(db: Session, supplier: Supplier) -> Supplier:
    db.add(supplier)
    db.flush()
    return supplier


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return db.query(Product).filter(Product.sku == sku).first()


def get_product_by_ean(db: Session, ean: str, *, exclude_id: int | None = None) -> Product | None:
    if not hasattr(Product, "ean"):
        return None
    query = db.query(Product).filter(Product.ean == ean)
    if exclude_id is not None:
        query = query.filter(Product.id != exclude_id)
    return query.first()


def _product_filters(
    query,
    *,
    q: str | None,
    active_only: bool,
    incomplete: bool = False,
    missing_ncm: bool = False,
    size: str | None = None,
    color: str | None = None,
):
    if active_only:
        query = query.filter(Product.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        clauses = [Product.sku.ilike(like), Product.description.ilike(like)]
        if hasattr(Product, "ean"):
            clauses.append(Product.ean.ilike(like))
        if hasattr(Product, "ncm"):
            clauses.append(Product.ncm.ilike(like))
        query = query.filter(or_(*clauses))
    if incomplete and hasattr(Product, "ncm") and hasattr(Product, "ean"):
        query = query.filter(or_(Product.ncm.is_(None), Product.ean.is_(None)))
    if missing_ncm and hasattr(Product, "ncm"):
        query = query.filter(Product.ncm.is_(None))
    if size and hasattr(Product, "size"):
        query = query.filter(func.lower(Product.size) == size.strip().lower())
    if color and hasattr(Product, "color"):
        query = query.filter(func.lower(Product.color) == color.strip().lower())
    return query


def list_products(
    db: Session,
    *,
    q: str | None,
    active_only: bool,
    limit: int,
    offset: int,
    sort: str | None = None,
    incomplete: bool = False,
    missing_ncm: bool = False,
    size: str | None = None,
    color: str | None = None,
) -> list[Product]:
    query = _product_filters(
        db.query(Product),
        q=q,
        active_only=active_only,
        incomplete=incomplete,
        missing_ncm=missing_ncm,
        size=size,
        color=color,
    )
    order = PRODUCT_SORT.get(sort or "sku", Product.sku.asc())
    return query.order_by(order).offset(offset).limit(limit).all()


def count_products(
    db: Session,
    *,
    q: str | None,
    active_only: bool,
    incomplete: bool = False,
    missing_ncm: bool = False,
    size: str | None = None,
    color: str | None = None,
) -> int:
    query = _product_filters(
        db.query(func.count(Product.id)),
        q=q,
        active_only=active_only,
        incomplete=incomplete,
        missing_ncm=missing_ncm,
        size=size,
        color=color,
    )
    return int(query.scalar() or 0)


def distinct_product_values(db: Session, field: str) -> list[str]:
    col = {"size": getattr(Product, "size", None), "color": getattr(Product, "color", None)}.get(field)
    if col is None:
        return []
    rows = (
        db.query(col)
        .filter(col.isnot(None), col != "")
        .distinct()
        .order_by(col.asc())
        .limit(200)
        .all()
    )
    return [str(r[0]) for r in rows if r[0]]


def add_product(db: Session, product: Product) -> Product:
    db.add(product)
    db.flush()
    return product
