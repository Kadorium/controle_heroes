from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.foundation.database import Base


class Supplier(Base):
    """Catalog supplier — schema alembic 026 (tax_id opcional; sem RUX-3A)."""

    __tablename__ = "suppliers"
    __table_args__ = (
        Index(
            "uq_suppliers_country_tax_id",
            "country_code",
            "tax_id",
            unique=True,
            postgresql_where=text("tax_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "net_weight_kg IS NULL OR net_weight_kg > 0",
            name="ck_products_net_weight_positive",
        ),
        Index(
            "uq_products_ean_not_null",
            "ean",
            unique=True,
            postgresql_where=text("ean IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ean: Mapped[str | None] = mapped_column(String(18), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ncm: Mapped[str | None] = mapped_column(String(8), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
