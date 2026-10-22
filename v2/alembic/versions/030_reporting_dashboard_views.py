"""J#7 — visões pessoais do painel gerencial.

Revision ID: 030
Revises: 029
Create Date: 2026-08-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reporting_dashboard_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_preset", sa.String(32), nullable=False),
        sa.Column("layout_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("filters_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("actor_id", "name", name="uq_reporting_dashboard_views_actor_name"),
    )
    op.create_index("ix_reporting_dashboard_views_actor_id", "reporting_dashboard_views", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_reporting_dashboard_views_actor_id", table_name="reporting_dashboard_views")
    op.drop_table("reporting_dashboard_views")
