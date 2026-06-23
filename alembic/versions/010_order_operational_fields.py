"""order operational fields: priority, responsible, internal_forecast_date

Revision ID: 010
Revises: 009
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "importation_orders",
        sa.Column("priority", sa.String(16), nullable=True),
    )
    op.add_column(
        "importation_orders",
        sa.Column("responsible", sa.String(128), nullable=True),
    )
    op.add_column(
        "importation_orders",
        sa.Column("internal_forecast_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("importation_orders", "internal_forecast_date")
    op.drop_column("importation_orders", "responsible")
    op.drop_column("importation_orders", "priority")
