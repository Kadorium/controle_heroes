"""Costing domain models — J#6."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

VERSION_KINDS = ("ESTIMATED", "REVISED", "REALIZED")
VERSION_STATUSES = ("DRAFT", "PUBLISHED", "SUPERSEDED", "CANCELLED")
ALLOCATION_METHODS = ("VALUE", "QUANTITY", "WEIGHT", "VOLUME", "MANUAL")
FREIGHT_CHOICES = ("VALUE_BASIS", "EXPENSE_LINE", "EXCLUDE")
EXPENSE_STATUSES = ("ACTIVE", "CANCELLED")


class CostingCase(Base):
    __tablename__ = "costing_cases"
    __table_args__ = (
        UniqueConstraint("import_process_id", name="uq_costing_cases_process"),
        CheckConstraint(
            "freight_choice IS NULL OR freight_choice IN ('VALUE_BASIS', 'EXPENSE_LINE', 'EXCLUDE')",
            name="ck_costing_cases_freight_choice",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    current_published_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "costing_versions.id",
            use_alter=True,
            name="fk_costing_cases_current_published",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    freight_choice: Mapped[str | None] = mapped_column(String(32), nullable=True)
    freight_choice_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["CostingVersion"]] = relationship(
        back_populates="case",
        foreign_keys="CostingVersion.case_id",
        cascade="all, delete-orphan",
    )
    expenses: Mapped[list["CostingExpense"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class CostingVersion(Base):
    __tablename__ = "costing_versions"
    __table_args__ = (
        UniqueConstraint("case_id", "version_number", name="uq_costing_versions_number"),
        CheckConstraint(
            "kind IN ('ESTIMATED', 'REVISED', 'REALIZED')",
            name="ck_costing_versions_kind",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'SUPERSEDED', 'CANCELLED')",
            name="ck_costing_versions_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("costing_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    partial_coverage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    included_total_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    gross_total_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    previous_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("costing_versions.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publish_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    case: Mapped[CostingCase] = relationship(
        back_populates="versions", foreign_keys=[case_id]
    )
    lines: Mapped[list["CostingLine"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    components: Mapped[list["CostComponent"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class CostingLine(Base):
    __tablename__ = "costing_lines"
    __table_args__ = (
        CheckConstraint(
            "invoice_item_id IS NOT NULL OR shipment_item_id IS NOT NULL",
            name="ck_costing_lines_ref",
        ),
        CheckConstraint("qty > 0", name="ck_costing_lines_qty"),
        Index(
            "uq_costing_lines_invoice_item",
            "version_id",
            "invoice_item_id",
            unique=True,
            postgresql_where=text("invoice_item_id IS NOT NULL"),
        ),
        Index(
            "uq_costing_lines_shipment_item",
            "version_id",
            "shipment_item_id",
            unique=True,
            postgresql_where=text("shipment_item_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("costing_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoice_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    shipment_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipment_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sku_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(String(512), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    foreign_net: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    merchandise_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fx_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NONE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    version: Mapped[CostingVersion] = relationship(back_populates="lines")
    allocations: Mapped[list["CostAllocation"]] = relationship(
        back_populates="line", cascade="all, delete-orphan"
    )


class CostComponent(Base):
    __tablename__ = "cost_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("costing_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_orig: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    amount_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allocation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="VALUE")
    fx_rule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OK")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    version: Mapped[CostingVersion] = relationship(back_populates="components")
    allocations: Mapped[list["CostAllocation"]] = relationship(
        back_populates="component", cascade="all, delete-orphan"
    )


class CostAllocation(Base):
    __tablename__ = "cost_allocations"
    __table_args__ = (
        UniqueConstraint("component_id", "line_id", name="uq_cost_allocations_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("cost_components.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_id: Mapped[int] = mapped_column(
        ForeignKey("costing_lines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    residual_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    component: Mapped[CostComponent] = relationship(back_populates="allocations")
    line: Mapped[CostingLine] = relationship(back_populates="allocations")


class CostingExpense(Base):
    __tablename__ = "costing_expenses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'CANCELLED')",
            name="ck_costing_expenses_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("costing_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    expense_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payee_snapshot: Mapped[str | None] = mapped_column(String(256), nullable=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    allocation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="VALUE")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[CostingCase] = relationship(back_populates="expenses")
