from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CustomsDocumentCreate(BaseModel):
    importation_id: int
    document_type: str
    document_number: str
    document_data_json: dict | None = None
    attachment_id: int | None = None


class CustomsDocumentApprove(BaseModel):
    official_data_json: dict


class CustomsDocumentResponse(BaseModel):
    id: int
    importation_id: int
    document_type: str
    document_number: str
    document_data_json: dict | None
    official_data_json: dict | None
    status: str
    is_valid: bool

    model_config = {"from_attributes": True}


class TaxCreate(BaseModel):
    importation_id: int
    customs_document_id: int
    tax_type: str
    amount: Decimal
    source_document_attachment_id: int
    currency: str = "BRL"
    notes: str | None = None


class TaxResponse(BaseModel):
    id: int
    importation_id: int
    customs_document_id: int
    tax_type: str
    amount: Decimal
    currency: str

    model_config = {"from_attributes": True}


class NationalizationItemCreate(BaseModel):
    importation_item_id: int
    quantity_nationalized: int


class NationalizationCreate(BaseModel):
    importation_id: int
    customs_document_id: int
    items: list[NationalizationItemCreate]
    event_date: date | None = None
    notes: str | None = None


class NationalizationResponse(BaseModel):
    id: int
    importation_id: int
    customs_document_id: int
    event_date: date | None

    model_config = {"from_attributes": True}


class StockEntryCreate(BaseModel):
    nationalization_id: int
    importation_item_id: int
    quantity_received: int
    unit_cost_approved: Decimal | None = None
    landed_cost_version_id: int | None = None
    reason_code: str | None = None
    justification: str | None = None


class StockEntryResponse(BaseModel):
    id: int
    nationalization_id: int
    importation_item_id: int
    quantity_received: int
    unit_cost_approved: Decimal | None

    model_config = {"from_attributes": True}


class QuantityDiscrepancyCreate(BaseModel):
    importation_id: int
    importation_item_id: int | None = None
    stage_from: str
    stage_to: str
    expected_quantity: int | None = None
    actual_quantity: int | None = None
    reason: str | None = None


class QuantityChainResponse(BaseModel):
    importation_item_id: int
    quantity_ordered: int | None
    quantity_shipped: int | None = None
    quantity_nationalized: int | None = None
    quantity_stocked: int | None = None
    difference_ordered_stocked: int | None


class LandedCostCreate(BaseModel):
    importation_id: int
    version_type: str = "INITIAL"
    allocation_method: str = "VALUE"
    trigger_event: str | None = None
    trigger_notes: str | None = None
    manual_allocations: dict[int, Decimal] | None = None
    reason_code: str | None = None
    justification: str | None = None


class LandedCostComponentResponse(BaseModel):
    id: int
    component_type: str
    amount: Decimal
    source_ref: str | None

    model_config = {"from_attributes": True}


class LandedCostAllocationResponse(BaseModel):
    id: int
    importation_item_id: int
    allocation_method: str
    allocated_amount: Decimal
    unit_cost: Decimal | None

    model_config = {"from_attributes": True}


class LandedCostVersionResponse(BaseModel):
    id: int
    importation_id: int
    version_number: int
    version_type: str
    is_current_version: bool
    previous_version_id: int | None
    total_cost: Decimal | None
    trigger_event: str | None
    created_at: datetime
    components: list[LandedCostComponentResponse] = []
    allocations: list[LandedCostAllocationResponse] = []

    model_config = {"from_attributes": True}
