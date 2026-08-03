"""J#5 I5-1 — ImportProcess + invoice/shipment joins + item allocations

Revision ID: 011
Revises: 010
Create Date: 2026-08-03

Sequência J#5 (planejada; só 011 nesta entrega):
  011 — ImportProcess + joins + alocações (I5-1)
  012 — Doganale versionada (I5-2)
  013 — FundingRequest / Payee / linhas (I5-3A)
  014 — Payables Customs / FundingPayableLink (I5-3B)
  015 — Inventory (I5-4)
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_processes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("external_reference", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'CANCELLED')",
            name="ck_import_processes_status",
        ),
    )
    op.create_index("ix_import_processes_code", "import_processes", ["code"], unique=True)
    op.create_index("ix_import_processes_status", "import_processes", ["status"])
    op.create_index("ix_import_processes_external_reference", "import_processes", ["external_reference"])

    op.create_table(
        "import_process_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_id", name="uq_import_process_invoices_invoice_id"),
        sa.UniqueConstraint("process_id", "invoice_id", name="uq_import_process_invoices_pair"),
    )
    op.create_index("ix_import_process_invoices_process_id", "import_process_invoices", ["process_id"])

    op.create_table(
        "import_process_invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_item_id",
            sa.Integer(),
            sa.ForeignKey("invoice_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("allocated_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("allocated_qty > 0", name="ck_import_process_invoice_items_qty"),
        sa.UniqueConstraint(
            "process_id",
            "invoice_item_id",
            name="uq_import_process_invoice_items_pair",
        ),
    )
    op.create_index(
        "ix_import_process_invoice_items_process_id",
        "import_process_invoice_items",
        ["process_id"],
    )
    op.create_index(
        "ix_import_process_invoice_items_invoice_item_id",
        "import_process_invoice_items",
        ["invoice_item_id"],
    )

    op.create_table(
        "import_process_shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shipment_id",
            sa.Integer(),
            sa.ForeignKey("shipments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("shipment_id", name="uq_import_process_shipments_shipment_id"),
        sa.UniqueConstraint("process_id", "shipment_id", name="uq_import_process_shipments_pair"),
    )
    op.create_index("ix_import_process_shipments_process_id", "import_process_shipments", ["process_id"])

    op.create_table(
        "import_process_shipment_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shipment_item_id",
            sa.Integer(),
            sa.ForeignKey("shipment_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("allocated_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("allocated_qty > 0", name="ck_import_process_shipment_items_qty"),
        sa.UniqueConstraint(
            "process_id",
            "shipment_item_id",
            name="uq_import_process_shipment_items_pair",
        ),
    )
    op.create_index(
        "ix_import_process_shipment_items_process_id",
        "import_process_shipment_items",
        ["process_id"],
    )
    op.create_index(
        "ix_import_process_shipment_items_shipment_item_id",
        "import_process_shipment_items",
        ["shipment_item_id"],
    )


def downgrade() -> None:
    op.drop_table("import_process_shipment_items")
    op.drop_table("import_process_shipments")
    op.drop_table("import_process_invoice_items")
    op.drop_table("import_process_invoices")
    op.drop_table("import_processes")
