from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog import repository as repo
from app.catalog.errors import CatalogValidationError, SkuDuplicate, SupplierCodeDuplicate
from app.catalog.models import Product, Supplier
from app.catalog.queries import get_product, get_supplier


def create_supplier(
    db: Session,
    *,
    name: str,
    code: str | None = None,
    country_code: str | None = None,
    is_active: bool = True,
    tax_id: str | None = None,
) -> Supplier:
    from app.catalog.normalization import normalize_country, normalize_tax_id

    name = (name or "").strip()
    if not name:
        raise CatalogValidationError("Nome do fornecedor é obrigatório")
    code_norm = code.strip() if code and code.strip() else None
    country = normalize_country(country_code)
    tax_norm = normalize_tax_id(tax_id, country_code=country)
    if tax_norm and not country:
        raise CatalogValidationError("Identificador fiscal exige o país")
    if code_norm and repo.get_supplier_by_code(db, code_norm):
        raise SupplierCodeDuplicate(code_norm)
    if tax_norm and country and repo.get_supplier_by_tax_id(db, country_code=country, tax_id=tax_norm):
        raise CatalogValidationError("Identificador fiscal já cadastrado neste país")

    kwargs: dict = {
        "name": name,
        "code": code_norm,
        "country_code": country,
        "is_active": is_active,
    }
    if hasattr(Supplier, "tax_id"):
        kwargs["tax_id"] = tax_norm

    try:
        return repo.add_supplier(db, Supplier(**kwargs))
    except IntegrityError as exc:
        db.rollback()
        if code_norm:
            raise SupplierCodeDuplicate(code_norm) from exc
        raise


def update_supplier(
    db: Session,
    supplier_id: int,
    *,
    name: str | None = None,
    code: str | None = None,
    country_code: str | None = None,
    is_active: bool | None = None,
    tax_id: str | None = None,
    tax_id_set: bool = False,
) -> Supplier:
    from app.catalog.normalization import normalize_country, normalize_tax_id

    row = get_supplier(db, supplier_id)
    if name is not None:
        name_n = name.strip()
        if not name_n:
            raise CatalogValidationError("Nome do fornecedor é obrigatório")
        row.name = name_n
    if code is not None:
        code_norm = code.strip() if code.strip() else None
        if code_norm:
            existing = repo.get_supplier_by_code(db, code_norm)
            if existing and existing.id != row.id:
                raise SupplierCodeDuplicate(code_norm)
        row.code = code_norm
    if country_code is not None:
        row.country_code = normalize_country(country_code)
    if is_active is not None:
        row.is_active = is_active
    if tax_id_set and hasattr(row, "tax_id"):
        country = row.country_code
        tax_norm = normalize_tax_id(tax_id, country_code=country)
        if tax_norm and not country:
            raise CatalogValidationError("Identificador fiscal exige o país")
        if tax_norm and country:
            clash = repo.get_supplier_by_tax_id(
                db, country_code=country, tax_id=tax_norm, exclude_id=row.id
            )
            if clash:
                raise CatalogValidationError("Identificador fiscal já cadastrado neste país")
        row.tax_id = tax_norm
    db.flush()
    return row


def create_product(
    db: Session,
    *,
    sku: str,
    description: str,
    is_active: bool = True,
) -> Product:
    sku_norm = (sku or "").strip()
    if not sku_norm:
        raise CatalogValidationError("SKU é obrigatório")
    desc = (description or "").strip()
    if not desc:
        raise CatalogValidationError("Descrição é obrigatória")
    if repo.get_product_by_sku(db, sku_norm):
        raise SkuDuplicate(sku_norm)
    try:
        return repo.add_product(db, Product(sku=sku_norm, description=desc, is_active=is_active))
    except IntegrityError as exc:
        db.rollback()
        raise SkuDuplicate(sku_norm) from exc


def update_product(
    db: Session,
    product_id: int,
    *,
    description: str | None = None,
    is_active: bool | None = None,
    ean: str | None = None,
    ean_set: bool = False,
    size: str | None = None,
    size_set: bool = False,
    color: str | None = None,
    color_set: bool = False,
    ncm: str | None = None,
    ncm_set: bool = False,
    country_of_origin: str | None = None,
    country_of_origin_set: bool = False,
    unit: str | None = None,
    unit_set: bool = False,
    net_weight_kg: object | None = None,
    net_weight_kg_set: bool = False,
) -> Product:
    from app.catalog.normalization import (
        normalize_country,
        normalize_ean,
        normalize_free_text,
        normalize_ncm,
        normalize_unit,
        normalize_weight,
    )

    row = get_product(db, product_id)
    if description is not None:
        desc = description.strip()
        if not desc:
            raise CatalogValidationError("Descrição é obrigatória")
        row.description = desc
    if is_active is not None:
        row.is_active = is_active
    if ean_set and hasattr(row, "ean"):
        ean_n = normalize_ean(ean)
        if ean_n:
            clash = repo.get_product_by_ean(db, ean_n, exclude_id=row.id)
            if clash:
                raise CatalogValidationError("EAN já cadastrado")
        row.ean = ean_n
    if size_set and hasattr(row, "size"):
        row.size = normalize_free_text(size)
    if color_set and hasattr(row, "color"):
        row.color = normalize_free_text(color)
    if ncm_set and hasattr(row, "ncm"):
        row.ncm = normalize_ncm(ncm)
    if country_of_origin_set and hasattr(row, "country_of_origin"):
        row.country_of_origin = normalize_country(country_of_origin)
    if unit_set and hasattr(row, "unit"):
        row.unit = normalize_unit(unit)
    if net_weight_kg_set and hasattr(row, "net_weight_kg"):
        row.net_weight_kg = normalize_weight(net_weight_kg)
    db.flush()
    return row
