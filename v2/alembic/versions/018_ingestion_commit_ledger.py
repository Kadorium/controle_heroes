"""J3-I3 — Ingestion commit ledger (IngestionCommitAttempt / IngestionCommitOperation)

Revision ID: 018
Revises: 017
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_commit_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("operation_key", sa.String(128), nullable=False),
        sa.Column("payload_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED', 'PARTIAL', 'FAILED', 'UNKNOWN')",
            name="ck_ingestion_commit_attempts_status",
        ),
        sa.UniqueConstraint("operation_key", name="uq_ingestion_commit_attempts_opkey"),
    )
    op.create_index(
        "ix_ingestion_commit_attempts_document_id",
        "ingestion_commit_attempts",
        ["document_id"],
    )
    op.create_index(
        "ix_ingestion_commit_attempts_status",
        "ingestion_commit_attempts",
        ["status"],
    )

    op.create_table(
        "ingestion_commit_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_commit_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("op_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED', 'FAILED', 'UNKNOWN', 'SKIPPED')",
            name="ck_ingestion_commit_operations_status",
        ),
        sa.UniqueConstraint(
            "attempt_id", "op_key", name="uq_ingestion_commit_operations_attempt_key"
        ),
    )
    op.create_index(
        "ix_ingestion_commit_operations_attempt_id",
        "ingestion_commit_operations",
        ["attempt_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_commit_operations_attempt_id",
        table_name="ingestion_commit_operations",
    )
    op.drop_table("ingestion_commit_operations")
    op.drop_index(
        "ix_ingestion_commit_attempts_status",
        table_name="ingestion_commit_attempts",
    )
    op.drop_index(
        "ix_ingestion_commit_attempts_document_id",
        table_name="ingestion_commit_attempts",
    )
    op.drop_table("ingestion_commit_attempts")
