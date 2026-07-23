from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ReconciliationResponse(BaseModel):
    id: int
    importation_id: int
    pair_type: str
    label: str
    source_a_label: str | None
    source_a_value: str | None
    source_b_label: str | None
    source_b_value: str | None
    variance_value: Decimal | None
    tolerance_value: Decimal | None
    status: str
    severity: str
    entity_ref: str | None
    details_json: dict | None = None

    model_config = {"from_attributes": True}


class ReconciliationApprove(BaseModel):
    reason_code: str | None = None
    justification: str | None = None


class CloseChecklistItem(BaseModel):
    id: str
    label: str
    passed: bool
    blocking_count: int | None = None


class CloseImportationRequest(BaseModel):
    landed_cost_version_id: int | None = None
    approved_reconciliation_ids: list[int] | None = None
    reason_code: str | None = None
    justification: str | None = None


class ReopenImportationRequest(BaseModel):
    reason_code: str
    justification: str | None = None


class ClosureResponse(BaseModel):
    id: int
    importation_id: int
    closure_version: int
    landed_cost_version_id: int | None
    closure_type: str
    status: str
    closed_at: datetime
    snapshot_json: dict

    model_config = {"from_attributes": True}


class TimelineEvent(BaseModel):
    type: str
    timestamp: str
    action: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    comment: str | None = None
    entity_type: str | None = None
    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
