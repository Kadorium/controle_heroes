"""J#5 I5-3A — CustomsPayee + FundingRequest + value/tax/expense lines

Revision ID: 013
Revises: 012
Create Date: 2026-08-03

Sequência J#5:
  011 — ImportProcess (I5-1) DONE
  012 — Doganale versionada (I5-2) DONE
  013 — FundingRequest / Payee / linhas (I5-3A)
  014 — Payables Customs / FundingPayableLink (I5-3B)
  015 — Inventory (I5-4)

I5-3A NÃO cria Payable — isso é I5-3B.
"""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customs_payees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("tax_id", sa.String(64), nullable=True),
        sa.Column("bank_name", sa.String(256), nullable=True),
        sa.Column("agency", sa.String(64), nullable=True),
        sa.Column("account", sa.String(64), nullable=True),
        sa.Column("pix_key", sa.String(256), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_customs_payees_name", "customs_payees", ["name"])

    op.create_table(
        "customs_funding_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payee_id",
            sa.Integer(),
            sa.ForeignKey("customs_payees.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("declared_total", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')",
            name="ck_customs_funding_requests_status",
        ),
        sa.UniqueConstraint(
            "process_id",
            "idempotency_key",
            name="uq_customs_funding_requests_idem",
        ),
    )
    op.create_index(
        "ix_customs_funding_requests_process_id",
        "customs_funding_requests",
        ["process_id"],
    )
    op.create_index(
        "ix_customs_funding_requests_payee_id",
        "customs_funding_requests",
        ["payee_id"],
    )
    op.create_index(
        "ix_customs_funding_requests_status",
        "customs_funding_requests",
        ["status"],
    )

    op.create_table(
        "customs_value_bases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "funding_request_id",
            sa.Integer(),
            sa.ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(256), nullable=True),
        sa.Column("code", sa.String(64), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "funding_request_id",
            "position",
            name="uq_customs_value_bases_pos",
        ),
    )
    op.create_index(
        "ix_customs_value_bases_funding_request_id",
        "customs_value_bases",
        ["funding_request_id"],
    )

    op.create_table(
        "customs_tax_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "funding_request_id",
            sa.Integer(),
            sa.ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(256), nullable=True),
        sa.Column("code", sa.String(64), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "funding_request_id",
            "position",
            name="uq_customs_tax_lines_pos",
        ),
    )
    op.create_index(
        "ix_customs_tax_lines_funding_request_id",
        "customs_tax_lines",
        ["funding_request_id"],
    )

    op.create_table(
        "customs_expense_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "funding_request_id",
            sa.Integer(),
            sa.ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(256), nullable=True),
        sa.Column("code", sa.String(64), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "funding_request_id",
            "position",
            name="uq_customs_expense_lines_pos",
        ),
    )
    op.create_index(
        "ix_customs_expense_lines_funding_request_id",
        "customs_expense_lines",
        ["funding_request_id"],
    )


def downgrade() -> None:
    op.drop_table("customs_expense_lines")
    op.drop_table("customs_tax_lines")
    op.drop_table("customs_value_bases")
    op.drop_table("customs_funding_requests")
    op.drop_table("customs_payees")
