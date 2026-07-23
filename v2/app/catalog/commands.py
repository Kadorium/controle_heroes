from sqlalchemy.orm import Session

from app.catalog import repository as repo
from app.catalog.errors import CatalogValidationError, SkuDuplicate, SupplierCodeDuplicate
from app.catalog.models import Product, Supplier


def create_supplier(
    db: Session,
    *,
    name: str,
    code: str | None = None,
    country_code: str | None = None,
    is_active: bool = True,
) -> Supplier:
    name = (name or "").strip()
    if not name:
        raise CatalogValidationError("Nome do fornecedor é obrigatório")
    code_norm = code.strip() if code and code.strip() else None
    country = country_code.strip().upper() if country_code and country_code.strip() else None
    if country is not None and len(country) != 2:
        raise CatalogValidationError("country_code deve ter 2 letras ISO")
    if code_norm and repo.get_supplier_by_code(db, code_norm):
        raise SupplierCodeDuplicate(code_norm)
    return repo.add_supplier(
        db,
        Supplier(name=name, code=code_norm, country_code=country, is_active=is_active),
    )


def create_product(
    db: Session,
    *,
    sku: str,
    description: str,
    is_active: bool = True,
) -> Product:
    sku_norm = (sku or "").strip()
    desc = (description or "").strip()
    if not sku_norm:
        raise CatalogValidationError("SKU é obrigatório")
    if not desc:
        raise CatalogValidationError("Descrição é obrigatória")
    if repo.get_product_by_sku(db, sku_norm):
        raise SkuDuplicate(sku_norm)
    return repo.add_product(db, Product(sku=sku_norm, description=desc, is_active=is_active))
