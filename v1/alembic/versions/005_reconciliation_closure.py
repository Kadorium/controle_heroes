"""customs stock landed cost schema

Revision ID: 005
Revises: 004
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("importation_orders", sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "reconciliations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("pair_type", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("source_a_label", sa.String(length=128), nullable=True),
        sa.Column("source_a_value", sa.Text(), nullable=True),
        sa.Column("source_b_label", sa.String(length=128), nullable=True),
        sa.Column("source_b_value", sa.Text(), nullable=True),
        sa.Column("variance_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("tolerance_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("entity_ref", sa.String(length=128), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_reason_code_id", sa.Integer(), nullable=True),
        sa.Column("approval_justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approval_reason_code_id"], ["reason_codes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliations_importation_id", "reconciliations", ["importation_id"])

    op.create_table(
        "importation_closures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("closure_version", sa.Integer(), nullable=False),
        sa.Column("landed_cost_version_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("closure_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("closed_by_id", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_reason_code_id", sa.Integer(), nullable=True),
        sa.Column("close_justification", sa.Text(), nullable=True),
        sa.Column("approved_reconciliation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reopened_by_id", sa.Integer(), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopen_reason_code_id", sa.Integer(), nullable=True),
        sa.Column("reopen_justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["landed_cost_version_id"], ["landed_cost_versions.id"]),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["close_reason_code_id"], ["reason_codes.id"]),
        sa.ForeignKeyConstraint(["reopened_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reopen_reason_code_id"], ["reason_codes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_importation_closures_importation_id", "importation_closures", ["importation_id"])


def downgrade() -> None:
    op.drop_table("importation_closures")
    op.drop_table("reconciliations")
    op.drop_column("importation_orders", "reopened_at")
