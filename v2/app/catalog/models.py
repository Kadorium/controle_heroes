from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProductType(Base):
    __tablename__ = "product_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommended_attributes: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )


class CatalogImportBatch(Base):
    __tablename__ = "catalog_import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "net_weight_kg IS NULL OR net_weight_kg > 0",
            name="ck_products_net_weight_positive",
        ),
        CheckConstraint(
            "taxonomy_status IS NULL OR taxonomy_status IN ('CONFIDENT', 'REVIEW')",
            name="ck_products_taxonomy_status",
        ),
        CheckConstraint(
            "lifecycle_status IS NULL OR lifecycle_status IN ('ACTIVE', 'DISCONTINUED', 'UNKNOWN')",
            name="ck_products_lifecycle_status",
        ),
        CheckConstraint(
            "import_decision IS NULL OR import_decision IN ('APROVAR', 'EDITAR', 'REVISAR', 'IGNORAR')",
            name="ck_products_import_decision",
        ),
        Index(
            "uq_products_ean_not_null",
            "ean",
            unique=True,
            postgresql_where=text("ean IS NOT NULL"),
        ),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_product_type_id", "product_type_id"),
        Index("ix_products_taxonomy_status", "taxonomy_status"),
        Index("ix_products_source_kind", "source_kind"),
        Index("ix_products_import_decision", "import_decision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    commercial_name: Mapped[str] = mapped_column(String(512), nullable=False)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    fiscal_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lifecycle_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(18), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ncm: Mapped[str | None] = mapped_column(String(8), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    supplier_sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"), nullable=True)
    product_type_id: Mapped[int | None] = mapped_column(ForeignKey("product_types.id"), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    taxonomy_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    taxonomy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    import_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    short_generic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    source_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_import_batches.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[ProductCategory | None] = relationship("ProductCategory")
    product_type: Mapped[ProductType | None] = relationship("ProductType")
    import_batch: Mapped[CatalogImportBatch | None] = relationship("CatalogImportBatch")
