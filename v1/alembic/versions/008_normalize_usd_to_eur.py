"""Normaliza moeda legada USD → EUR em importações e faturas.

Revision ID: 008
Revises: 007
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE importation_orders SET currency = 'EUR' WHERE UPPER(currency) = 'USD'")
    op.execute("UPDATE invoices SET currency = 'EUR' WHERE UPPER(currency) = 'USD'")
    op.execute("UPDATE suppliers SET currency_default = 'EUR' WHERE UPPER(currency_default) = 'USD'")
    op.execute("UPDATE payments SET currency_foreign = 'EUR' WHERE UPPER(currency_foreign) = 'USD'")
    op.execute(
        "UPDATE exchange_rates SET currency_from = 'EUR' WHERE UPPER(currency_from) = 'USD'"
    )


def downgrade() -> None:
    pass
