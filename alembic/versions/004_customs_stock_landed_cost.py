"""customs stock landed cost schema

Revision ID: 004
Revises: 003
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customs_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=16), nullable=False),
        sa.Column("document_number", sa.String(length=64), nullable=False),
        sa.Column("document_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("official_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["attachment_id"], ["document_attachments.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customs_documents_importation_id", "customs_documents", ["importation_id"])

    op.create_table(
        "taxes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("customs_document_id", sa.Integer(), nullable=False),
        sa.Column("tax_type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("source_document_attachment_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["customs_document_id"], ["customs_documents.id"]),
        sa.ForeignKeyConstraint(["source_document_attachment_id"], ["document_attachments.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taxes_importation_id", "taxes", ["importation_id"])

    op.create_table(
        "landed_cost_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_type", sa.String(length=32), nullable=False),
        sa.Column("is_current_version", sa.Boolean(), nullable=False),
        sa.Column("previous_version_id", sa.Integer(), nullable=True),
        sa.Column("trigger_event", sa.String(length=64), nullable=True),
        sa.Column("trigger_notes", sa.Text(), nullable=True),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["previous_version_id"], ["landed_cost_versions.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landed_cost_versions_importation_id", "landed_cost_versions", ["importation_id"])

    op.create_table(
        "nationalizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("customs_document_id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["customs_document_id"], ["customs_documents.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nationalizations_importation_id", "nationalizations", ["importation_id"])

    op.create_table(
        "nationalization_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nationalization_id", sa.Integer(), nullable=False),
        sa.Column("importation_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity_nationalized", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["nationalization_id"], ["nationalizations.id"]),
        sa.ForeignKeyConstraint(["importation_item_id"], ["importation_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nationalization_items_nationalization_id", "nationalization_items", ["nationalization_id"])

    op.create_table(
        "stock_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nationalization_id", sa.Integer(), nullable=False),
        sa.Column("importation_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("unit_cost_approved", sa.Numeric(18, 6), nullable=True),
        sa.Column("landed_cost_version_id", sa.Integer(), nullable=True),
        sa.Column("override_reason_code_id", sa.Integer(), nullable=True),
        sa.Column("override_justification", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["nationalization_id"], ["nationalizations.id"]),
        sa.ForeignKeyConstraint(["importation_item_id"], ["importation_items.id"]),
        sa.ForeignKeyConstraint(["landed_cost_version_id"], ["landed_cost_versions.id"]),
        sa.ForeignKeyConstraint(["override_reason_code_id"], ["reason_codes.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_entries_nationalization_id", "stock_entries", ["nationalization_id"])

    op.create_table(
        "quantity_discrepancies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("importation_item_id", sa.Integer(), nullable=True),
        sa.Column("stage_from", sa.String(length=32), nullable=False),
        sa.Column("stage_to", sa.String(length=32), nullable=False),
        sa.Column("expected_quantity", sa.Integer(), nullable=True),
        sa.Column("actual_quantity", sa.Integer(), nullable=True),
        sa.Column("difference", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("recorded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["importation_item_id"], ["importation_items.id"]),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quantity_discrepancies_importation_id", "quantity_discrepancies", ["importation_id"])

    op.create_table(
        "landed_cost_components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("landed_cost_version_id", sa.Integer(), nullable=False),
        sa.Column("component_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["landed_cost_version_id"], ["landed_cost_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landed_cost_components_landed_cost_version_id", "landed_cost_components", ["landed_cost_version_id"])

    op.create_table(
        "landed_cost_sku_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("landed_cost_version_id", sa.Integer(), nullable=False),
        sa.Column("importation_item_id", sa.Integer(), nullable=False),
        sa.Column("allocation_method", sa.String(length=16), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("quantity_basis", sa.Integer(), nullable=True),
        sa.Column("manual_reason_code_id", sa.Integer(), nullable=True),
        sa.Column("manual_justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["landed_cost_version_id"], ["landed_cost_versions.id"]),
        sa.ForeignKeyConstraint(["importation_item_id"], ["importation_items.id"]),
        sa.ForeignKeyConstraint(["manual_reason_code_id"], ["reason_codes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_landed_cost_sku_allocations_landed_cost_version_id",
        "landed_cost_sku_allocations",
        ["landed_cost_version_id"],
    )

    op.create_table(
        "landed_cost_variances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importation_id", sa.Integer(), nullable=False),
        sa.Column("version_from_id", sa.Integer(), nullable=False),
        sa.Column("version_to_id", sa.Integer(), nullable=False),
        sa.Column("variance_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["importation_id"], ["importation_orders.id"]),
        sa.ForeignKeyConstraint(["version_from_id"], ["landed_cost_versions.id"]),
        sa.ForeignKeyConstraint(["version_to_id"], ["landed_cost_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landed_cost_variances_importation_id", "landed_cost_variances", ["importation_id"])


def downgrade() -> None:
    op.drop_table("landed_cost_variances")
    op.drop_table("landed_cost_sku_allocations")
    op.drop_table("landed_cost_components")
    op.drop_table("quantity_discrepancies")
    op.drop_table("stock_entries")
    op.drop_table("nationalization_items")
    op.drop_table("nationalizations")
    op.drop_table("taxes")
    op.drop_table("landed_cost_versions")
    op.drop_table("customs_documents")
