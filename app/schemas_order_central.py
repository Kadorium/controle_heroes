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
    totals_by_currency: dict[str, CurrencyTotals] | None = None


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
    model_label: str | None = None
    quantity_ordered: int | None = None
    quantity_shipped: int | None = None
    quantity_nationalized: int | None = None
    quantity_stocked: int | None = None
    quantity_invoiced: int | None = None
    to_dispatch: int | None = None


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


class OrderCentralResponse(BaseModel):
    order: ImportationResponse
    supplier_name: str | None = None
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
    pending_actions_count: int = 0
    updated_at: datetime | None = None
    created_at: datetime


class OrderQueueResponse(BaseModel):
    items: list[OrderQueueRow] = Field(default_factory=list)
    total: int = 0
