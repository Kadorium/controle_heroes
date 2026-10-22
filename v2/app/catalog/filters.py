from dataclasses import dataclass


@dataclass
class ProductListFilters:
    q: str | None = None
    active_only: bool = False
    is_active: bool | None = None
    incomplete: bool = False
    missing_ncm: bool = False
    missing_image: bool = False
    needs_review: bool = False
    needs_classification_review: bool = False
    short_generic: bool = False
    quality_incomplete: bool = False
    category: str | None = None
    subcategory: str | None = None
    product_type: str | None = None
    sport: str | None = None
    collection_year: str | None = None
    color: str | None = None
    size: str | None = None
    origin: str | None = None
    unit: str | None = None
    ean: str | None = None
    supplier_sku: str | None = None
    model: str | None = None
    garment_kind: str | None = None
    gender: str | None = None
    source_kind: str | None = None
    sort: str | None = None
    limit: int = 50
    offset: int = 0
