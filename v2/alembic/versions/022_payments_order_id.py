"""J4-FIN FIN-1 — payments.order_id (adiantamento / ACCONTO Opção B).

Nullable FK: Payment residual sem Fattura ligado ao Order.
N Payments por Order; Payable NÃO é criado por este vínculo.

Revision ID: 022
Revises: 021
Create Date: 2026-08-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("order_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payments_order_id_orders",
        "payments",
        "orders",
        ["order_id"],
        ["id"],
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_constraint("fk_payments_order_id_orders", "payments", type_="foreignkey")
    op.drop_column("payments", "order_id")
