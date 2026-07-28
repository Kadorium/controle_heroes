"""Fachada pública Catalog — reexporta commands/queries."""

from app.catalog.commands import create_product, create_supplier
from app.catalog.errors import CatalogError
from app.catalog.queries import (
    get_product,
    get_product_by_sku,
    get_supplier,
    get_suppliers_bulk,
    list_products,
    list_suppliers,
    resolve_product,
)

__all__ = [
    "CatalogError",
    "create_supplier",
    "create_product",
    "get_supplier",
    "get_suppliers_bulk",
    "list_suppliers",
    "get_product",
    "get_product_by_sku",
    "list_products",
    "resolve_product",
]
