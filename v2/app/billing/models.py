from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

INVOICE_STATUSES = ("DRAFT", "ISSUED", "CANCELLED")
INVOICE_TYPES = ("FINAL", "PROFORMA")
DISCOUNT_TYPES = ("NONE", "UNIT_AMOUNT", "PERCENT")
TERMS_MODES = ("PERCENT", "AMOUNT")
PAYABLE_STATUSES = ("OPEN", "CANCELLED")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'ISSUED', 'CANCELLED')",
            name="ck_invoices_status",
        ),
        CheckConstraint(
            "invoice_type IN ('FINAL', 'PROFORMA')",
            name="ck_invoices_type",
        ),
        CheckConstraint(
            "terms_mode IS NULL OR terms_mode IN ('PERCENT', 'AMOUNT')",
            name="ck_invoices_terms_mode",
        ),
        UniqueConstraint("supplier_id", "invoice_number", name="uq_invoice_supplier_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    invoice_type: Mapped[str] = mapped_column(String(32), nullable=False, default="FINAL")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    terms_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issue_without_document: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.position"
    )
    terms: Mapped[list["PaymentTerm"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="PaymentTerm.sequence"
    )
    payables: Mapped[list["Payable"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="Payable.sequence"
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        UniqueConstraint("invoice_id", "position", name="uq_invoice_item_position"),
        CheckConstraint(
            "discount_type IS NULL OR discount_type IN ('NONE', 'UNIT_AMOUNT', 'PERCENT')",
            name="ck_invoice_item_discount_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price_gross: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    discount_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    discount_unit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="items")


class PaymentTerm(Base):
    __tablename__ = "payment_terms"
    __table_args__ = (
        UniqueConstraint("invoice_id", "sequence", name="uq_payment_term_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped["Invoice"] = relationship(back_populates="terms")


class Payable(Base):
    __tablename__ = "payables"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'CANCELLED')",
            name="ck_payables_status",
        ),
        UniqueConstraint("invoice_id", "sequence", name="uq_payable_invoice_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    payment_term_id: Mapped[int] = mapped_column(ForeignKey("payment_terms.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="payables")
