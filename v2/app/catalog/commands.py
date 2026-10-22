from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog import repository as repo
from app.catalog.attributes import merge_attributes, normalize_attributes, validate_subcategory
from app.catalog.errors import CatalogValidationError, SkuDuplicate, SupplierCodeDuplicate
from app.catalog.models import Product, Supplier
from app.catalog.queries import get_product, get_supplier
from app.catalog.taxonomy import LIFECYCLE_STATUSES, TAXONOMY_STATUSES, ensure_taxonomy

TYPE_CHANGE_NOTICE = (
    "Algumas informações preenchidas não são usadas neste tipo de produto. "
    "Elas serão preservadas até você revisar."
)

_UNSET = object()
UNSET = _UNSET


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
    ensure_taxonomy(db)
    try:
        return repo.add_product(
            db,
            Product(
                sku=sku_norm,
                description=desc,
                commercial_name=desc,
                is_active=is_active,
                lifecycle_status="ACTIVE" if is_active else "DISCONTINUED",
                attributes={},
                provenance={"commercial_name": "manual"},
                source_kind="manual",
            ),
        )
    except IntegrityError as exc:
        db.rollback()
        raise SkuDuplicate(sku_norm) from exc


def _mark_manual(row: Product, field: str) -> None:
    prov = dict(row.provenance or {})
    prov[field] = "manual"
    row.provenance = prov


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
    commercial_name: object = _UNSET,
    short_description: object = _UNSET,
    long_description: object = _UNSET,
    fiscal_description: object = _UNSET,
    category_id: object = _UNSET,
    product_type_id: object = _UNSET,
    subcategory: object = _UNSET,
    attributes: object = _UNSET,
    supplier_sku: object = _UNSET,
    taxonomy_status: object = _UNSET,
    taxonomy_reason: object = _UNSET,
    lifecycle_status: object = _UNSET,
    notices: list[str] | None = None,
) -> Product:
    from app.catalog.normalization import (
        normalize_country,
        normalize_ean,
        normalize_free_text,
        normalize_ncm,
        normalize_unit,
        normalize_weight,
    )

    ensure_taxonomy(db)
    row = get_product(db, product_id)
    collected = notices if notices is not None else []

    if commercial_name is not _UNSET:
        name = (str(commercial_name).strip() if commercial_name else "")
        if not name:
            raise CatalogValidationError("Nome comercial é obrigatório")
        row.commercial_name = name
        row.description = name[:512]
        _mark_manual(row, "commercial_name")
    elif description is not None:
        desc = description.strip()
        if not desc:
            raise CatalogValidationError("Descrição é obrigatória")
        row.description = desc
        row.commercial_name = desc
        _mark_manual(row, "commercial_name")

    if is_active is not None:
        row.is_active = is_active
        _mark_manual(row, "is_active")
        if lifecycle_status is _UNSET:
            row.lifecycle_status = "ACTIVE" if is_active else "DISCONTINUED"

    if ean_set:
        ean_n = normalize_ean(ean)
        if ean_n:
            clash = repo.get_product_by_ean(db, ean_n, exclude_id=row.id)
            if clash:
                raise CatalogValidationError("EAN já cadastrado")
        row.ean = ean_n
        _mark_manual(row, "ean")
    if size_set:
        row.size = normalize_free_text(size)
        _mark_manual(row, "size")
    if color_set:
        row.color = normalize_free_text(color)
        _mark_manual(row, "color")
    if ncm_set:
        row.ncm = normalize_ncm(ncm)
        _mark_manual(row, "ncm")
    if country_of_origin_set:
        row.country_of_origin = normalize_country(country_of_origin)
        _mark_manual(row, "origin")
    if unit_set:
        row.unit = normalize_unit(unit)
        _mark_manual(row, "unit")
    if net_weight_kg_set:
        row.net_weight_kg = normalize_weight(net_weight_kg)

    if short_description is not _UNSET:
        text = str(short_description).strip() if short_description else None
        row.short_description = text or None
        _mark_manual(row, "short_description")
    if long_description is not _UNSET:
        text = str(long_description).strip() if long_description else None
        row.long_description = text or None
    if fiscal_description is not _UNSET:
        text = str(fiscal_description).strip() if fiscal_description else None
        row.fiscal_description = text or None
        _mark_manual(row, "fiscal_description")
    if supplier_sku is not _UNSET:
        row.supplier_sku = normalize_free_text(str(supplier_sku) if supplier_sku else None)

    old_type_id = row.product_type_id
    if category_id is not _UNSET:
        if category_id is None:
            row.category_id = None
        else:
            cat = repo.get_category(db, int(category_id))
            if not cat:
                raise CatalogValidationError("Categoria inválida")
            row.category_id = cat.id
        _mark_manual(row, "category")
    if product_type_id is not _UNSET:
        if product_type_id is None:
            row.product_type_id = None
        else:
            ptype = repo.get_product_type(db, int(product_type_id))
            if not ptype:
                raise CatalogValidationError("Tipo de produto inválido")
            row.product_type_id = ptype.id
        _mark_manual(row, "product_type")
        if old_type_id is not None and old_type_id != row.product_type_id:
            collected.append(TYPE_CHANGE_NOTICE)

    if subcategory is not _UNSET or category_id is not _UNSET:
        slug = None
        if row.category_id:
            cat = repo.get_category(db, row.category_id)
            slug = cat.slug if cat else None
        sub_val = row.subcategory if subcategory is _UNSET else (str(subcategory).strip() if subcategory else None)
        try:
            row.subcategory = validate_subcategory(slug, sub_val)
        except CatalogValidationError:
            if category_id is not _UNSET:
                row.subcategory = None
            else:
                raise
        _mark_manual(row, "subcategory")

    if attributes is not _UNSET:
        incoming = normalize_attributes(attributes)
        row.attributes = merge_attributes(row.attributes, incoming)
        for key in incoming:
            _mark_manual(row, key)

    if taxonomy_status is not _UNSET:
        status = str(taxonomy_status).strip() if taxonomy_status else None
        if status and status not in TAXONOMY_STATUSES:
            raise CatalogValidationError("Situação de classificação inválida")
        row.taxonomy_status = status
        _mark_manual(row, "taxonomy_status")
    if taxonomy_reason is not _UNSET:
        row.taxonomy_reason = str(taxonomy_reason).strip() if taxonomy_reason else None

    if lifecycle_status is not _UNSET:
        status = str(lifecycle_status).strip() if lifecycle_status else None
        if status and status not in LIFECYCLE_STATUSES:
            raise CatalogValidationError("Situação inválida")
        row.lifecycle_status = status
        if status == "ACTIVE":
            row.is_active = True
        elif status in ("DISCONTINUED", "UNKNOWN"):
            row.is_active = False

    db.flush()
    return get_product(db, row.id) or row
