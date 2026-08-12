"""J3-I1 — Ingestion staging IR (Document / Section / Field / Row / Issue / Set)

Revision ID: 017
Revises: 016
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_document_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("projection_key", sa.String(128), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("created_by_actor_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ingestion_document_sets_batch_id", "ingestion_document_sets", ["batch_id"])
    op.create_index(
        "ix_ingestion_document_sets_projection_key",
        "ingestion_document_sets",
        ["projection_key"],
    )

    op.create_table(
        "ingestion_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "occurrence_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_occurrences.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_set_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_document_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("adapter_id", sa.String(128), nullable=False, server_default="contract_stub_v1"),
        sa.Column("adapter_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("ir_schema_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("locked_by_actor_id", sa.String(64), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_actor_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "review_status IN ('DRAFT', 'IN_REVIEW', 'READY', 'REJECTED')",
            name="ck_ingestion_documents_review_status",
        ),
        sa.UniqueConstraint("occurrence_id", name="uq_ingestion_documents_occurrence"),
    )
    op.create_index("ix_ingestion_documents_occurrence_id", "ingestion_documents", ["occurrence_id"])
    op.create_index("ix_ingestion_documents_batch_id", "ingestion_documents", ["batch_id"])
    op.create_index(
        "ix_ingestion_documents_document_set_id", "ingestion_documents", ["document_set_id"]
    )
    op.create_index("ix_ingestion_documents_doc_type", "ingestion_documents", ["doc_type"])
    op.create_index(
        "ix_ingestion_documents_review_status", "ingestion_documents", ["review_status"]
    )

    op.create_table(
        "ingestion_document_set_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_set_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_document_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "document_set_id",
            "document_id",
            name="uq_ingestion_document_set_members_set_doc",
        ),
    )
    op.create_index(
        "ix_ingestion_document_set_members_document_set_id",
        "ingestion_document_set_members",
        ["document_set_id"],
    )
    op.create_index(
        "ix_ingestion_document_set_members_document_id",
        "ingestion_document_set_members",
        ["document_id"],
    )

    op.create_table(
        "ingestion_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'CORRECTED', 'REJECTED')",
            name="ck_ingestion_sections_review_status",
        ),
        sa.UniqueConstraint("document_id", "section_key", name="uq_ingestion_sections_doc_key"),
    )
    op.create_index("ix_ingestion_sections_document_id", "ingestion_sections", ["document_id"])

    op.create_table(
        "ingestion_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("value_type", sa.String(32), nullable=False, server_default="string"),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("corrected_value", sa.Text(), nullable=True),
        sa.Column("locator_json", sa.Text(), nullable=True),
        sa.Column("provenance_json", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'CORRECTED', 'REJECTED')",
            name="ck_ingestion_fields_review_status",
        ),
        sa.UniqueConstraint("document_id", "field_key", name="uq_ingestion_fields_doc_key"),
    )
    op.create_index("ix_ingestion_fields_document_id", "ingestion_fields", ["document_id"])
    op.create_index("ix_ingestion_fields_section_id", "ingestion_fields", ["section_id"])
    op.create_index("ix_ingestion_fields_review_status", "ingestion_fields", ["review_status"])

    op.create_table(
        "ingestion_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("row_key", sa.String(128), nullable=True),
        sa.Column("cells_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'CORRECTED', 'REJECTED')",
            name="ck_ingestion_rows_review_status",
        ),
        sa.UniqueConstraint("document_id", "row_index", name="uq_ingestion_rows_doc_index"),
    )
    op.create_index("ix_ingestion_rows_document_id", "ingestion_rows", ["document_id"])
    op.create_index("ix_ingestion_rows_section_id", "ingestion_rows", ["section_id"])
    op.create_index("ix_ingestion_rows_review_status", "ingestion_rows", ["review_status"])

    op.create_table(
        "ingestion_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(16), nullable=False, server_default="ERROR"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False, server_default="DOCUMENT"),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("locator_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "severity IN ('ERROR', 'WARNING', 'INFO')",
            name="ck_ingestion_issues_severity",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="ck_ingestion_issues_status",
        ),
        sa.CheckConstraint(
            "target_type IN ('DOCUMENT', 'SECTION', 'FIELD', 'ROW')",
            name="ck_ingestion_issues_target_type",
        ),
    )
    op.create_index("ix_ingestion_issues_document_id", "ingestion_issues", ["document_id"])
    op.create_index("ix_ingestion_issues_code", "ingestion_issues", ["code"])
    op.create_index("ix_ingestion_issues_status", "ingestion_issues", ["status"])

    op.create_table(
        "ingestion_review_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("previous_review_status", sa.String(32), nullable=True),
        sa.Column("new_review_status", sa.String(32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "target_type IN ('FIELD', 'ROW', 'SECTION', 'DOCUMENT')",
            name="ck_ingestion_review_changes_target_type",
        ),
    )
    op.create_index(
        "ix_ingestion_review_changes_document_id",
        "ingestion_review_changes",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_review_changes_document_id", table_name="ingestion_review_changes")
    op.drop_table("ingestion_review_changes")
    op.drop_index("ix_ingestion_issues_status", table_name="ingestion_issues")
    op.drop_index("ix_ingestion_issues_code", table_name="ingestion_issues")
    op.drop_index("ix_ingestion_issues_document_id", table_name="ingestion_issues")
    op.drop_table("ingestion_issues")
    op.drop_index("ix_ingestion_rows_review_status", table_name="ingestion_rows")
    op.drop_index("ix_ingestion_rows_section_id", table_name="ingestion_rows")
    op.drop_index("ix_ingestion_rows_document_id", table_name="ingestion_rows")
    op.drop_table("ingestion_rows")
    op.drop_index("ix_ingestion_fields_review_status", table_name="ingestion_fields")
    op.drop_index("ix_ingestion_fields_section_id", table_name="ingestion_fields")
    op.drop_index("ix_ingestion_fields_document_id", table_name="ingestion_fields")
    op.drop_table("ingestion_fields")
    op.drop_index("ix_ingestion_sections_document_id", table_name="ingestion_sections")
    op.drop_table("ingestion_sections")
    op.drop_index(
        "ix_ingestion_document_set_members_document_id",
        table_name="ingestion_document_set_members",
    )
    op.drop_index(
        "ix_ingestion_document_set_members_document_set_id",
        table_name="ingestion_document_set_members",
    )
    op.drop_table("ingestion_document_set_members")
    op.drop_index("ix_ingestion_documents_review_status", table_name="ingestion_documents")
    op.drop_index("ix_ingestion_documents_doc_type", table_name="ingestion_documents")
    op.drop_index("ix_ingestion_documents_document_set_id", table_name="ingestion_documents")
    op.drop_index("ix_ingestion_documents_batch_id", table_name="ingestion_documents")
    op.drop_index("ix_ingestion_documents_occurrence_id", table_name="ingestion_documents")
    op.drop_table("ingestion_documents")
    op.drop_index("ix_ingestion_document_sets_projection_key", table_name="ingestion_document_sets")
    op.drop_index("ix_ingestion_document_sets_batch_id", table_name="ingestion_document_sets")
    op.drop_table("ingestion_document_sets")
