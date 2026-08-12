"""J3-I7 — Ingestion metrics events table.

Minimal event table for per-adapter+version metrics:
classification rate, field coverage, human corrections, matching, commits, retries.

Revision ID: 019
Revises: 018
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_metric_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("adapter_id", sa.String(128), nullable=False),
        sa.Column("adapter_version", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("occurrence_id", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'ADAPTER_RUN','COMMIT_ATTEMPT','COMMIT_COMPLETE',"
            "'FIELD_CORRECTED','MATCHING_RESULT','REVIEW_COMPLETE','RETRY'"
            ")",
            name="ck_ingestion_metric_events_event_type",
        ),
    )
    op.create_index(
        "ix_ingestion_metric_events_adapter",
        "ingestion_metric_events",
        ["adapter_id", "adapter_version"],
    )
    op.create_index(
        "ix_ingestion_metric_events_event_type",
        "ingestion_metric_events",
        ["event_type"],
    )
    op.create_index(
        "ix_ingestion_metric_events_document_id",
        "ingestion_metric_events",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_metric_events_document_id", table_name="ingestion_metric_events")
    op.drop_index("ix_ingestion_metric_events_event_type", table_name="ingestion_metric_events")
    op.drop_index("ix_ingestion_metric_events_adapter", table_name="ingestion_metric_events")
    op.drop_table("ingestion_metric_events")
