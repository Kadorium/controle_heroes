from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.catalog.models import Product, Supplier


def get_supplier(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def get_supplier_by_code(db: Session, code: str) -> Supplier | None:
    return db.query(Supplier).filter(Supplier.code == code).first()


def list_suppliers(db: Session, *, q: str | None, active_only: bool, limit: int, offset: int) -> list[Supplier]:
    query = db.query(Supplier)
    if active_only:
        query = query.filter(Supplier.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Supplier.name.ilike(like), Supplier.code.ilike(like)))
    return query.order_by(Supplier.name).offset(offset).limit(limit).all()


def add_supplier(db: Session, supplier: Supplier) -> Supplier:
    db.add(supplier)
    db.flush()
    return supplier


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return db.query(Product).filter(Product.sku == sku).first()


def list_products(db: Session, *, q: str | None, active_only: bool, limit: int, offset: int) -> list[Product]:
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Product.sku.ilike(like), Product.description.ilike(like)))
    return query.order_by(Product.sku).offset(offset).limit(limit).all()


def add_product(db: Session, product: Product) -> Product:
    db.add(product)
    db.flush()
    return product
