"""Logistics domain models — J#4."""

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

SHIPMENT_STATUSES = ("PLANNED", "BOOKED", "IN_TRANSIT", "ARRIVED")
SHIPMENT_MODALS = ("SEA", "AIR", "ROAD", "COURIER", "MULTIMODAL", "OTHER")
PROVIDER_TYPES = (
    "TRANSPORTADOR",
    "ARMADOR",
    "FREIGHT_FORWARDER",
    "OPERADOR_LOGISTICO",
    "DESPACHANTE",
)
SHIPMENT_PROVIDER_TYPES = (
    "TRANSPORTADOR",
    "ARMADOR",
    "FREIGHT_FORWARDER",
    "OPERADOR_LOGISTICO",
)
PACKAGE_TYPES = ("PALLET", "CARTON", "BOX", "OTHER")
DECLARED_PROVENANCES = ("PACKING_LIST", "FATTURA_DOGANALE", "MANUAL", "OTHER")
REFERENCE_TYPES = (
    "PACKING_LIST",
    "DDT",
    "BL",
    "AWB",
    "BOOKING",
    "CONTAINER",
    "FORWARDER_REFERENCE",
    "OTHER",
)


class LogisticsProvider(Base):
    __tablename__ = "logistics_providers"
    __table_args__ = (
        CheckConstraint(
            "provider_type IN ("
            "'TRANSPORTADOR','ARMADOR','FREIGHT_FORWARDER',"
            "'OPERADOR_LOGISTICO','DESPACHANTE')",
            name="ck_logistics_providers_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED', 'BOOKED', 'IN_TRANSIT', 'ARRIVED')",
            name="ck_shipments_status",
        ),
        CheckConstraint(
            "modal IS NULL OR modal IN ("
            "'SEA','AIR','ROAD','COURIER','MULTIMODAL','OTHER')",
            name="ck_shipments_modal",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    modal: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    origin: Mapped[str | None] = mapped_column(String(128), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(128), nullable=True)
    logistics_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("logistics_providers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    carrier_name_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    planned_departure: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_arrival: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_departure: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_arrival: Mapped[date | None] = mapped_column(Date, nullable=True)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    logistics_provider: Mapped["LogisticsProvider | None"] = relationship()
    items: Mapped[list["ShipmentItem"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )
    packages: Mapped[list["ShipmentPackage"]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        foreign_keys="ShipmentPackage.shipment_id",
    )
    references: Mapped[list["ShipmentReference"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )
    document_summaries: Mapped[list["ShipmentDocumentSummary"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )


class ShipmentItem(Base):
    __tablename__ = "shipment_items"
    __table_args__ = (
        UniqueConstraint("shipment_id", "order_item_id", name="uq_shipment_item_order_item"),
        CheckConstraint("quantity > 0", name="ck_shipment_items_qty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="items")
    contents: Mapped[list["ShipmentPackageContent"]] = relationship(
        back_populates="shipment_item", cascade="all, delete-orphan"
    )


class ShipmentPackage(Base):
    __tablename__ = "shipment_packages"
    __table_args__ = (
        CheckConstraint(
            "package_type IN ('PALLET', 'CARTON', 'BOX', 'OTHER')",
            name="ck_shipment_packages_type",
        ),
        CheckConstraint("package_count > 0", name="ck_shipment_packages_count"),
        CheckConstraint(
            "parent_package_id IS NULL OR package_count = 1",
            name="ck_shipment_packages_parent_count",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_package_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipment_packages.id", ondelete="SET NULL"), nullable=True
    )
    external_package_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    package_type: Mapped[str] = mapped_column(String(16), nullable=False)
    package_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    packaging_ncm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    length: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    dimension_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    raw_dimensions: Mapped[str | None] = mapped_column(String(128), nullable=True)
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume_is_derived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shipment: Mapped["Shipment"] = relationship(
        back_populates="packages", foreign_keys=[shipment_id]
    )
    contents: Mapped[list["ShipmentPackageContent"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )


class ShipmentPackageContent(Base):
    __tablename__ = "shipment_package_contents"
    __table_args__ = (
        UniqueConstraint("package_id", "shipment_item_id", name="uq_pkg_content_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("shipment_packages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shipment_item_id: Mapped[int] = mapped_column(
        ForeignKey("shipment_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contained_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    source_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_line_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_ncm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    units_per_package: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    source_total_net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    source_total_gross_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    package: Mapped["ShipmentPackage"] = relationship(back_populates="contents")
    shipment_item: Mapped["ShipmentItem"] = relationship(back_populates="contents")


class ShipmentReference(Base):
    __tablename__ = "shipment_references"
    __table_args__ = (
        UniqueConstraint(
            "shipment_id",
            "reference_type",
            "reference_value",
            name="uq_shipment_reference",
        ),
        CheckConstraint(
            "reference_type IN ("
            "'PACKING_LIST','DDT','BL','AWB','BOOKING','CONTAINER',"
            "'FORWARDER_REFERENCE','OTHER')",
            name="ck_shipment_references_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_value: Mapped[str] = mapped_column(String(128), nullable=False)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shipment: Mapped["Shipment"] = relationship(back_populates="references")


class ShipmentDocumentSummary(Base):
    __tablename__ = "shipment_document_summaries"
    __table_args__ = (
        UniqueConstraint("shipment_id", "document_id", name="uq_shipment_doc_summary"),
        CheckConstraint(
            "declared_provenance IS NULL OR declared_provenance IN ("
            "'PACKING_LIST','FATTURA_DOGANALE','MANUAL','OTHER')",
            name="ck_shipment_doc_summary_provenance",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    declared_net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    declared_gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    declared_pallet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    declared_carton_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    declared_volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    declared_provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="document_summaries")
