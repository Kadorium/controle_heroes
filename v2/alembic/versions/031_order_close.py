"""Elo 10 — Order.closed_at / close_reason_code (simétrico a cancel).

Revision ID: 031
Revises: 030
Create Date: 2026-10-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("close_reason_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "close_reason_code")
    op.drop_column("orders", "closed_at")
