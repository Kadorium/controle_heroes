"""J#5 I5-3B — Payable Customs extension + FundingPayableLink

Revision ID: 014
Revises: 013
Create Date: 2026-08-03

Sequência J#5:
  011 — ImportProcess (I5-1) DONE
  012 — Doganale versionada (I5-2) DONE
  013 — FundingRequest / Payee / linhas (I5-3A) DONE
  014 — Payables Customs / FundingPayableLink (I5-3B)
  015 — Inventory (I5-4)

Customs cria Payable via billing.public; NÃO cria Payment/Allocation.
Customs payables ficam OPEN na AP mas NÃO entram em list_eligible_payables
(INNER JOIN Invoice) — gap intencional (sem redesign Treasury).
"""

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("payables", "invoice_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("payables", "payment_term_id", existing_type=sa.Integer(), nullable=True)

    op.add_column(
        "payables",
        sa.Column("source_type", sa.String(32), nullable=False, server_default="INVOICE"),
    )
    op.add_column("payables", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("payables", sa.Column("payee_display_name", sa.String(256), nullable=True))

    op.execute("UPDATE payables SET source_id = invoice_id WHERE source_id IS NULL")

    op.drop_constraint("uq_payable_invoice_sequence", "payables", type_="unique")
    op.create_index(
        "uq_payable_invoice_sequence",
        "payables",
        ["invoice_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("invoice_id IS NOT NULL"),
    )
    op.create_index(
        "uq_payable_source_sequence",
        "payables",
        ["source_type", "source_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("source_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_payables_customs_invoice_null",
        "payables",
        "source_type <> 'CUSTOMS_FUNDING' OR invoice_id IS NULL",
    )
    op.create_index("ix_payables_source_type", "payables", ["source_type"])
    op.alter_column("payables", "source_type", server_default=None)

    op.create_table(
        "funding_payable_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "funding_request_id",
            sa.Integer(),
            sa.ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payable_id",
            sa.Integer(),
            sa.ForeignKey("payables.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "funding_request_id", "payable_id", name="uq_funding_payable_link_pair"
        ),
        sa.UniqueConstraint(
            "funding_request_id", "sequence", name="uq_funding_payable_link_seq"
        ),
    )
    op.create_index(
        "ix_funding_payable_links_funding_request_id",
        "funding_payable_links",
        ["funding_request_id"],
    )
    op.create_index(
        "ix_funding_payable_links_payable_id",
        "funding_payable_links",
        ["payable_id"],
    )


def downgrade() -> None:
    op.drop_table("funding_payable_links")

    op.drop_constraint("ck_payables_customs_invoice_null", "payables", type_="check")
    op.drop_index("ix_payables_source_type", table_name="payables")
    op.drop_index("uq_payable_source_sequence", table_name="payables")
    op.drop_index("uq_payable_invoice_sequence", table_name="payables")

    op.execute("DELETE FROM payables WHERE invoice_id IS NULL")
    op.alter_column("payables", "payment_term_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("payables", "invoice_id", existing_type=sa.Integer(), nullable=False)

    op.create_unique_constraint(
        "uq_payable_invoice_sequence", "payables", ["invoice_id", "sequence"]
    )
    op.drop_column("payables", "payee_display_name")
    op.drop_column("payables", "source_id")
    op.drop_column("payables", "source_type")
