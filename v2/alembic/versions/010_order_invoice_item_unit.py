"""A2 Document Readiness — optional unit snapshot on OrderItem / InvoiceItem

Revision ID: 010
Revises: 009
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("unit", sa.String(16), nullable=True),
    )
    op.add_column(
        "invoice_items",
        sa.Column("unit", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoice_items", "unit")
    op.drop_column("order_items", "unit")
