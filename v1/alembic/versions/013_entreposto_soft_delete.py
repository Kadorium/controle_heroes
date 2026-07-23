"""entreposto soft-delete columns

Revision ID: 013
Revises: 012
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("entreposto_movements", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("entreposto_movements", sa.Column("cancelled_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("entreposto_movements", sa.Column("cancellation_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("entreposto_movements", "cancellation_reason")
    op.drop_column("entreposto_movements", "cancelled_by_id")
    op.drop_column("entreposto_movements", "cancelled_at")
