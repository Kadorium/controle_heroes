from pydantic import BaseModel, Field


class StageCount(BaseModel):
    label: str
    count: int


class DataAvailability(BaseModel):
    payments_due: bool = False
    eta: bool = False
    monthly_stock_trend: bool = False
    fx_rate: bool = False


class DashboardSummaryResponse(BaseModel):
    open_importations_count: int
    open_value_by_currency: dict[str, str | None] = Field(
        description="Saldo consolidado por moeda; null se alguma importação tem invoice sem valor"
    )
    divergence_importations_count: int
    divergence_reconciliations_count: int
    stocked_units_total: int
    review_queue_count: int
    stage_counts: list[StageCount]
    closure_pending_importations_count: int
    payments_due_count: int = 0
    payments_overdue_count: int = 0
    payments_due_amount_by_currency: dict[str, str] = Field(default_factory=dict)
    payments_due_window_days: int = 7
    data_availability: DataAvailability


class DashboardActionItem(BaseModel):
    kind: str
    label: str
    detail: str
    tone: str


class DashboardPendingPayment(BaseModel):
    payment_id: int | None = None
    invoice_id: int
    invoice_number: str
    invoice_type: str
    balance: str | None
    currency: str
    due_date: str | None = None
    is_overdue: bool = False


class DashboardImportationRow(BaseModel):
    id: int
    po_number: str
    status: str
    supplier_name: str
    currency: str
    created_at: str
    modal: str | None
    stage_index: int
    in_transit: bool
    open_value: str | None
    stocked_qty: int
    has_divergence: bool
    divergence_count: int
    lc_estimated: str | None
    lc_actual: str | None
    eta: str | None
    closure_pending_count: int
    action_items: list[DashboardActionItem]
    pending_payments: list[DashboardPendingPayment]


class DashboardImportationsResponse(BaseModel):
    items: list[DashboardImportationRow]
    total_open: int
