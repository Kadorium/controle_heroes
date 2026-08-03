"""J#5 I5-2 — Doganale versionada + lines + divergences + provenance

Revision ID: 012
Revises: 011
Create Date: 2026-08-03

Sequência J#5:
  011 — ImportProcess (I5-1) DONE
  012 — Doganale versionada (I5-2)
  013 — FundingRequest / Payee / linhas (I5-3A)
  014 — Payables Customs / FundingPayableLink (I5-3B)
  015 — Inventory (I5-4)
"""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customs_doganales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("process_id", name="uq_customs_doganales_process_id"),
    )
    op.create_index("ix_customs_doganales_process_id", "customs_doganales", ["process_id"])

    op.create_table(
        "customs_doganale_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doganale_id",
            sa.Integer(),
            sa.ForeignKey("customs_doganales.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'SUPERSEDED', 'CANCELLED')",
            name="ck_customs_doganale_versions_status",
        ),
        sa.CheckConstraint("version_number > 0", name="ck_customs_doganale_versions_num"),
        sa.UniqueConstraint(
            "doganale_id",
            "version_number",
            name="uq_customs_doganale_versions_num",
        ),
        sa.UniqueConstraint(
            "doganale_id",
            "idempotency_key",
            name="uq_customs_doganale_versions_idem",
        ),
    )
    op.create_index(
        "ix_customs_doganale_versions_doganale_id",
        "customs_doganale_versions",
        ["doganale_id"],
    )
    op.create_index(
        "ix_customs_doganale_versions_status",
        "customs_doganale_versions",
        ["status"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_customs_doganale_one_current
        ON customs_doganale_versions (doganale_id)
        WHERE is_current IS TRUE
        """
    )

    op.create_table(
        "customs_doganale_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("customs_doganale_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("ncm", sa.String(16), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("line_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("manufacturer", sa.String(256), nullable=True),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("acquisition_country", sa.String(2), nullable=True),
        sa.Column("net_weight_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("gross_weight_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("pallet_count", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "invoice_item_id",
            sa.Integer(),
            sa.ForeignKey("invoice_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("version_id", "position", name="uq_customs_doganale_lines_pos"),
    )
    op.create_index(
        "ix_customs_doganale_lines_version_id",
        "customs_doganale_lines",
        ["version_id"],
    )

    op.create_table(
        "customs_divergences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doganale_version_id",
            sa.Integer(),
            sa.ForeignKey("customs_doganale_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "doganale_line_id",
            sa.Integer(),
            sa.ForeignKey("customs_doganale_lines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="INFO"),
        sa.Column("field_name", sa.String(64), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("actual_value", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('INFO', 'WARN', 'ERROR')",
            name="ck_customs_divergences_severity",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="ck_customs_divergences_status",
        ),
    )
    op.create_index("ix_customs_divergences_process_id", "customs_divergences", ["process_id"])

    op.create_table(
        "customs_provenances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("import_processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(64), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("adapter_key", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "source_kind",
            name="uq_customs_provenances_entity_source",
        ),
    )
    op.create_index("ix_customs_provenances_process_id", "customs_provenances", ["process_id"])


def downgrade() -> None:
    op.drop_table("customs_provenances")
    op.drop_table("customs_divergences")
    op.drop_table("customs_doganale_lines")
    op.execute("DROP INDEX IF EXISTS uq_customs_doganale_one_current")
    op.drop_table("customs_doganale_versions")
    op.drop_table("customs_doganales")
