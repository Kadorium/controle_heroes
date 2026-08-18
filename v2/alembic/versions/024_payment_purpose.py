"""J4-FIN-CICLO-FIX C1 — Payment.purpose ADVANCE vs SETTLEMENT.

Adiantamento nasce no painel /orders/{id}/advances e continua adiantamento
depois de aplicado. Pagamento de saldo (Pagar saldo restante) é SETTLEMENT
mesmo com order_id. Backfill: FX audit order_advance= ou reason ORDER_ADVANCE.

Revision ID: 024
Revises: 023
Create Date: 2026-08-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("purpose", sa.String(length=16), nullable=True))
    op.create_index("ix_payments_purpose", "payments", ["purpose"])
    op.create_check_constraint(
        "ck_payments_purpose",
        "payments",
        "purpose IS NULL OR purpose IN ('ADVANCE', 'SETTLEMENT')",
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE payments AS p
            SET purpose = 'ADVANCE'
            WHERE EXISTS (
                SELECT 1
                FROM fx_executions fe
                JOIN audit_log a
                  ON a.entity_type = 'fx_execution'
                 AND a.entity_id = CAST(fe.id AS VARCHAR)
                 AND a.action = 'fx.realized.register'
                 AND a.details LIKE '%order_advance=%'
                WHERE fe.payment_id = p.id
            )
            OR EXISTS (
                SELECT 1
                FROM audit_log a
                WHERE a.entity_type = 'payment'
                  AND a.entity_id = CAST(p.id AS VARCHAR)
                  AND a.action = 'register'
                  AND a.reason_code = 'ORDER_ADVANCE'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE payments
            SET purpose = 'SETTLEMENT'
            WHERE order_id IS NOT NULL AND purpose IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("ck_payments_purpose", "payments", type_="check")
    op.drop_index("ix_payments_purpose", table_name="payments")
    op.drop_column("payments", "purpose")
