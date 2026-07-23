"""Modelos FX Inc-4 — plan / quote / execution / link / valuation."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.foundation.database import Base


class FxPlanRate(Base):
    __tablename__ = "fx_plan_rates"
    __table_args__ = (
        CheckConstraint("kind IN ('INITIAL', 'REFORECAST', 'CORRECTION')", name="ck_fx_plan_kind"),
        CheckConstraint("rate > 0", name="ck_fx_plan_rate_positive"),
        CheckConstraint("base_currency = 'BRL'", name="ck_fx_plan_base_brl"),
        UniqueConstraint("payable_id", "idempotency_key", name="uq_fx_plan_idempotency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payable_id: Mapped[int] = mapped_column(ForeignKey("payables.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    foreign_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("fx_plan_rates.id"), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FxMarketQuote(Base):
    __tablename__ = "fx_market_quotes"
    __table_args__ = (
        CheckConstraint("rate > 0", name="ck_fx_quote_rate_positive"),
        CheckConstraint("base_currency = 'BRL'", name="ck_fx_quote_base_brl"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    foreign_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FxExecution(Base):
    __tablename__ = "fx_executions"
    __table_args__ = (
        CheckConstraint("foreign_amount > 0", name="ck_fx_exec_foreign_positive"),
        CheckConstraint("brl_amount > 0", name="ck_fx_exec_brl_positive"),
        CheckConstraint("rate > 0", name="ck_fx_exec_rate_positive"),
        UniqueConstraint("payment_id", "idempotency_key", name="uq_fx_exec_idempotency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    foreign_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    brl_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    execution_date: Mapped[date] = mapped_column(Date, nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    register_without_document: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FxExecutionAllocation(Base):
    __tablename__ = "fx_execution_allocations"
    __table_args__ = (
        CheckConstraint("foreign_amount > 0", name="ck_fx_link_foreign_positive"),
        CheckConstraint("brl_amount > 0", name="ck_fx_link_brl_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fx_execution_id: Mapped[int] = mapped_column(ForeignKey("fx_executions.id"), nullable=False, index=True)
    payment_allocation_id: Mapped[int] = mapped_column(
        ForeignKey("payment_allocations.id"), nullable=False, index=True
    )
    foreign_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    brl_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FxAllocationValuation(Base):
    __tablename__ = "fx_allocation_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_allocation_id: Mapped[int] = mapped_column(
        ForeignKey("payment_allocations.id"), nullable=False, unique=True
    )
    planned_rate_id: Mapped[int] = mapped_column(ForeignKey("fx_plan_rates.id"), nullable=False)
    planned_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    realized_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    foreign_amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    planned_brl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    realized_brl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    realized_result_vs_reference: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    reference_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="CURRENT_AT_FREEZE")
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
