"""billing Inc-2

Revision ID: 003
Revises: 002
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("invoice_number", sa.String(64), nullable=False),
        sa.Column("invoice_type", sa.String(32), nullable=False, server_default="FINAL"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("terms_mode", sa.String(16), nullable=True),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason_code", sa.String(64), nullable=True),
        sa.Column("issue_without_document", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('DRAFT', 'ISSUED', 'CANCELLED')", name="ck_invoices_status"),
        sa.CheckConstraint("invoice_type IN ('FINAL', 'PROFORMA')", name="ck_invoices_type"),
        sa.CheckConstraint(
            "terms_mode IS NULL OR terms_mode IN ('PERCENT', 'AMOUNT')",
            name="ck_invoices_terms_mode",
        ),
        sa.UniqueConstraint("supplier_id", "invoice_number", name="uq_invoice_supplier_number"),
    )
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"])
    op.create_index("ix_invoices_supplier_id", "invoices", ["supplier_id"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("sku_snapshot", sa.String(64), nullable=False),
        sa.Column("description_snapshot", sa.String(512), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price_gross", sa.Numeric(18, 4), nullable=True),
        sa.Column("discount_type", sa.String(32), nullable=True),
        sa.Column("discount_unit_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("discount_percent", sa.Numeric(18, 4), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_id", "position", name="uq_invoice_item_position"),
        sa.CheckConstraint(
            "discount_type IS NULL OR discount_type IN ('NONE', 'UNIT_AMOUNT', 'PERCENT')",
            name="ck_invoice_item_discount_type",
        ),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])
    op.create_index("ix_invoice_items_order_item_id", "invoice_items", ["order_item_id"])

    op.create_table(
        "payment_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("percent", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_id", "sequence", name="uq_payment_term_sequence"),
    )
    op.create_index("ix_payment_terms_invoice_id", "payment_terms", ["invoice_id"])

    op.create_table(
        "payables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("payment_term_id", sa.Integer(), sa.ForeignKey("payment_terms.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('OPEN', 'CANCELLED')", name="ck_payables_status"),
        sa.UniqueConstraint("invoice_id", "sequence", name="uq_payable_invoice_sequence"),
    )
    op.create_index("ix_payables_invoice_id", "payables", ["invoice_id"])
    op.create_index("ix_payables_due_date", "payables", ["due_date"])


def downgrade() -> None:
    op.drop_table("payables")
    op.drop_table("payment_terms")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
