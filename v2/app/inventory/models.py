"""Inventory domain models — J#5 I5-4 StockLocation / GoodsReceipt / Movements / StockBalance."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

LOCATION_TYPES = ("BONDED", "DOMESTIC", "QUARANTINE")
RECEIPT_TYPES = ("BONDED_IN", "DOMESTIC_IN", "RECLASS", "ADJUSTMENT")
RECEIPT_STATUSES = ("DRAFT", "CONFIRMED", "REVERSED")
MOVEMENT_TYPES = (
    "BONDED_IN",
    "DOMESTIC_IN",
    "RECLASS_OUT",
    "RECLASS_IN",
    "ADJUSTMENT",
    "QUARANTINE_IN",
    "QUARANTINE_OUT",
    "SHORTAGE",
    "SURPLUS",
    "DAMAGE",
    "REVERSAL",
)

DEFAULT_LOCATIONS = (
    ("BONDED-MAIN", "Entreposto principal", "BONDED"),
    ("DOMESTIC-MAIN", "Estoque doméstico principal", "DOMESTIC"),
    ("QUARANTINE-MAIN", "Quarentena principal", "QUARANTINE"),
)


class StockLocation(Base):
    __tablename__ = "stock_locations"
    __table_args__ = (
        UniqueConstraint("code", name="uq_stock_locations_code"),
        CheckConstraint(
            "location_type IN ('BONDED', 'DOMESTIC', 'QUARANTINE')",
            name="ck_stock_locations_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    receipts: Mapped[list["GoodsReceipt"]] = relationship(back_populates="location")
    movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="location")
    balances: Mapped[list["StockBalance"]] = relationship(back_populates="location")


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"
    __table_args__ = (
        CheckConstraint(
            "receipt_type IN ('BONDED_IN', 'DOMESTIC_IN', 'RECLASS', 'ADJUSTMENT')",
            name="ck_goods_receipts_type",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'REVERSED')",
            name="ck_goods_receipts_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    process_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_processes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nationalization_id: Mapped[int | None] = mapped_column(
        ForeignKey("nationalizations.id", ondelete="SET NULL"), nullable=True
    )
    receipt_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    location: Mapped[StockLocation] = relationship(back_populates="receipts")
    lines: Mapped[list["GoodsReceiptLine"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_goods_receipt_lines_qty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    nationalization_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("nationalization_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    shipment_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipment_items.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    receipt: Mapped[GoodsReceipt] = relationship(back_populates="lines")


class InventoryMovement(Base):
    """Append-only ledger — never edit; reverse via inverse movement."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ("
            "'BONDED_IN', 'DOMESTIC_IN', 'RECLASS_OUT', 'RECLASS_IN', "
            "'ADJUSTMENT', 'QUARANTINE_IN', 'QUARANTINE_OUT', "
            "'SHORTAGE', 'SURPLUS', 'DAMAGE', 'REVERSAL'"
            ")",
            name="ck_inventory_movements_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    receipt_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("goods_receipt_lines.id", ondelete="SET NULL"), nullable=True
    )
    nationalization_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("nationalization_items.id", ondelete="SET NULL"), nullable=True
    )
    reversal_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    location: Mapped[StockLocation] = relationship(back_populates="movements")


class StockBalance(Base):
    """Derived cache — rebuildable from InventoryMovement; never edit manually."""

    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint(
            "location_id", "product_id", name="uq_stock_balances_location_product"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    location: Mapped[StockLocation] = relationship(back_populates="balances")
