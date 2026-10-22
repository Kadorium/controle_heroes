"""Reconciliation domain models — J#6 (pares mínimos de publicação)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base


class ReconciliationCase(Base):
    __tablename__ = "reconciliation_cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')",
            name="ck_reconciliation_cases_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    costing_version_id: Mapped[int] = mapped_column(
        ForeignKey("costing_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pairs: Mapped[list["ReconciliationPair"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class ReconciliationPair(Base):
    __tablename__ = "reconciliation_pairs"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('WARNING', 'BLOCKING')",
            name="ck_reconciliation_pairs_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'ACCEPTED', 'RESOLVED')",
            name="ck_reconciliation_pairs_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("reconciliation_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pair_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    left_label: Mapped[str] = mapped_column(String(256), nullable=False)
    left_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    right_label: Mapped[str] = mapped_column(String(256), nullable=False)
    right_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    delta: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tolerance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    blocks_publish: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[ReconciliationCase] = relationship(back_populates="pairs")
