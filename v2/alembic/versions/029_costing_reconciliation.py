"""J#6 Costing + Reconciliation schema.

Revision ID: 029
Revises: 028
Create Date: 2026-08-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "costing_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "import_process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("current_published_id", sa.Integer(), nullable=True),
        sa.Column("freight_choice", sa.String(32), nullable=True),
        sa.Column("freight_choice_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("import_process_id", name="uq_costing_cases_process"),
        sa.CheckConstraint(
            "freight_choice IS NULL OR freight_choice IN ('VALUE_BASIS', 'EXPENSE_LINE', 'EXCLUDE')",
            name="ck_costing_cases_freight_choice",
        ),
    )
    op.create_index("ix_costing_cases_import_process_id", "costing_cases", ["import_process_id"])

    op.create_table(
        "costing_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("costing_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("partial_coverage", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("included_total_brl", sa.Numeric(18, 4), nullable=True),
        sa.Column("gross_total_brl", sa.Numeric(18, 4), nullable=True),
        sa.Column("snapshot", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "previous_version_id",
            sa.Integer(),
            sa.ForeignKey("costing_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_actor_id", sa.String(64), nullable=True),
        sa.Column("publish_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "version_number", name="uq_costing_versions_number"),
        sa.CheckConstraint(
            "kind IN ('ESTIMATED', 'REVISED', 'REALIZED')",
            name="ck_costing_versions_kind",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'SUPERSEDED', 'CANCELLED')",
            name="ck_costing_versions_status",
        ),
    )
    op.create_index("ix_costing_versions_case_id", "costing_versions", ["case_id"])
    op.create_index("ix_costing_versions_status", "costing_versions", ["status"])

    op.create_foreign_key(
        "fk_costing_cases_current_published",
        "costing_cases",
        "costing_versions",
        ["current_published_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "costing_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("costing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_item_id",
            sa.Integer(),
            sa.ForeignKey("invoice_items.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "shipment_item_id",
            sa.Integer(),
            sa.ForeignKey("shipment_items.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "order_item_id",
            sa.Integer(),
            sa.ForeignKey("order_items.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("sku_snapshot", sa.String(64), nullable=False),
        sa.Column("description_snapshot", sa.String(512), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("foreign_net", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("merchandise_brl", sa.Numeric(18, 4), nullable=True),
        sa.Column("fx_status", sa.String(32), nullable=False, server_default="NONE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "invoice_item_id IS NOT NULL OR shipment_item_id IS NOT NULL",
            name="ck_costing_lines_ref",
        ),
        sa.CheckConstraint("qty > 0", name="ck_costing_lines_qty"),
    )
    op.create_index("ix_costing_lines_version_id", "costing_lines", ["version_id"])
    op.create_index(
        "uq_costing_lines_invoice_item",
        "costing_lines",
        ["version_id", "invoice_item_id"],
        unique=True,
        postgresql_where=sa.text("invoice_item_id IS NOT NULL"),
    )
    op.create_index(
        "uq_costing_lines_shipment_item",
        "costing_lines",
        ["version_id", "shipment_item_id"],
        unique=True,
        postgresql_where=sa.text("shipment_item_id IS NOT NULL"),
    )

    op.create_table(
        "cost_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("costing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("component_type", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("amount_orig", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("amount_brl", sa.Numeric(18, 4), nullable=True),
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allocation_method", sa.String(32), nullable=False, server_default="VALUE"),
        sa.Column("fx_rule", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="OK"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cost_components_version_id", "cost_components", ["version_id"])

    op.create_table(
        "cost_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "component_id",
            sa.Integer(),
            sa.ForeignKey("cost_components.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "line_id",
            sa.Integer(),
            sa.ForeignKey("costing_lines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_brl", sa.Numeric(18, 6), nullable=False),
        sa.Column("residual_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("component_id", "line_id", name="uq_cost_allocations_pair"),
    )

    op.create_table(
        "costing_expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("costing_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="BRL"),
        sa.Column("expense_date", sa.Date(), nullable=True),
        sa.Column("payee_snapshot", sa.String(256), nullable=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("allocation_method", sa.String(32), nullable=False, server_default="VALUE"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'CANCELLED')",
            name="ck_costing_expenses_status",
        ),
    )

    op.create_table(
        "reconciliation_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "costing_version_id",
            sa.Integer(),
            sa.ForeignKey("costing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_reconciliation_cases_status"),
    )
    op.create_index(
        "ix_reconciliation_cases_costing_version_id",
        "reconciliation_cases",
        ["costing_version_id"],
    )

    op.create_table(
        "reconciliation_pairs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("reconciliation_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pair_type", sa.String(64), nullable=False),
        sa.Column("left_label", sa.String(256), nullable=False),
        sa.Column("left_value", sa.Text(), nullable=True),
        sa.Column("right_label", sa.String(256), nullable=False),
        sa.Column("right_value", sa.Text(), nullable=True),
        sa.Column("delta", sa.String(64), nullable=True),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("tolerance", sa.String(64), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("blocks_publish", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "severity IN ('WARNING', 'BLOCKING')",
            name="ck_reconciliation_pairs_severity",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ACCEPTED', 'RESOLVED')",
            name="ck_reconciliation_pairs_status",
        ),
    )
    op.create_index("ix_reconciliation_pairs_case_id", "reconciliation_pairs", ["case_id"])
    op.create_index("ix_reconciliation_pairs_pair_type", "reconciliation_pairs", ["pair_type"])


def downgrade() -> None:
    op.drop_table("reconciliation_pairs")
    op.drop_table("reconciliation_cases")
    op.drop_table("costing_expenses")
    op.drop_table("cost_allocations")
    op.drop_table("cost_components")
    op.drop_table("costing_lines")
    op.drop_constraint("fk_costing_cases_current_published", "costing_cases", type_="foreignkey")
    op.drop_table("costing_versions")
    op.drop_table("costing_cases")
