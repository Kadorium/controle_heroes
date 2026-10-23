from typing import Any
from pydantic import BaseModel

class VersionSource(BaseModel):
    id: int
    number: int
    kind: str
    status: str
    partial_coverage: bool
    invoices: list[dict[str, Any]]
    product: dict[str, Any] | None

class ProductSource(BaseModel):
    case_id: int
    process_id: int
    code: str
    reference: str | None
    current_published_id: int | None
    purchases: list[dict[str, Any]]
    versions: list[VersionSource]

class ProductSourcesResponse(BaseModel):
    product_id: int
    total: int
    limit: int
    offset: int
    rows: list[ProductSource]

class SourceDocument(BaseModel):
    id: int
    name: str
    mime_type: str | None

class ProductComponent(BaseModel):
    id: int
    type: str
    included: bool
    product_brl: str | None
    process_brl: str | None
    source_kind: str
    source_id: int | None
    documents: list[SourceDocument]
    document_state: str

class ProductVersionResponse(BaseModel):
    product_id: int
    case_id: int
    version_id: int
    number: int
    kind: str
    status: str
    current_published_id: int | None
    partial_coverage: bool
    product: dict[str, Any] | None
    fx: dict[str, Any]
    coverage: dict[str, Any]
    components: list[ProductComponent]
    basis: str
    tax_basis: str
