"""Fachada pública Catalog — reexporta commands/queries."""

from app.catalog.commands import create_product, create_supplier, update_product, update_supplier
from app.catalog.errors import CatalogError, SupplierCodeDuplicate
from app.catalog.queries import (
    get_product,
    get_product_by_sku,
    get_supplier,
    get_supplier_by_code,
    get_suppliers_bulk,
    list_products,
    list_products_page,
    list_suppliers,
    list_suppliers_page,
    resolve_product,
)
from app.catalog.repository import distinct_product_values

__all__ = [
    "CatalogError",
    "SupplierCodeDuplicate",
    "create_supplier",
    "create_product",
    "update_supplier",
    "update_product",
    "get_supplier",
    "get_supplier_by_code",
    "get_suppliers_bulk",
    "list_suppliers",
    "list_suppliers_page",
    "get_product",
    "get_product_by_sku",
    "list_products",
    "list_products_page",
    "distinct_product_values",
    "resolve_product",
]
