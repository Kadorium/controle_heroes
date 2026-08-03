"""J#5 I5-4 — Nationalization + Inventory + SkuPosition

Revision ID: 015
Revises: 014
Create Date: 2026-08-03

Sequência J#5:
  011 — ImportProcess (I5-1) DONE
  012 — Doganale versionada (I5-2) DONE
  013 — FundingRequest / Payee / linhas (I5-3A) DONE
  014 — Payables Customs / FundingPayableLink (I5-3B) DONE
  015 — Nationalization + Inventory (I5-4)

Expande import_processes.status com PARTIALLY_CLEARED / CLEARED / IN_CLEARANCE.
Seed de localizações padrão: BONDED-MAIN, DOMESTIC-MAIN, QUARANTINE-MAIN.
Sem landed cost (J#6).
"""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_import_processes_status", "import_processes", type_="check")
    op.create_check_constraint(
        "ck_import_processes_status",
        "import_processes",
        "status IN ("
        "'DRAFT', 'SUBMITTED', 'IN_CLEARANCE', "
        "'PARTIALLY_CLEARED', 'CLEARED', 'CANCELLED'"
        ")",
    )

    op.create_table(
        "nationalizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'REVERSED')",
            name="ck_nationalizations_status",
        ),
    )
    op.create_index("ix_nationalizations_process_id", "nationalizations", ["process_id"])
    op.create_index("ix_nationalizations_status", "nationalizations", ["status"])

    op.create_table(
        "nationalization_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "nationalization_id",
            sa.Integer(),
            sa.ForeignKey("nationalizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doganale_line_id",
            sa.Integer(),
            sa.ForeignKey("customs_doganale_lines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "invoice_item_id",
            sa.Integer(),
            sa.ForeignKey("invoice_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "shipment_item_id",
            sa.Integer(),
            sa.ForeignKey("shipment_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_nationalization_items_qty"),
    )
    op.create_index(
        "ix_nationalization_items_nat_id", "nationalization_items", ["nationalization_id"]
    )
    op.create_index(
        "ix_nationalization_items_doganale_line_id",
        "nationalization_items",
        ["doganale_line_id"],
    )
    op.create_index(
        "ix_nationalization_items_invoice_item_id",
        "nationalization_items",
        ["invoice_item_id"],
    )
    op.create_index(
        "ix_nationalization_items_shipment_item_id",
        "nationalization_items",
        ["shipment_item_id"],
    )
    op.create_index(
        "ix_nationalization_items_product_id", "nationalization_items", ["product_id"]
    )

    op.create_table(
        "stock_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("location_type", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code", name="uq_stock_locations_code"),
        sa.CheckConstraint(
            "location_type IN ('BONDED', 'DOMESTIC', 'QUARANTINE')",
            name="ck_stock_locations_type",
        ),
    )
    op.create_index("ix_stock_locations_type", "stock_locations", ["location_type"])

    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("stock_locations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "nationalization_id",
            sa.Integer(),
            sa.ForeignKey("nationalizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("receipt_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "receipt_type IN ('BONDED_IN', 'DOMESTIC_IN', 'RECLASS', 'ADJUSTMENT')",
            name="ck_goods_receipts_type",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'REVERSED')",
            name="ck_goods_receipts_status",
        ),
    )
    op.create_index("ix_goods_receipts_location_id", "goods_receipts", ["location_id"])
    op.create_index("ix_goods_receipts_process_id", "goods_receipts", ["process_id"])
    op.create_index("ix_goods_receipts_status", "goods_receipts", ["status"])

    op.create_table(
        "goods_receipt_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "receipt_id",
            sa.Integer(),
            sa.ForeignKey("goods_receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "nationalization_item_id",
            sa.Integer(),
            sa.ForeignKey("nationalization_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "shipment_item_id",
            sa.Integer(),
            sa.ForeignKey("shipment_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_goods_receipt_lines_qty"),
    )
    op.create_index("ix_goods_receipt_lines_receipt_id", "goods_receipt_lines", ["receipt_id"])
    op.create_index("ix_goods_receipt_lines_product_id", "goods_receipt_lines", ["product_id"])
    op.create_index(
        "ix_goods_receipt_lines_nat_item_id",
        "goods_receipt_lines",
        ["nationalization_item_id"],
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("stock_locations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity_delta", sa.Numeric(18, 4), nullable=False),
        sa.Column("movement_type", sa.String(32), nullable=False),
        sa.Column(
            "receipt_line_id",
            sa.Integer(),
            sa.ForeignKey("goods_receipt_lines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "nationalization_item_id",
            sa.Integer(),
            sa.ForeignKey("nationalization_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reversal_of_id",
            sa.Integer(),
            sa.ForeignKey("inventory_movements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type IN ("
            "'BONDED_IN', 'DOMESTIC_IN', 'RECLASS_OUT', 'RECLASS_IN', "
            "'ADJUSTMENT', 'QUARANTINE_IN', 'QUARANTINE_OUT', "
            "'SHORTAGE', 'SURPLUS', 'DAMAGE', 'REVERSAL'"
            ")",
            name="ck_inventory_movements_type",
        ),
    )
    op.create_index("ix_inventory_movements_location_id", "inventory_movements", ["location_id"])
    op.create_index("ix_inventory_movements_product_id", "inventory_movements", ["product_id"])
    op.create_index("ix_inventory_movements_created_at", "inventory_movements", ["created_at"])

    op.create_table(
        "stock_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("stock_locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "location_id", "product_id", name="uq_stock_balances_location_product"
        ),
    )
    op.create_index("ix_stock_balances_product_id", "stock_balances", ["product_id"])

    op.execute(
        """
        INSERT INTO stock_locations (code, name, location_type, active) VALUES
        ('BONDED-MAIN', 'Entreposto principal', 'BONDED', true),
        ('DOMESTIC-MAIN', 'Estoque doméstico principal', 'DOMESTIC', true),
        ('QUARANTINE-MAIN', 'Quarentena principal', 'QUARANTINE', true)
        """
    )


def downgrade() -> None:
    op.drop_table("stock_balances")
    op.drop_table("inventory_movements")
    op.drop_table("goods_receipt_lines")
    op.drop_table("goods_receipts")
    op.drop_table("stock_locations")
    op.drop_table("nationalization_items")
    op.drop_table("nationalizations")

    op.drop_constraint("ck_import_processes_status", "import_processes", type_="check")
    op.create_check_constraint(
        "ck_import_processes_status",
        "import_processes",
        "status IN ('DRAFT', 'SUBMITTED', 'CANCELLED')",
    )
