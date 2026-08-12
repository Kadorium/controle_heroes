"""J4-FIN FIN-3 — IBAN/banco de pagamento + scadenze literais do documento.

IBAN da linha de Pagamento (não rodapé). Copiado Invoice → Payable na emissão.
terms_from_document trava modo PERCENT quando as scadenze vieram da Fattura.

Revision ID: 023
Revises: 022
Create Date: 2026-08-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("destination_iban", sa.String(length=34), nullable=True))
    op.add_column("invoices", sa.Column("destination_bank", sa.String(length=128), nullable=True))
    op.add_column(
        "invoices",
        sa.Column(
            "terms_from_document",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("payables", sa.Column("destination_iban", sa.String(length=34), nullable=True))
    op.add_column("payables", sa.Column("destination_bank", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("payables", "destination_bank")
    op.drop_column("payables", "destination_iban")
    op.drop_column("invoices", "terms_from_document")
    op.drop_column("invoices", "destination_bank")
    op.drop_column("invoices", "destination_iban")
