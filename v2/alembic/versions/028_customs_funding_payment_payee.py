"""CUSTOMS-FUNDING — Payment sem Supplier + snapshots de favorecido.

Revision ID: 028
Revises: 027
Create Date: 2026-08-20

Additive. Payments Invoice existentes mantêm supplier_id.
Não persiste status derivado do FundingRequest.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("payee_display_name", sa.String(length=256), nullable=True))
    op.add_column("payments", sa.Column("payee_tax_id", sa.String(length=64), nullable=True))
    op.add_column("payables", sa.Column("payee_tax_id", sa.String(length=64), nullable=True))

    op.execute(
        """
        UPDATE payments AS p
        SET payee_display_name = s.name
        FROM suppliers AS s
        WHERE p.supplier_id = s.id
          AND (p.payee_display_name IS NULL OR btrim(p.payee_display_name) = '')
        """
    )

    op.alter_column("payments", "supplier_id", existing_type=sa.Integer(), nullable=True)

    op.create_check_constraint(
        "ck_payments_payee_identity",
        "payments",
        "(supplier_id IS NOT NULL) OR "
        "(payee_display_name IS NOT NULL AND btrim(payee_display_name) <> '')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payments_payee_identity", "payments", type_="check")
    op.execute("DELETE FROM payments WHERE supplier_id IS NULL")
    op.alter_column("payments", "supplier_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("payables", "payee_tax_id")
    op.drop_column("payments", "payee_tax_id")
    op.drop_column("payments", "payee_display_name")
