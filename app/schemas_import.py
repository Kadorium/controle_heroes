from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config import DEFAULT_IMPORT_CURRENCY
from app.core.currency import normalize_import_currency
from app.core.parse import optional_decimal, optional_int


def _currency_validator(v: Any) -> str:
    return normalize_import_currency(v if v is not None else DEFAULT_IMPORT_CURRENCY)


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    currency_default: str | None = DEFAULT_IMPORT_CURRENCY

    @field_validator("currency_default", mode="before")
    @classmethod
    def normalize_supplier_currency(cls, v: Any) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return DEFAULT_IMPORT_CURRENCY
        return normalize_import_currency(v)


class SupplierUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    currency_default: str | None = None

    @field_validator("currency_default", mode="before")
    @classmethod
    def normalize_supplier_currency(cls, v: Any) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return normalize_import_currency(v)


class SupplierResponse(BaseModel):
    id: int
    name: str
    country: str | None
    tax_id: str | None
    contact_name: str | None
    contact_email: str | None
    currency_default: str | None
    is_active: bool

    @field_validator("currency_default", mode="before")
    @classmethod
    def normalize_supplier_currency(cls, v: Any) -> str | None:
        if v is None:
            return None
        return normalize_import_currency(v)

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku_code: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=512)
    ncm: str | None = None
    weight_kg: Any = None
    volume_m3: Any = None
    category: str | None = "OTHER"

    @field_validator("weight_kg", "volume_m3", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class ProductUpdate(BaseModel):
    description: str | None = None
    ncm: str | None = None
    weight_kg: Any = None
    volume_m3: Any = None
    category: str | None = None

    @field_validator("weight_kg", "volume_m3", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class ProductResponse(BaseModel):
    id: int
    sku_code: str
    description: str
    ncm: str | None
    weight_kg: Decimal | None
    volume_m3: Decimal | None
    category: str
    is_active: bool

    model_config = {"from_attributes": True}


class ImportationItemCreate(BaseModel):
    product_id: int | None = None
    supplier_sku: str | None = None
    description: str | None = None
    quantity_ordered: Any = None
    unit_price_foreign: Any = None
    discount_amount_foreign: Any = None

    @field_validator("quantity_ordered", mode="before")
    @classmethod
    def parse_qty(cls, v: Any) -> int | None:
        return optional_int(v)

    @field_validator("unit_price_foreign", "discount_amount_foreign", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class ImportationCreate(BaseModel):
    po_number: str = Field(min_length=1, max_length=64)
    supplier_id: int
    currency: str = Field(default=DEFAULT_IMPORT_CURRENCY, min_length=3, max_length=8)
    incoterm: str | None = None
    estimated_total: Any = None
    items: list[ImportationItemCreate] = Field(default_factory=list)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: Any) -> str:
        return _currency_validator(v)

    @field_validator("estimated_total", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class ImportationResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    currency: str
    incoterm: str | None
    estimated_total: Decimal | None
    current_status: str
    brazil_operational_notes: str | None = None
    priority: str | None = None
    responsible: str | None = None
    internal_forecast_date: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: Any) -> str:
        return _currency_validator(v)

    model_config = {"from_attributes": True}


class ImportationItemResponse(BaseModel):
    id: int
    importation_id: int
    product_id: int | None
    supplier_sku: str | None
    description: str | None
    quantity_ordered: int | None
    unit_price_foreign: Decimal | None
    discount_amount_foreign: Decimal | None
    is_active: bool

    model_config = {"from_attributes": True}


class StatusTransitionRequest(BaseModel):
    new_status: str
    reason: str | None = None


class BrazilOperationalNotesUpdate(BaseModel):
    """Campos Brasil editáveis inline. Use exclude_unset para update parcial."""

    brazil_operational_notes: str | None = None
    priority: str | None = None
    responsible: str | None = None
    internal_forecast_date: date | None = None


class ImportationItemMappingUpdate(BaseModel):
    """Mapeamento Brasil de SKU/produto e descrição de um item da ordem."""

    product_id: int | None = None
    description: str | None = None
    supplier_sku: str | None = None


class AllowedTransitionItem(BaseModel):
    status: str
    blocked: bool
    block_reason: str | None = None


class AllowedTransitionsResponse(BaseModel):
    current_status: str
    transitions: list[AllowedTransitionItem]


class ItalyFieldOverrideRequest(BaseModel):
    entity_type: str = Field(pattern="^(invoice|invoice_item)$")
    entity_id: int
    field_name: str
    new_value: str
    reason: str = Field(min_length=3, max_length=512)
    attachment_id: int


class ItalyFieldOverrideResponse(BaseModel):
    entity_type: str
    entity_id: int
    field_name: str
    old_value: str | None
    new_value: str
    attachment_id: int


class InvoiceItemCreate(BaseModel):
    importation_item_id: int | None = None
    product_id: int | None = None
    quantity: Any = None
    unit_price: Any = None
    amount: Any = None

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_qty(cls, v: Any) -> int | None:
        return optional_int(v)

    @field_validator("unit_price", "amount", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class InvoiceCreate(BaseModel):
    importation_id: int
    invoice_type: str
    invoice_number: str
    invoice_date: date | None = None
    amount: Any = None
    currency: str = DEFAULT_IMPORT_CURRENCY
    discount_amount: Any = None
    expected_exchange_rate: Any = None
    notes: str | None = None
    items: list[InvoiceItemCreate] = Field(default_factory=list)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: Any) -> str:
        return _currency_validator(v)

    @field_validator("amount", "discount_amount", "expected_exchange_rate", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class InvoiceUpdate(BaseModel):
    invoice_type: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    amount: Any = None
    discount_amount: Any = None
    expected_exchange_rate: Any = None
    notes: str | None = None

    @field_validator("amount", "discount_amount", "expected_exchange_rate", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class InvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    quantity: int | None
    unit_price: Decimal | None
    amount: Decimal | None

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: int
    importation_id: int
    invoice_type: str
    invoice_number: str
    invoice_date: date | None
    amount: Decimal | None
    currency: str
    discount_amount: Decimal | None
    expected_exchange_rate: Decimal | None
    payment_status: str | None
    is_active: bool
    balance: Decimal | None = None
    paid_total: Decimal | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: Any) -> str:
        return _currency_validator(v)

    model_config = {"from_attributes": True}


class CancelRequest(BaseModel):
    reason: str = Field(min_length=3)


class PaymentCreate(BaseModel):
    invoice_id: int
    payment_type: str
    payment_date: date | None = None
    due_date: date | None = None
    amount_foreign: Any = None
    amount_local: Any = None
    currency_foreign: str | None = None
    exchange_rate: Any = None
    exchange_contract_number: str | None = None
    settlement_date: date | None = None
    bank_name: str | None = None
    receipt_reference: str | None = None
    approved_without_receipt: bool = False

    @field_validator("currency_foreign", mode="before")
    @classmethod
    def normalize_currency(cls, v: Any) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return normalize_import_currency(v)

    @field_validator("amount_foreign", "amount_local", "exchange_rate", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class PaymentUpdate(BaseModel):
    payment_date: date | None = None
    due_date: date | None = None
    amount_foreign: Any = None
    amount_local: Any = None
    exchange_rate: Any = None
    exchange_contract_number: str | None = None
    settlement_date: date | None = None
    bank_name: str | None = None
    receipt_reference: str | None = None
    approved_without_receipt: bool | None = None

    @field_validator("amount_foreign", "amount_local", "exchange_rate", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    payment_type: str
    payment_date: date | None
    due_date: date | None = None
    amount_foreign: Decimal | None
    amount_local: Decimal | None
    exchange_rate: Decimal | None
    currency_foreign: str | None = None
    receipt_reference: str | None = None
    exchange_contract_number: str | None = None
    settlement_date: date | None = None
    bank_name: str | None = None
    approved_without_receipt: bool = False
    is_active: bool

    model_config = {"from_attributes": True}


class ExchangeRateCreate(BaseModel):
    currency_from: str
    rate_type: str
    rate_value: Any = None
    importation_id: int | None = None
    invoice_id: int | None = None
    payment_id: int | None = None
    comment: str | None = None

    @field_validator("rate_value", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class ExchangeRateResponse(BaseModel):
    id: int
    currency_from: str
    currency_to: str
    rate_type: str
    rate_value: Decimal | None
    importation_id: int | None
    invoice_id: int | None
    payment_id: int | None

    model_config = {"from_attributes": True}


class DiscountCreate(BaseModel):
    invoice_id: int
    discount_type: str
    amount: Any = None
    currency: str
    reason: str | None = None
    source_document_ref: str | None = None
    importation_item_id: int | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class DiscountResponse(BaseModel):
    id: int
    invoice_id: int
    importation_item_id: int | None = None
    discount_type: str
    amount: Decimal | None
    currency: str
    reason: str | None
    source_document_ref: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class CreditCreate(BaseModel):
    supplier_id: int
    amount: Decimal
    currency: str
    credit_type: str | None = None
    origin_importation_id: int | None = None
    source_document_ref: str | None = None


class CreditApplyRequest(BaseModel):
    importation_id: int
    invoice_id: int | None = None
    amount: Decimal


class CreditResponse(BaseModel):
    id: int
    supplier_id: int
    amount: Decimal
    currency: str
    amount_used: Decimal
    amount_available: Decimal
    status: str
    is_active: bool

    model_config = {"from_attributes": True}


class BrazilAccountCreate(BaseModel):
    supplier_id: int
    description: str
    amount: Decimal
    currency: str = "BRL"
    financial_impact_estimated: Any = None
    fiscal_impact_estimated: Any = None
    origin_credit_id: int | None = None
    origin_importation_id: int | None = None
    source_document_ref: str | None = None

    @field_validator("financial_impact_estimated", "fiscal_impact_estimated", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class BrazilAccountResponse(BaseModel):
    id: int
    supplier_id: int
    description: str
    amount: Decimal
    currency: str
    amount_available: Decimal
    financial_impact_estimated: Decimal | None
    fiscal_impact_estimated: Decimal | None
    status: str
    is_active: bool

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    importation_id: int
    expense_type: str
    description: str | None = None
    amount: Any = None
    currency: str = "BRL"
    exchange_rate: Any = None
    amount_local: Any = None
    supplier_id: int | None = None
    source_document_ref: str | None = None
    is_included_in_landed_cost: bool = True

    @field_validator("amount", "exchange_rate", "amount_local", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal | None:
        return optional_decimal(v)


class ExpenseResponse(BaseModel):
    id: int
    importation_id: int
    expense_type: str
    description: str | None
    amount: Decimal | None
    currency: str
    source_document_ref: str | None = None
    is_included_in_landed_cost: bool = True
    is_active: bool

    model_config = {"from_attributes": True}


class FinancialSummaryResponse(BaseModel):
    importation_id: int
    currency: str
    total_invoiced: str | None = None
    total_paid: str | None = None
    total_discounts: str | None = None
    consolidated_balance: str | None = None
    invoices: list[dict]
