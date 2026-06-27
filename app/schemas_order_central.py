"""Schemas agregados — central da ordem e fila operacional (Fase 6)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas_import import (
    BrazilAccountResponse,
    CreditResponse,
    DiscountResponse,
    ImportationResponse,
    PaymentResponse,
)


class CurrencyTotals(BaseModel):
    total_invoiced: str | None = None
    total_paid: str | None = None
    total_discounts: str | None = None
    consolidated_balance: str | None = None


class OrderCentralKpis(BaseModel):
    currency: str
    total_invoiced: str | None = None
    total_paid: str | None = None
    consolidated_balance: str | None = None
    to_dispatch: int | None = None
    versato_heroes: str | None = None
    versato_heroes_currency: str | None = None
    totals_by_currency: dict[str, CurrencyTotals] | None = None


class LegacySheetSummary(BaseModel):
    versato_amount: str | None = None
    versato_currency: str | None = None
    versato_source: str | None = None
    versato_confidence: float | None = None
    sheet_name: str | None = None
    source: str = "planilha Heroes"


class DispatchPendingItem(BaseModel):
    id: int
    product_name_raw: str
    product_id: int | None = None
    product_category_suggested: str | None = None
    quantity_to_dispatch: int | None = None
    price_listino: str | None = None
    price_fattura: str | None = None
    discount_unit: str | None = None
    acconto_amount: str | None = None
    credit_remaining: str | None = None
    currency: str
    source_sheet: str
    source_row: int | None = None
    needs_review: bool = False
    heroes_source: bool = True


class StatusRailStage(BaseModel):
    key: str
    label: str
    state: str
    data_supported: bool
    status_declared: bool
    subtitle: str | None = None


class StatusRail(BaseModel):
    stages: list[StatusRailStage] = Field(default_factory=list)
    current_index: int = 0
    alerts: list[str] = Field(default_factory=list)


class OrderCentralInvoiceItem(BaseModel):
    id: int
    importation_item_id: int | None = None
    product_id: int | None = None
    product_sku: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class OrderCentralInvoice(BaseModel):
    id: int
    invoice_type: str
    invoice_number: str
    invoice_date: date | None = None
    payment_due_date: date | None = None
    amount: Decimal | None = None
    currency: str
    discount_amount: Decimal | None = None
    balance: Decimal | None = None
    paid_total: Decimal | None = None
    items: list[OrderCentralInvoiceItem] = Field(default_factory=list)


class OrderCentralModel(BaseModel):
    importation_item_id: int
    product_id: int | None = None
    supplier_sku: str | None = None
    description: str | None = None
    product_sku: str | None = None
    product_category: str | None = None
    model_label: str | None = None
    quantity_ordered: int | None = None
    quantity_shipped: int | None = None
    quantity_nationalized: int | None = None
    quantity_stocked: int | None = None
    quantity_invoiced: int | None = None
    to_dispatch: int | None = None
    price_listino: str | None = None
    price_fattura: str | None = None
    discount_unit: str | None = None
    acconto_amount: str | None = None
    credit_remaining: str | None = None
    heroes_source: bool = False
    dispatch_needs_review: bool = False


class OrderCentralPayment(PaymentResponse):
    is_settled: bool = False
    invoice_number: str | None = None
    invoice_type: str | None = None


class OrderCentralShipment(BaseModel):
    id: int
    importation_id: int
    shipment_number: str
    modal: str
    modal_previous: str | None = None
    bl_number: str | None = None
    awb_number: str | None = None
    container_number: str | None = None
    status: str
    etd_planned: date | None = None
    eta_planned: date | None = None
    etd_actual: date | None = None
    eta_actual: date | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class PendingAction(BaseModel):
    kind: str
    label: str
    detail: str | None = None
    tone: str = "warning"


class FxPnlBlock(BaseModel):
    label: str = "PnL Cambial"
    disclaimer: str = "Variação cambial operacional vs provisão — não é resultado contábil."
    provision_rate: str | None = None
    mark_rate: str | None = None
    pnl_realized_brl: str | None = None
    pnl_planned_brl: str | None = None
    pnl_unrealized_brl: str | None = None
    pnl_total_brl: str | None = None


class OperationalHeader(BaseModel):
    invoices_count: int = 0
    invoices_settled_count: int = 0
    totals_by_currency: dict[str, CurrencyTotals] | None = None
    total_invoiced: str | None = None
    total_paid: str | None = None
    open_balance: str | None = None
    open_balance_brl_equivalent: str | None = None
    next_due_date: date | None = None
    overdue_count: int = 0
    overdue_amount_foreign: str | None = None
    next_open_invoice_number: str | None = None
    next_open_invoice_balance: str | None = None
    next_etd: date | None = None
    next_eta: date | None = None
    active_modal: str | None = None
    to_dispatch: int | None = None
    quantity_ordered: int | None = None
    supplier_credit_available: str | None = None
    pending_actions_count: int = 0
    fx_pnl: FxPnlBlock | None = None
    order_total_eur: str | None = None
    order_total_brl: str | None = None
    invoiced_eur: str | None = None
    invoiced_brl: str | None = None
    settled_eur: str | None = None
    settled_brl: str | None = None
    remaining_to_invoice_eur: str | None = None
    remaining_to_invoice_brl: str | None = None
    balance_to_settle_eur: str | None = None
    balance_to_settle_brl: str | None = None
    opening_exchange_rate: str | None = None


class OrderCentralResponse(BaseModel):
    order: ImportationResponse
    supplier_name: str | None = None
    legacy_sheet_summary: LegacySheetSummary | None = None
    dispatch_pending: list[DispatchPendingItem] = Field(default_factory=list)
    status_rail: StatusRail | None = None
    operational_header: OperationalHeader
    kpis: OrderCentralKpis
    invoices: list[OrderCentralInvoice] = Field(default_factory=list)
    models: list[OrderCentralModel] = Field(default_factory=list)
    payments_planned: list[OrderCentralPayment] = Field(default_factory=list)
    payments_settled: list[OrderCentralPayment] = Field(default_factory=list)
    discounts: list[DiscountResponse] = Field(default_factory=list)
    supplier_credits: list[CreditResponse] = Field(default_factory=list)
    brazil_accounts: list[BrazilAccountResponse] = Field(default_factory=list)
    shipments: list[OrderCentralShipment] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)


class OrderQueueRow(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    supplier_name: str | None = None
    status: str
    currency: str
    total_invoiced: str | None = None
    total_paid: str | None = None
    consolidated_balance: str | None = None
    totals_by_currency: dict[str, CurrencyTotals] | None = None
    to_dispatch: int | None = None
    qty_ordered: int | None = None
    qty_invoiced: int | None = None
    qty_shipped: int | None = None
    products_count: int = 0
    invoices_count: int = 0
    invoices_settled_count: int = 0
    docs_pending_count: int = 0
    next_due_date: date | None = None
    overdue_count: int = 0
    priority: str | None = None
    responsible: str | None = None
    internal_forecast_date: date | None = None
    brazil_operational_notes: str | None = None
    pending_actions_count: int = 0
    updated_at: datetime | None = None
    created_at: datetime


class OrderQueueResponse(BaseModel):
    items: list[OrderQueueRow] = Field(default_factory=list)
    total: int = 0
