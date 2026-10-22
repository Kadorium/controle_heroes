"""Fachada pública Catalog — reexporta commands/queries."""

from app.catalog.commands import create_product, create_supplier, update_product, update_supplier
from app.catalog.errors import CatalogError, SupplierCodeDuplicate
from app.catalog.filters import ProductListFilters
from app.catalog.heroes_import import commit_heroes_batch, preview_heroes_batch
from app.catalog.queries import (
    get_product,
    get_product_by_ean,
    get_product_by_sku,
    get_products_bulk,
    get_supplier,
    get_supplier_by_code,
    get_suppliers_bulk,
    list_products,
    list_products_page,
    list_products_report,
    list_suppliers,
    list_suppliers_page,
    lookup_product_by_sku_or_ean,
    resolve_product,
    taxonomy_catalog,
    exceptions,
)
from app.catalog.repository import distinct_product_values, product_facets, product_list_summary
from app.catalog.taxonomy import ensure_taxonomy

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
    "get_product_by_ean",
    "lookup_product_by_sku_or_ean",
    "get_products_bulk",
    "list_products",
    "list_products_page",
    "list_products_report",
    "distinct_product_values",
    "product_list_summary",
    "product_facets",
    "resolve_product",
    "taxonomy_catalog",
    "exceptions",
    "ensure_taxonomy",
    "ProductListFilters",
    "commit_heroes_batch",
    "preview_heroes_batch",
]
