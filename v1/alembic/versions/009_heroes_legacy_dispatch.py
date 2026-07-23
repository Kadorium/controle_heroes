"""heroes legacy versato + dispatch pending items

Revision ID: 009
Revises: 008
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "heroes_legacy_sheet_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("importation_id", sa.Integer(), sa.ForeignKey("importation_orders.id"), nullable=False, index=True),
        sa.Column("heroes_import_run_id", sa.Integer(), sa.ForeignKey("heroes_import_runs.id"), nullable=False, index=True),
        sa.Column("sheet_name", sa.String(128), nullable=False),
        sa.Column("versato_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("versato_currency", sa.String(8), nullable=False, server_default="EUR"),
        sa.Column("versato_source_row", sa.Integer(), nullable=True),
        sa.Column("versato_source_cell", sa.String(16), nullable=True),
        sa.Column("versato_raw_value", sa.String(64), nullable=True),
        sa.Column("versato_confidence", sa.Float(), nullable=True),
        sa.Column("parser_version", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "heroes_dispatch_pending_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("importation_id", sa.Integer(), sa.ForeignKey("importation_orders.id"), nullable=False, index=True),
        sa.Column("heroes_import_run_id", sa.Integer(), sa.ForeignKey("heroes_import_runs.id"), nullable=False, index=True),
        sa.Column("product_name_raw", sa.String(256), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("product_category_suggested", sa.String(32), nullable=True),
        sa.Column("quantity_to_dispatch", sa.Integer(), nullable=True),
        sa.Column("price_listino", sa.Numeric(18, 4), nullable=True),
        sa.Column("price_fattura", sa.Numeric(18, 4), nullable=True),
        sa.Column("discount_unit", sa.Numeric(18, 4), nullable=True),
        sa.Column("acconto_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("credit_remaining", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="EUR"),
        sa.Column("source_sheet", sa.String(128), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("parser_confidence", sa.Float(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_values", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "heroes_import_runs",
        sa.Column("confirmed_order_number", sa.String(32), nullable=True),
    )
    op.add_column(
        "heroes_import_runs",
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "importation_orders",
        sa.Column("brazil_operational_notes", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("importation_orders", "brazil_operational_notes")
    op.drop_column("heroes_import_runs", "review_required")
    op.drop_column("heroes_import_runs", "confirmed_order_number")
    op.drop_table("heroes_dispatch_pending_items")
    op.drop_table("heroes_legacy_sheet_summaries")
