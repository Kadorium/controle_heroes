"""product category + heroes import runs

Revision ID: 007
Revises: 006
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("category", sa.String(32), nullable=False, server_default="OTHER"),
    )
    op.create_table(
        "heroes_import_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_file_id", sa.Integer(), sa.ForeignKey("raw_import_files.id"), nullable=True),
        sa.Column("file_checksum", sa.String(64), nullable=False, index=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("sheet_name", sa.String(128), nullable=False),
        sa.Column("sheet_type", sa.String(32), nullable=False),
        sa.Column("parser_version", sa.String(16), nullable=False),
        sa.Column("order_number", sa.String(32), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PREVIEW"),
        sa.Column("preview_json", JSONB, nullable=False),
        sa.Column("normalized_json", JSONB, nullable=True),
        sa.Column("warnings_json", JSONB, nullable=True),
        sa.Column("errors_json", JSONB, nullable=True),
        sa.Column("importation_id", sa.Integer(), sa.ForeignKey("importation_orders.id"), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("heroes_import_runs")
    op.drop_column("products", "category")
