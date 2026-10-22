from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str
    code: str | None = None
    country_code: str | None = None
    is_active: bool = True
    tax_id: str | None = None


class SupplierPatch(BaseModel):
    name: str | None = None
    code: str | None = None
    country_code: str | None = None
    is_active: bool | None = None
    tax_id: str | None = None


class SupplierResponse(BaseModel):
    id: int
    code: str | None
    name: str
    country_code: str | None
    is_active: bool
    tax_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str
    description: str
    is_active: bool = True


class ProductPatch(BaseModel):
    description: str | None = None
    commercial_name: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    fiscal_description: str | None = None
    is_active: bool | None = None
    ean: str | None = None
    size: str | None = None
    color: str | None = None
    ncm: str | None = None
    country_of_origin: str | None = None
    unit: str | None = None
    net_weight_kg: Decimal | None = None
    supplier_sku: str | None = None
    category_id: int | None = None
    product_type_id: int | None = None
    subcategory: str | None = None
    attributes: dict[str, Any] | None = None
    taxonomy_status: str | None = None
    taxonomy_reason: str | None = None
    lifecycle_status: str | None = None


class QualityItem(BaseModel):
    code: str
    layer: str
    ok: bool
    label: str
    consequence: str


class QualityPayload(BaseModel):
    essential_ok: bool = False
    operation_ok: bool = False
    commercial_ok: bool = False
    pending_count: int = 0
    summary: str = ""
    items: list[QualityItem] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list)
    quality_incomplete: bool = False
    needs_review: bool = False
    needs_product_review: bool = False
    needs_classification_review: bool = False
    short_generic: bool = False
    missing_image: bool = True
    missing_ncm: bool = True
    incomplete_mdm: bool = True


class ProvenanceEntry(BaseModel):
    field: str
    label: str
    source: str
    source_label: str


class ProductResponse(BaseModel):
    id: int
    sku: str
    description: str
    commercial_name: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    fiscal_description: str | None = None
    is_active: bool
    lifecycle_status: str | None = None
    ean: str | None = None
    size: str | None = None
    color: str | None = None
    ncm: str | None = None
    country_of_origin: str | None = None
    unit: str | None = None
    net_weight_kg: Decimal | None = None
    supplier_sku: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    category_slug: str | None = None
    subcategory: str | None = None
    product_type_id: int | None = None
    product_type_name: str | None = None
    product_type_slug: str | None = None
    taxonomy_status: str | None = None
    taxonomy_reason: str | None = None
    import_decision: str | None = None
    short_generic: bool = False
    needs_review: bool = False
    needs_product_review: bool = False
    needs_classification_review: bool = False
    classification_note: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    sport: str | None = None
    line: str | None = None
    model: str | None = None
    collection_year: str | None = None
    garment_kind: str | None = None
    gender: str | None = None
    pack_qty: str | None = None
    source_kind: str | None = None
    import_batch_id: int | None = None
    has_image: bool = False
    quality: QualityPayload | None = None
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductListSummary(BaseModel):
    total: int
    incomplete: int
    missing_ncm: int
    needs_review: int = 0
    needs_product_review: int = 0
    needs_classification_review: int = 0
    short_generic: int = 0
    missing_image: int = 0
    quality_incomplete: int = 0


class FacetValue(BaseModel):
    value: str
    count: int
    label: str | None = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
    summary: ProductListSummary
    facets: dict[str, list[FacetValue]] = Field(default_factory=dict)


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int
    limit: int
    offset: int


class AttributeValuesResponse(BaseModel):
    field: str
    values: list[str]


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    subcategories: list[str] = Field(default_factory=list)


class ProductTypeResponse(BaseModel):
    id: int
    name: str
    slug: str
    recommended_attributes: list[str] = Field(default_factory=list)


class TaxonomyResponse(BaseModel):
    categories: list[CategoryResponse]
    product_types: list[ProductTypeResponse]
