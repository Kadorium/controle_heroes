from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.catalog.filters import ProductListFilters
from app.catalog.models import CatalogImportBatch, Product, ProductCategory, ProductType, Supplier

PRODUCT_SORT = {
    "sku": Product.sku.asc(),
    "-sku": Product.sku.desc(),
    "description": Product.description.asc(),
    "-description": Product.description.desc(),
    "commercial_name": Product.commercial_name.asc(),
    "-commercial_name": Product.commercial_name.desc(),
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


def get_products_by_ids(db: Session, product_ids: list[int] | set[int]) -> list[Product]:
    ids = sorted({int(i) for i in product_ids})
    if not ids:
        return []
    return (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.product_type))
        .filter(Product.id.in_(ids))
        .all()
    )


def get_supplier(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def get_suppliers_by_ids(db: Session, supplier_ids: list[int] | set[int]) -> list[Supplier]:
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
    return (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.product_type))
        .filter(Product.id == product_id)
        .first()
    )


def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.product_type))
        .filter(Product.sku == sku)
        .first()
    )


def get_product_by_ean(db: Session, ean: str, *, exclude_id: int | None = None) -> Product | None:
    query = db.query(Product).filter(Product.ean == ean)
    if exclude_id is not None:
        query = query.filter(Product.id != exclude_id)
    return query.first()


def list_categories(db: Session) -> list[ProductCategory]:
    return db.query(ProductCategory).order_by(ProductCategory.position.asc()).all()


def list_product_types(db: Session) -> list[ProductType]:
    return db.query(ProductType).order_by(ProductType.position.asc()).all()


def get_category(db: Session, category_id: int) -> ProductCategory | None:
    return db.get(ProductCategory, category_id)


def get_product_type(db: Session, type_id: int) -> ProductType | None:
    return db.get(ProductType, type_id)


def add_import_batch(db: Session, batch: CatalogImportBatch) -> CatalogImportBatch:
    db.add(batch)
    db.flush()
    return batch


def _csv_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def _in_ci(query, col, raw: str | None):
    tokens = _csv_tokens(raw)
    if not tokens or col is None:
        return query
    return query.filter(func.lower(col).in_(tokens))


def _attr_text(key: str):
    return Product.attributes[key].as_string()


def _product_query(
    db: Session, filters: ProductListFilters, *, for_count: bool = False, bare: bool = False
):
    query = db.query(func.count(Product.id)) if for_count else db.query(Product)
    if not for_count and not bare:
        query = query.options(joinedload(Product.category), joinedload(Product.product_type))
    query = query.outerjoin(Product.category).outerjoin(Product.product_type)

    if filters.is_active is True or (filters.is_active is None and filters.active_only):
        query = query.filter(Product.is_active.is_(True))
    elif filters.is_active is False:
        query = query.filter(Product.is_active.is_(False))

    if filters.q:
        like = f"%{filters.q.strip()}%"
        clauses = [
            Product.sku.ilike(like),
            Product.description.ilike(like),
            Product.commercial_name.ilike(like),
            Product.short_description.ilike(like),
            Product.subcategory.ilike(like),
            Product.ean.ilike(like),
            Product.ncm.ilike(like),
            Product.supplier_sku.ilike(like),
            ProductCategory.name.ilike(like),
            ProductType.name.ilike(like),
            _attr_text("sport").ilike(like),
            _attr_text("model").ilike(like),
            _attr_text("line").ilike(like),
            _attr_text("collection_year").ilike(like),
            _attr_text("garment_kind").ilike(like),
        ]
        query = query.filter(or_(*clauses))

    if filters.incomplete:
        query = query.filter(or_(Product.ncm.is_(None), Product.ean.is_(None)))
    if filters.missing_ncm:
        query = query.filter(Product.ncm.is_(None))
    if filters.needs_review:
        query = query.filter(Product.import_decision == "REVISAR")
    if filters.needs_classification_review:
        query = query.filter(Product.taxonomy_status == "REVIEW")
    if filters.short_generic:
        query = query.filter(Product.short_generic.is_(True))
    if filters.quality_incomplete:
        query = query.filter(
            or_(
                Product.category_id.is_(None),
                Product.product_type_id.is_(None),
                Product.short_description.is_(None),
                Product.short_description == "",
            )
        )
    if filters.missing_image:
        query = query.filter(Product.id.isnot(None))
    if filters.category:
        token = filters.category.strip().lower()
        query = query.filter(
            or_(
                func.lower(ProductCategory.slug) == token,
                func.lower(ProductCategory.name) == token,
            )
        )
    if filters.subcategory:
        query = query.filter(func.lower(Product.subcategory) == filters.subcategory.strip().lower())
    if filters.product_type:
        token = filters.product_type.strip().lower()
        query = query.filter(
            or_(
                func.lower(ProductType.slug) == token,
                func.lower(ProductType.name) == token,
            )
        )
    if filters.source_kind:
        query = query.filter(Product.source_kind == filters.source_kind.strip())

    query = _in_ci(query, Product.size, filters.size)
    query = _in_ci(query, Product.color, filters.color)
    query = _in_ci(query, Product.country_of_origin, filters.origin)
    query = _in_ci(query, Product.unit, filters.unit)
    query = _in_ci(query, Product.ean, filters.ean)
    query = _in_ci(query, Product.supplier_sku, filters.supplier_sku)
    query = _in_ci(query, _attr_text("sport"), filters.sport)
    query = _in_ci(query, _attr_text("collection_year"), filters.collection_year)
    query = _in_ci(query, _attr_text("model"), filters.model)
    query = _in_ci(query, _attr_text("garment_kind"), filters.garment_kind)
    query = _in_ci(query, _attr_text("gender"), filters.gender)
    return query


def _product_order(sort: str | None):
    key = sort or "commercial_name"
    if key == "quality":
        incomplete_flag = case(
            (
                or_(
                    Product.category_id.is_(None),
                    Product.product_type_id.is_(None),
                    Product.ncm.is_(None),
                ),
                1,
            ),
            else_=0,
        )
        return incomplete_flag.desc(), Product.commercial_name.asc()
    if key == "description":
        return (Product.commercial_name.asc(),)
    order = PRODUCT_SORT.get(key, Product.commercial_name.asc())
    return (order,)


def list_products_filtered(db: Session, filters: ProductListFilters) -> list[Product]:
    query = _product_query(db, filters, for_count=False)
    return query.order_by(*_product_order(filters.sort)).offset(filters.offset).limit(filters.limit).all()


def count_products_filtered(db: Session, filters: ProductListFilters) -> int:
    query = _product_query(db, filters, for_count=True)
    return int(query.scalar() or 0)


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
    origin: str | None = None,
    is_active: bool | None = None,
) -> list[Product]:
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
    return list_products_filtered(db, filters)


def count_products(
    db: Session,
    *,
    q: str | None,
    active_only: bool,
    incomplete: bool = False,
    missing_ncm: bool = False,
    size: str | None = None,
    color: str | None = None,
    origin: str | None = None,
    is_active: bool | None = None,
) -> int:
    filters = ProductListFilters(
        q=q,
        active_only=active_only,
        is_active=is_active,
        incomplete=incomplete,
        missing_ncm=missing_ncm,
        size=size,
        color=color,
        origin=origin,
    )
    return count_products_filtered(db, filters)


def product_list_summary(db: Session) -> dict[str, int]:
    total = int(db.query(func.count(Product.id)).scalar() or 0)
    incomplete = int(
        db.query(func.count(Product.id))
        .filter(or_(Product.ncm.is_(None), Product.ean.is_(None)))
        .scalar()
        or 0
    )
    missing_ncm = int(db.query(func.count(Product.id)).filter(Product.ncm.is_(None)).scalar() or 0)
    needs_review = int(
        db.query(func.count(Product.id)).filter(Product.import_decision == "REVISAR").scalar() or 0
    )
    needs_classification_review = int(
        db.query(func.count(Product.id)).filter(Product.taxonomy_status == "REVIEW").scalar() or 0
    )
    short_generic = int(
        db.query(func.count(Product.id)).filter(Product.short_generic.is_(True)).scalar() or 0
    )
    quality_incomplete = int(
        db.query(func.count(Product.id))
        .filter(
            or_(
                Product.category_id.is_(None),
                Product.product_type_id.is_(None),
                Product.short_description.is_(None),
                Product.short_description == "",
            )
        )
        .scalar()
        or 0
    )
    return {
        "total": total,
        "incomplete": incomplete,
        "missing_ncm": missing_ncm,
        "needs_review": needs_review,
        "needs_product_review": needs_review,
        "needs_classification_review": needs_classification_review,
        "short_generic": short_generic,
        "missing_image": total,
        "quality_incomplete": quality_incomplete,
    }


def exceptions(db: Session, *, limit: int = 20) -> list[dict]:
    filters = ProductListFilters(needs_review=True, limit=limit, offset=0)
    items = list_products_filtered(db, filters)
    out = []
    for p in items:
        out.append(
            {
                "kind": "catalog_review",
                "severity": "warning",
                "title": p.commercial_name or p.sku,
                "reason": "Cadastro incompleto — precisa de revisão",
                "entity_id": p.id,
                "href": f"/catalog/products/{p.id}",
                "since": p.updated_at.isoformat() if p.updated_at else None,
                "module": "catalog",
            }
        )
    return out


def _facet_values(db: Session, filters: ProductListFilters, col, *, attr_key: str | None = None) -> list[dict]:
    query = _product_query(db, filters, for_count=False, bare=True)
    expr = _attr_text(attr_key) if attr_key else col
    rows = (
        query.with_entities(expr, func.count(Product.id))
        .filter(expr.isnot(None), expr != "")
        .group_by(expr)
        .order_by(func.count(Product.id).desc(), expr.asc())
        .limit(50)
        .all()
    )
    return [{"value": str(value), "count": int(count)} for value, count in rows if value]


def product_facets(db: Session, filters: ProductListFilters) -> dict[str, list[dict]]:
    facets: dict[str, list[dict]] = {}
    mapping = {
        "size": (Product.size, None),
        "color": (Product.color, None),
        "origin": (Product.country_of_origin, None),
        "unit": (Product.unit, None),
        "sport": (None, "sport"),
        "collection_year": (None, "collection_year"),
        "model": (None, "model"),
        "line": (None, "line"),
        "garment_kind": (None, "garment_kind"),
        "gender": (None, "gender"),
        "subcategory": (Product.subcategory, None),
    }
    for key, (col, attr_key) in mapping.items():
        values = _facet_values(db, filters, col, attr_key=attr_key)
        if values:
            facets[key] = values

    cat_rows = (
        _product_query(db, filters, for_count=False, bare=True)
        .with_entities(ProductCategory.slug, ProductCategory.name, func.count(Product.id))
        .filter(Product.category_id.isnot(None))
        .group_by(ProductCategory.slug, ProductCategory.name)
        .order_by(ProductCategory.name.asc())
        .all()
    )
    if cat_rows:
        facets["category"] = [
            {"value": slug, "label": name, "count": int(count)} for slug, name, count in cat_rows if slug
        ]

    type_rows = (
        _product_query(db, filters, for_count=False, bare=True)
        .with_entities(ProductType.slug, ProductType.name, func.count(Product.id))
        .filter(Product.product_type_id.isnot(None))
        .group_by(ProductType.slug, ProductType.name)
        .order_by(ProductType.name.asc())
        .all()
    )
    if type_rows:
        facets["product_type"] = [
            {"value": slug, "label": name, "count": int(count)} for slug, name, count in type_rows if slug
        ]
    return facets


def distinct_product_values(db: Session, field: str) -> list[str]:
    attr_fields = {
        "sport": "sport",
        "model": "model",
        "collection_year": "collection_year",
        "line": "line",
        "garment_kind": "garment_kind",
        "gender": "gender",
    }
    if field in attr_fields:
        col = _attr_text(attr_fields[field])
    else:
        col = {
            "size": Product.size,
            "color": Product.color,
            "country_of_origin": Product.country_of_origin,
            "unit": Product.unit,
            "subcategory": Product.subcategory,
            "ean": Product.ean,
            "supplier_sku": Product.supplier_sku,
        }.get(field)
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
