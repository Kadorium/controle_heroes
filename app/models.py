from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permissions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped["Role"] = relationship(back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


class ReasonCode(Base, TimestampMixin):
    __tablename__ = "reason_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_comment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    field_changed: Mapped[str | None] = mapped_column(String(128), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    impact_estimate: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_or_machine_info: Mapped[str | None] = mapped_column(String(255), nullable=True)


class TechnicalLog(Base):
    __tablename__ = "technical_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="ERROR")
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class StatusTransitionLog(Base):
    __tablename__ = "status_transition_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocking_checks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attachment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency_default: Mapped[str | None] = mapped_column(String(8), nullable=True)

    importations: Mapped[list["ImportationOrder"]] = relationship(back_populates="supplier")
    credits: Mapped[list["Credit"]] = relationship(back_populates="supplier")


class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    ncm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="OTHER")
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    product_group: Mapped[str] = mapped_column(String(64), nullable=False, default="Sem grupo")
    product_subgroup: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(8), nullable=True)
    unit_of_measure: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fiscal_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    fiscal_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    launch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    commercial_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    default_supplier: Mapped["Supplier | None"] = relationship(foreign_keys=[default_supplier_id])


class ImportationOrder(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "importation_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    incoterm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    estimated_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    current_status: Mapped[str] = mapped_column(String(64), nullable=False, default="PO_CREATED")
    brazil_operational_notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    responsible: Mapped[str | None] = mapped_column(String(128), nullable=True)
    internal_forecast_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="importations")
    items: Mapped[list["ImportationItem"]] = relationship(back_populates="importation")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="importation")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="importation")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="importation")
    customs_documents: Mapped[list["CustomsDocument"]] = relationship(back_populates="importation")
    taxes: Mapped[list["Tax"]] = relationship(back_populates="importation")
    nationalizations: Mapped[list["Nationalization"]] = relationship(back_populates="importation")
    entreposto_movements: Mapped[list["EntrepostoMovement"]] = relationship(back_populates="importation")
    landed_cost_versions: Mapped[list["LandedCostVersion"]] = relationship(back_populates="importation")
    reconciliations: Mapped[list["Reconciliation"]] = relationship(back_populates="importation")
    closures: Mapped[list["ImportationClosure"]] = relationship(back_populates="importation")


class ImportationItem(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "importation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    supplier_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    quantity_ordered: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price_foreign: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    discount_amount_foreign: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()


class Invoice(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    invoice_type: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")
    discounts: Mapped[list["Discount"]] = relationship(back_populates="invoice")


class InvoiceItem(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    importation_item_id: Mapped[int | None] = mapped_column(ForeignKey("importation_items.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")


class Payment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    payment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_foreign: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount_local: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency_foreign: Mapped[str | None] = mapped_column(String(8), nullable=True)
    currency_local: Mapped[str | None] = mapped_column(String(8), nullable=True, default="BRL")
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    exchange_contract_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    settlement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receipt_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_without_receipt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")


class ExchangeRate(Base, TimestampMixin):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency_from: Mapped[str] = mapped_column(String(8), nullable=False)
    currency_to: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rate_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    importation_id: Mapped[int | None] = mapped_column(ForeignKey("importation_orders.id"), nullable=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    registered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Discount(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    importation_item_id: Mapped[int | None] = mapped_column(ForeignKey("importation_items.id"), nullable=True)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="discounts")


class Credit(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "credits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    origin_importation_id: Mapped[int | None] = mapped_column(ForeignKey("importation_orders.id"), nullable=True)
    credit_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount_used: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    amount_available: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    used_in_importation_id: Mapped[int | None] = mapped_column(ForeignKey("importation_orders.id"), nullable=True)
    source_document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="credits")
    usages: Mapped[list["CreditUsage"]] = relationship(back_populates="credit")


class CreditUsage(Base):
    __tablename__ = "credit_usages"
    __table_args__ = (UniqueConstraint("credit_id", "importation_id", "invoice_id", name="uq_credit_usage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("credits.id"), nullable=False, index=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    amount_used: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    used_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    credit: Mapped["Credit"] = relationship(back_populates="usages")


class BrazilCurrentAccount(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "brazil_current_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    origin_credit_id: Mapped[int | None] = mapped_column(ForeignKey("credits.id"), nullable=True)
    origin_importation_id: Mapped[int | None] = mapped_column(ForeignKey("importation_orders.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    amount_used: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    amount_available: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    financial_impact_estimated: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fiscal_impact_estimated: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    source_document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Expense(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    expense_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    amount_local: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    source_document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_included_in_landed_cost: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="expenses")


class DocumentAttachment(Base, TimestampMixin):
    __tablename__ = "document_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current_version: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RawImportFile(Base, TimestampMixin):
    __tablename__ = "raw_import_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class StagingImportRow(Base, TimestampMixin):
    __tablename__ = "staging_import_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_file_id: Mapped[int] = mapped_column(ForeignKey("raw_import_files.id"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parsed_data_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW")
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    merged_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merged_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewQueueItem(Base, TimestampMixin):
    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    staging_row_id: Mapped[int] = mapped_column(ForeignKey("staging_import_rows.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class HeroesImportMapping(Base, TimestampMixin):
    __tablename__ = "heroes_import_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    column_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class HeroesImportRun(Base, TimestampMixin):
    __tablename__ = "heroes_import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_file_id: Mapped[int | None] = mapped_column(ForeignKey("raw_import_files.id"), nullable=True)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sheet_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(16), nullable=False)
    order_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PREVIEW")
    preview_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    errors_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    importation_id: Mapped[int | None] = mapped_column(ForeignKey("importation_orders.id"), nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_order_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class HeroesLegacySheetSummary(Base, TimestampMixin):
    __tablename__ = "heroes_legacy_sheet_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    heroes_import_run_id: Mapped[int] = mapped_column(ForeignKey("heroes_import_runs.id"), nullable=False, index=True)
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    versato_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    versato_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    versato_source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    versato_source_cell: Mapped[str | None] = mapped_column(String(16), nullable=True)
    versato_raw_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    versato_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    parser_version: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class HeroesDispatchPendingItem(Base, TimestampMixin):
    __tablename__ = "heroes_dispatch_pending_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    heroes_import_run_id: Mapped[int] = mapped_column(ForeignKey("heroes_import_runs.id"), nullable=False, index=True)
    product_name_raw: Mapped[str] = mapped_column(String(256), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_category_suggested: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quantity_to_dispatch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_listino: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_fattura: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    discount_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    acconto_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    credit_remaining: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    source_sheet: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parser_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_values: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Shipment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    shipment_number: Mapped[str] = mapped_column(String(64), nullable=False)
    modal: Mapped[str] = mapped_column(String(16), nullable=False)
    modal_previous: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bl_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    awb_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    container_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    etd_planned: Mapped[date | None] = mapped_column(Date, nullable=True)
    eta_planned: Mapped[date | None] = mapped_column(Date, nullable=True)
    etd_actual: Mapped[date | None] = mapped_column(Date, nullable=True)
    eta_actual: Mapped[date | None] = mapped_column(Date, nullable=True)
    freight_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    freight_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="shipments")
    items: Mapped[list["ShipmentItem"]] = relationship(back_populates="shipment")
    modal_changes: Mapped[list["ModalChangeLog"]] = relationship(back_populates="shipment")


class ShipmentItem(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "shipment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), nullable=False, index=True)
    importation_item_id: Mapped[int] = mapped_column(ForeignKey("importation_items.id"), nullable=False, index=True)
    quantity_shipped: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity_override_reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    quantity_override_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    shipment: Mapped["Shipment"] = relationship(back_populates="items")
    importation_item: Mapped["ImportationItem"] = relationship()


class ModalChangeLog(Base):
    __tablename__ = "modal_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), nullable=False, index=True)
    from_modal: Mapped[str] = mapped_column(String(16), nullable=False)
    to_modal: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    estimated_cost_impact: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    estimated_time_impact_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="modal_changes")


class CustomsDocument(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customs_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(16), nullable=False)
    document_number: Mapped[str] = mapped_column(String(64), nullable=False)
    document_data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    official_data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="STAGING")
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("document_attachments.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="customs_documents")
    taxes: Mapped[list["Tax"]] = relationship(back_populates="customs_document")


class Tax(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "taxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    customs_document_id: Mapped[int] = mapped_column(ForeignKey("customs_documents.id"), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    source_document_attachment_id: Mapped[int] = mapped_column(
        ForeignKey("document_attachments.id"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="taxes")
    customs_document: Mapped["CustomsDocument"] = relationship(back_populates="taxes")


class Nationalization(Base, TimestampMixin):
    __tablename__ = "nationalizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    customs_document_id: Mapped[int] = mapped_column(ForeignKey("customs_documents.id"), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="nationalizations")
    items: Mapped[list["NationalizationItem"]] = relationship(back_populates="nationalization")
    stock_entries: Mapped[list["StockEntry"]] = relationship(back_populates="nationalization")


class NationalizationItem(Base, TimestampMixin):
    __tablename__ = "nationalization_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nationalization_id: Mapped[int] = mapped_column(ForeignKey("nationalizations.id"), nullable=False, index=True)
    importation_item_id: Mapped[int] = mapped_column(ForeignKey("importation_items.id"), nullable=False)
    quantity_nationalized: Mapped[int] = mapped_column(Integer, nullable=False)

    nationalization: Mapped["Nationalization"] = relationship(back_populates="items")


class StockEntry(Base, TimestampMixin):
    __tablename__ = "stock_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nationalization_id: Mapped[int] = mapped_column(ForeignKey("nationalizations.id"), nullable=False, index=True)
    importation_item_id: Mapped[int] = mapped_column(ForeignKey("importation_items.id"), nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_approved: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    landed_cost_version_id: Mapped[int | None] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=True)
    override_reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    override_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    nationalization: Mapped["Nationalization"] = relationship(back_populates="stock_entries")


class EntrepostoMovement(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "entreposto_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    importation_item_id: Mapped[int] = mapped_column(ForeignKey("importation_items.id"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipments.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="entreposto_movements")
    importation_item: Mapped["ImportationItem"] = relationship()
    shipment: Mapped["Shipment | None"] = relationship()


class QuantityDiscrepancy(Base, TimestampMixin):
    __tablename__ = "quantity_discrepancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    importation_item_id: Mapped[int | None] = mapped_column(ForeignKey("importation_items.id"), nullable=True)
    stage_from: Mapped[str] = mapped_column(String(32), nullable=False)
    stage_to: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difference: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class LandedCostVersion(Base, TimestampMixin):
    __tablename__ = "landed_cost_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_current_version: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    previous_version_id: Mapped[int | None] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=True)
    trigger_event: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trigger_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="landed_cost_versions")
    components: Mapped[list["LandedCostComponent"]] = relationship(back_populates="version")
    allocations: Mapped[list["LandedCostSkuAllocation"]] = relationship(back_populates="version")


class LandedCostComponent(Base, TimestampMixin):
    __tablename__ = "landed_cost_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    landed_cost_version_id: Mapped[int] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=False, index=True)
    component_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    version: Mapped["LandedCostVersion"] = relationship(back_populates="components")


class LandedCostSkuAllocation(Base, TimestampMixin):
    __tablename__ = "landed_cost_sku_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    landed_cost_version_id: Mapped[int] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=False, index=True)
    importation_item_id: Mapped[int] = mapped_column(ForeignKey("importation_items.id"), nullable=False)
    allocation_method: Mapped[str] = mapped_column(String(16), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantity_basis: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual_reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    manual_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped["LandedCostVersion"] = relationship(back_populates="allocations")


class LandedCostVariance(Base, TimestampMixin):
    __tablename__ = "landed_cost_variances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    version_from_id: Mapped[int] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=False)
    version_to_id: Mapped[int] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=False)
    variance_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class Reconciliation(Base, TimestampMixin):
    __tablename__ = "reconciliations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    pair_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_a_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_a_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_b_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_b_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    variance_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tolerance_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="BLOCKING")
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    entity_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    approval_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="reconciliations")


class ImportationClosure(Base, TimestampMixin):
    __tablename__ = "importation_closures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importation_id: Mapped[int] = mapped_column(ForeignKey("importation_orders.id"), nullable=False, index=True)
    closure_version: Mapped[int] = mapped_column(Integer, nullable=False)
    landed_cost_version_id: Mapped[int | None] = mapped_column(ForeignKey("landed_cost_versions.id"), nullable=True)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    closure_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    close_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_reconciliation_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reopened_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopen_reason_code_id: Mapped[int | None] = mapped_column(ForeignKey("reason_codes.id"), nullable=True)
    reopen_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    importation: Mapped["ImportationOrder"] = relationship(back_populates="closures")
