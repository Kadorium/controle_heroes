from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: int
    document_key: str
    version: int
    is_current_version: bool
    file_hash: str
    original_filename: str
    mime_type: str | None
    size_bytes: int
    entity_type: str
    entity_id: str
    document_type: str | None
    created_at: datetime
    storage_path: str | None = None

    model_config = {"from_attributes": True}


class RawImportFileResponse(BaseModel):
    id: int
    file_hash: str
    original_filename: str
    source_system: str
    row_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StagingRowResponse(BaseModel):
    id: int
    raw_file_id: int
    row_number: int
    parsed_data_json: dict
    status: str
    review_reason: str | None
    merged_entity_id: str | None

    model_config = {"from_attributes": True}


class ReviewQueueResponse(BaseModel):
    id: int
    staging_row_id: int
    status: str
    reason: str
    priority: int
    created_at: datetime
    staging_row: StagingRowResponse | None = None

    model_config = {"from_attributes": True}


class HeroesMappingCreate(BaseModel):
    name: str
    column_mapping: dict[str, str]
    is_default: bool = False


class HeroesMappingResponse(BaseModel):
    id: int
    name: str
    column_mapping: dict[str, str]
    is_default: bool

    model_config = {"from_attributes": True}


class HeroesXlsxSheetInfo(BaseModel):
    sheet_name: str
    sheet_type: str
    order_number_hint: str | None = None
    order_number_from_content: str | None = None
    order_number_divergence: bool = False
    parser_confidence: float | None = None
    recommendation: str | None = None


class HeroesWorkbookProfileResponse(BaseModel):
    profiler_version: str
    source_file: str | None = None
    resolved_path: str | None = None
    file_checksum: str
    sheet_count: int
    sheets: list[dict]
    database_writes: bool = False
    read_only_mode: bool = True
    note: str | None = None


class HeroesXlsxUploadResponse(BaseModel):
    raw_file_id: int
    file_checksum: str
    sheets: list[HeroesXlsxSheetInfo]
    workbook_profile: HeroesWorkbookProfileResponse | None = None
    source_path: str | None = None


class HeroesWorkbookLocateResponse(BaseModel):
    found: bool
    resolved_path: str | None = None
    search_paths: list[str]


class HeroesXlsxPreviewRequest(BaseModel):
    raw_file_id: int
    sheet_name: str
    confirmed_order_number: str | None = None


class HeroesXlsxPreviewResponse(BaseModel):
    run_id: int
    status: str
    sheet_name: str
    sheet_type: str
    order_number: str | None
    order_number_from_sheet_name: str | None = None
    order_number_from_content: str | None = None
    order_number_divergence: bool = False
    review_required: bool = False
    preview: dict
    canonical: dict | None = None
    warnings: list[str] | None = None
    errors: list[str] | None = None
    already_committed: bool = False
    importation_id: int | None = None


class HeroesXlsxCommitRequest(BaseModel):
    run_id: int
    category_overrides: dict[str, str] | None = None
    confirmed_order_number: str | None = None
    confirm_sheet_match: bool = False
    confirm_import: bool = False


class HeroesXlsxExportRequest(BaseModel):
    run_id: int
    format: str = "xlsx"  # xlsx | zip


class HeroesXlsxCommitResponse(BaseModel):
    importation_id: int
    po_number: str
    run_id: int


class ShipmentCreate(BaseModel):
    importation_id: int
    shipment_number: str
    modal: str
    bl_number: str | None = None
    awb_number: str | None = None
    container_number: str | None = None
    etd_planned: date | None = None
    eta_planned: date | None = None
    freight_amount: Decimal | None = None
    freight_currency: str | None = None


class ShipmentItemCreate(BaseModel):
    importation_item_id: int
    quantity_shipped: int | None = None
    reason_code: str | None = None
    justification: str | None = None


class ModalChangeRequest(BaseModel):
    new_modal: str
    reason_code: str | None = None
    comment: str | None = None
    estimated_cost_impact: Decimal | None = None
    estimated_time_impact_days: int | None = None


class ShipmentResponse(BaseModel):
    id: int
    importation_id: int
    shipment_number: str
    modal: str
    modal_previous: str | None
    bl_number: str | None
    awb_number: str | None
    container_number: str | None
    status: str
    etd_planned: date | None = None
    eta_planned: date | None = None
    etd_actual: date | None = None
    eta_actual: date | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class ShipmentItemResponse(BaseModel):
    id: int
    shipment_id: int
    importation_item_id: int
    quantity_shipped: int | None

    model_config = {"from_attributes": True}


class ModalChangeLogResponse(BaseModel):
    id: int
    shipment_id: int
    from_modal: str
    to_modal: str
    comment: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class QuantitySummaryResponse(BaseModel):
    importation_item_id: int
    quantity_ordered: int | None
    quantity_shipped: int
    quantity_remaining: int | None
