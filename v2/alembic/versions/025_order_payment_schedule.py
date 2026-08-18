"""FIN-4 — cronograma de pagamento no pedido (planejamento Orders).

Não é Payable, Payment nem PaymentAllocation. Sem coluna de modo em orders.
Backfill: NONE.

Revision ID: 025
Revises: 024
Create Date: 2026-08-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_payment_schedule_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("condition_text", sa.String(length=256), nullable=True),
        sa.Column("percent", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("order_id", "sequence", name="uq_order_schedule_sequence"),
        sa.CheckConstraint(
            "(percent IS NOT NULL AND amount IS NULL) OR "
            "(amount IS NOT NULL AND percent IS NULL)",
            name="ck_order_schedule_percent_xor_amount",
        ),
        sa.CheckConstraint(
            "percent IS NULL OR percent > 0",
            name="ck_order_schedule_percent_positive",
        ),
        sa.CheckConstraint(
            "amount IS NULL OR amount > 0",
            name="ck_order_schedule_amount_positive",
        ),
        sa.CheckConstraint(
            "due_date IS NOT NULL OR "
            "(condition_text IS NOT NULL AND btrim(condition_text) <> '')",
            name="ck_order_schedule_when",
        ),
    )
    op.create_index(
        "ix_order_payment_schedule_lines_order_id",
        "order_payment_schedule_lines",
        ["order_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_payment_schedule_lines_order_id",
        table_name="order_payment_schedule_lines",
    )
    op.drop_table("order_payment_schedule_lines")
