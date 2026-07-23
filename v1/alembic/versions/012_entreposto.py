"""entreposto movements

Revision ID: 012
Revises: 011
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entreposto_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("importation_id", sa.Integer(), sa.ForeignKey("importation_orders.id"), nullable=False),
        sa.Column("importation_item_id", sa.Integer(), sa.ForeignKey("importation_items.id"), nullable=False),
        sa.Column("movement_type", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reason_code_id", sa.Integer(), sa.ForeignKey("reason_codes.id"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_entreposto_movements_importation_id", "entreposto_movements", ["importation_id"])
    op.create_index("ix_entreposto_movements_importation_item_id", "entreposto_movements", ["importation_item_id"])


def downgrade() -> None:
    op.drop_index("ix_entreposto_movements_importation_item_id", table_name="entreposto_movements")
    op.drop_index("ix_entreposto_movements_importation_id", table_name="entreposto_movements")
    op.drop_table("entreposto_movements")
