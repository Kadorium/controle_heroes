from decimal import Decimal
from enum import Enum


class InvoiceType(str, Enum):
    ANTECIPO = "ANTECIPO"
    PROFORMA = "PROFORMA"
    SALDO = "SALDO"
    COMPLEMENTAR = "COMPLEMENTAR"
    AJUSTE = "AJUSTE"
    CREDITO = "CREDITO"
    OUTRA = "OUTRA"


class PaymentType(str, Enum):
    ADVANCE = "ADVANCE"
    PARTIAL = "PARTIAL"
    FINAL = "FINAL"
    ADJUSTMENT = "ADJUSTMENT"


class ExchangeRateType(str, Enum):
    ESTIMATED = "ESTIMATED"
    REVISED = "REVISED"
    SETTLED = "SETTLED"


class DiscountType(str, Enum):
    ITEM = "ITEM"
    GLOBAL = "GLOBAL"


class CreditStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    USED = "USED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class ExpenseType(str, Enum):
    FREIGHT = "FREIGHT"
    INSURANCE = "INSURANCE"
    STORAGE = "STORAGE"
    CUSTOMS_AGENT = "CUSTOMS_AGENT"
    BANK_FEE = "BANK_FEE"
    LOCAL_TRANSPORT = "LOCAL_TRANSPORT"
    OTHER = "OTHER"


# Transições básicas Fase 3
IMPORTATION_TRANSITIONS: dict[str, list[str]] = {
    "PO_CREATED": ["PROFORMA_RECEIVED", "ON_HOLD", "CANCELLED"],
    "PROFORMA_RECEIVED": ["ADVANCE_PAID", "PARTIAL_PAID", "BOOKED", "ON_HOLD", "CANCELLED"],
    "ADVANCE_PAID": ["PARTIAL_PAID", "BOOKED", "ON_HOLD"],
    "PARTIAL_PAID": ["FULL_PAID", "BOOKED", "ON_HOLD"],
    "FULL_PAID": ["BOOKED", "ON_HOLD"],
    "ON_HOLD": ["PO_CREATED", "PROFORMA_RECEIVED", "CANCELLED"],
    "BOOKED": ["SHIPPED", "ON_HOLD"],
    "SHIPPED": ["IN_TRANSIT", "ON_HOLD"],
    "IN_TRANSIT": ["ARRIVED", "ON_HOLD"],
    "CANCELLED": [],
}


class ShipmentModal(str, Enum):
    AIR = "AIR"
    OCEAN = "OCEAN"
    OTHER = "OTHER"


class StagingRowStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MERGED = "MERGED"


class ReviewQueueStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class SourceSystem(str, Enum):
    HEROES_SPREADSHEET = "HEROES_SPREADSHEET"
    HEROES_XLSX = "HEROES_XLSX"


class ProductCategory(str, Enum):
    RACKET = "RACKET"
    BALL = "BALL"
    BAG_ACCESSORY = "BAG_ACCESSORY"
    APPAREL = "APPAREL"
    PICKLEBALL = "PICKLEBALL"
    OTHER = "OTHER"


class HeroesSheetType(str, Enum):
    ORDER = "ORDER"
    FINANCIAL_ANNUAL = "FINANCIAL_ANNUAL"
    LOGISTICS = "LOGISTICS"
    RECEIPT_AGGREGATE = "RECEIPT_AGGREGATE"
    FUTURE_PLANNING = "FUTURE_PLANNING"
    UNKNOWN = "UNKNOWN"


class HeroesImportRunStatus(str, Enum):
    PREVIEW = "PREVIEW"
    COMMITTED = "COMMITTED"
    SUPERSEDED = "SUPERSEDED"
    FAILED = "FAILED"


HEROES_XLSX_PARSER_VERSION = "1.1.0"


DEFAULT_HEROES_COLUMN_MAPPING: dict[str, str] = {
    "po_number": "PO",
    "sku": "SKU",
    "description": "Description",
    "quantity": "Qty",
    "unit_price": "UnitPrice",
    "supplier": "Supplier",
}


# Documentos exigidos para transições (F5-010)
TRANSITION_REQUIRED_DOCUMENTS: dict[str, list[str]] = {
    "PROFORMA_RECEIVED": ["PROFORMA"],
    "BOOKED": ["BL", "AWB"],
}


class CustomsDocumentType(str, Enum):
    DI = "DI"
    DUIMP = "DUIMP"


class CustomsDocumentStatus(str, Enum):
    STAGING = "STAGING"
    OFFICIAL = "OFFICIAL"
    CANCELLED = "CANCELLED"


class TaxType(str, Enum):
    II = "II"
    IPI = "IPI"
    PIS = "PIS"
    COFINS = "COFINS"
    ICMS = "ICMS"
    OTHER = "OTHER"


class LandedCostVersionType(str, Enum):
    INITIAL = "INITIAL"
    REVISED = "REVISED"
    PRELIMINARY = "PRELIMINARY"
    FINAL = "FINAL"
    FINAL_REOPENED = "FINAL_REOPENED"


class LandedCostComponentType(str, Enum):
    FOB = "FOB"
    DISCOUNT = "DISCOUNT"
    CREDIT = "CREDIT"
    FREIGHT = "FREIGHT"
    INSURANCE = "INSURANCE"
    TAX = "TAX"
    BRAZIL_EXPENSE = "BRAZIL_EXPENSE"
    CUSTOMS_AGENT = "CUSTOMS_AGENT"
    BANK_FEE = "BANK_FEE"
    STORAGE = "STORAGE"
    FX_DIFF = "FX_DIFF"
    OTHER = "OTHER"


class AllocationMethod(str, Enum):
    VALUE = "VALUE"
    QUANTITY = "QUANTITY"
    WEIGHT = "WEIGHT"
    VOLUME = "VOLUME"
    EQUAL = "EQUAL"
    MANUAL = "MANUAL"


class ReconciliationPairType(str, Enum):
    INVOICE_PAYMENT = "INVOICE_PAYMENT"
    PAYMENT_EXCHANGE = "PAYMENT_EXCHANGE"
    INVOICE_ORDER = "INVOICE_ORDER"
    HEROES_INVOICE = "HEROES_INVOICE"
    CUSTOMS_EXPENSE = "CUSTOMS_EXPENSE"
    TAX_CALC_PAID = "TAX_CALC_PAID"
    QTY_CHAIN = "QTY_CHAIN"
    COST_ESTIMATED_ACTUAL = "COST_ESTIMATED_ACTUAL"
    LC_PRELIM_FINAL = "LC_PRELIM_FINAL"
    DISCOUNT_APPLIED = "DISCOUNT_APPLIED"
    CREDIT_USED = "CREDIT_USED"


class ReconciliationStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    DIVERGENT = "DIVERGENT"
    APPROVED = "APPROVED"
    PENDING = "PENDING"


class ClosureType(str, Enum):
    CLEAN = "CLEAN"
    WITH_APPROVED_VARIANCE = "WITH_APPROVED_VARIANCE"


class ClosureStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REOPENED = "REOPENED"


# Tolerâncias MVP — revisar com financeiro (L-001)
RECONCILIATION_TOLERANCE_AMOUNT = Decimal("10.00")
RECONCILIATION_TOLERANCE_PCT = Decimal("0.01")
RECONCILIATION_TOLERANCE_EXCHANGE = Decimal("0.05")
