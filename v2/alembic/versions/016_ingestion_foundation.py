"""J3-I0 — Ingestion foundation (Batch / Blob / Occurrence)

Revision ID: 016
Revises: 015
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_by_actor_id", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_ingestion_batches_status"),
    )
    op.create_index("ix_ingestion_batches_status", "ingestion_batches", ["status"])

    op.create_table(
        "ingestion_blobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detected_mime", sa.String(128), nullable=True),
        sa.Column("physical_status", sa.String(32), nullable=False, server_default="PRESENT"),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "physical_status IN ('PRESENT', 'PURGED')",
            name="ck_ingestion_blobs_physical_status",
        ),
        sa.UniqueConstraint("sha256", name="uq_ingestion_blobs_sha256"),
    )
    op.create_index("ix_ingestion_blobs_sha256", "ingestion_blobs", ["sha256"])
    op.create_index("ix_ingestion_blobs_physical_status", "ingestion_blobs", ["physical_status"])

    op.create_table(
        "ingestion_occurrences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "blob_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_blobs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="RECEIVED"),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("declared_mime", sa.String(128), nullable=True),
        sa.Column("detected_mime", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("client_upload_key", sa.String(128), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("physical_reuse", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rehydrated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bytes_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_actor_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ("
            "'RECEIVED', 'VALIDATING', 'STORED', 'REJECTED', 'FAILED', 'ABANDONED'"
            ")",
            name="ck_ingestion_occurrences_status",
        ),
    )
    op.create_index("ix_ingestion_occurrences_batch_id", "ingestion_occurrences", ["batch_id"])
    op.create_index("ix_ingestion_occurrences_blob_id", "ingestion_occurrences", ["blob_id"])
    op.create_index("ix_ingestion_occurrences_status", "ingestion_occurrences", ["status"])
    op.create_index("ix_ingestion_occurrences_sha256", "ingestion_occurrences", ["sha256"])
    op.create_index(
        "ix_ingestion_occurrences_retain_until",
        "ingestion_occurrences",
        ["retain_until"],
    )
    # Partial unique: only when client_upload_key is present
    op.create_index(
        "uq_ingestion_occurrences_batch_client_key",
        "ingestion_occurrences",
        ["batch_id", "client_upload_key"],
        unique=True,
        postgresql_where=sa.text("client_upload_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_ingestion_occurrences_batch_client_key",
        table_name="ingestion_occurrences",
    )
    op.drop_index("ix_ingestion_occurrences_retain_until", table_name="ingestion_occurrences")
    op.drop_index("ix_ingestion_occurrences_sha256", table_name="ingestion_occurrences")
    op.drop_index("ix_ingestion_occurrences_status", table_name="ingestion_occurrences")
    op.drop_index("ix_ingestion_occurrences_blob_id", table_name="ingestion_occurrences")
    op.drop_index("ix_ingestion_occurrences_batch_id", table_name="ingestion_occurrences")
    op.drop_table("ingestion_occurrences")
    op.drop_index("ix_ingestion_blobs_physical_status", table_name="ingestion_blobs")
    op.drop_index("ix_ingestion_blobs_sha256", table_name="ingestion_blobs")
    op.drop_table("ingestion_blobs")
    op.drop_index("ix_ingestion_batches_status", table_name="ingestion_batches")
    op.drop_table("ingestion_batches")
