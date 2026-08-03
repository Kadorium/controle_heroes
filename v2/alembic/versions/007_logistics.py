"""logistics J#4 — shipments + packages + refs + summaries

Revision ID: 007
Revises: 006
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PLANNED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modal", sa.String(32), nullable=True),
        sa.Column("origin", sa.String(128), nullable=True),
        sa.Column("destination", sa.String(128), nullable=True),
        sa.Column("carrier", sa.String(128), nullable=True),
        sa.Column("planned_departure", sa.Date(), nullable=True),
        sa.Column("planned_arrival", sa.Date(), nullable=True),
        sa.Column("actual_departure", sa.Date(), nullable=True),
        sa.Column("actual_arrival", sa.Date(), nullable=True),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('PLANNED', 'BOOKED', 'IN_TRANSIT', 'ARRIVED')",
            name="ck_shipments_status",
        ),
    )
    op.create_index("ix_shipments_code", "shipments", ["code"], unique=True)
    op.create_index("ix_shipments_status", "shipments", ["status"])

    op.create_table(
        "shipment_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "order_item_id",
            sa.Integer(),
            sa.ForeignKey("order_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_shipment_items_qty"),
        sa.UniqueConstraint("shipment_id", "order_item_id", name="uq_shipment_item_order_item"),
    )
    op.create_index("ix_shipment_items_shipment_id", "shipment_items", ["shipment_id"])
    op.create_index("ix_shipment_items_order_item_id", "shipment_items", ["order_item_id"])

    op.create_table(
        "shipment_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "parent_package_id",
            sa.Integer(),
            sa.ForeignKey("shipment_packages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_package_no", sa.String(64), nullable=True),
        sa.Column("package_type", sa.String(16), nullable=False),
        sa.Column("package_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("packaging_ncm", sa.String(16), nullable=True),
        sa.Column("length", sa.Numeric(18, 4), nullable=True),
        sa.Column("width", sa.Numeric(18, 4), nullable=True),
        sa.Column("height", sa.Numeric(18, 4), nullable=True),
        sa.Column("dimension_unit", sa.String(8), nullable=True),
        sa.Column("raw_dimensions", sa.String(128), nullable=True),
        sa.Column("net_weight_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("gross_weight_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("volume_m3", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume_is_derived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "package_type IN ('PALLET', 'CARTON', 'BOX', 'OTHER')",
            name="ck_shipment_packages_type",
        ),
        sa.CheckConstraint("package_count > 0", name="ck_shipment_packages_count"),
        sa.CheckConstraint(
            "parent_package_id IS NULL OR package_count = 1",
            name="ck_shipment_packages_parent_count",
        ),
    )
    op.create_index("ix_shipment_packages_shipment_id", "shipment_packages", ["shipment_id"])
    op.create_index(
        "uq_shipment_packages_ext_no",
        "shipment_packages",
        ["shipment_id", "external_package_no"],
        unique=True,
        postgresql_where=sa.text("external_package_no IS NOT NULL"),
    )

    op.create_table(
        "shipment_package_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "package_id",
            sa.Integer(),
            sa.ForeignKey("shipment_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shipment_item_id",
            sa.Integer(),
            sa.ForeignKey("shipment_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("contained_quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("source_unit", sa.String(16), nullable=True),
        sa.Column("source_line_reference", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("package_id", "shipment_item_id", name="uq_pkg_content_item"),
    )
    op.create_index("ix_shipment_package_contents_package_id", "shipment_package_contents", ["package_id"])
    op.create_index(
        "ix_shipment_package_contents_shipment_item_id",
        "shipment_package_contents",
        ["shipment_item_id"],
    )

    op.create_table(
        "shipment_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_type", sa.String(32), nullable=False),
        sa.Column("reference_value", sa.String(128), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "reference_type IN ("
            "'PACKING_LIST','DDT','BL','AWB','BOOKING','CONTAINER',"
            "'FORWARDER_REFERENCE','OTHER')",
            name="ck_shipment_references_type",
        ),
        sa.UniqueConstraint(
            "shipment_id",
            "reference_type",
            "reference_value",
            name="uq_shipment_reference",
        ),
    )
    op.create_index("ix_shipment_references_shipment_id", "shipment_references", ["shipment_id"])
    op.create_index(
        "ix_shipment_references_type_value",
        "shipment_references",
        ["reference_type", "reference_value"],
    )

    op.create_table(
        "shipment_document_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("declared_net_weight_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("declared_gross_weight_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("declared_pallet_count", sa.Integer(), nullable=True),
        sa.Column("declared_carton_count", sa.Integer(), nullable=True),
        sa.Column("declared_volume_m3", sa.Numeric(18, 6), nullable=True),
        sa.Column("raw_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("shipment_id", "document_id", name="uq_shipment_doc_summary"),
    )
    op.create_index(
        "ix_shipment_document_summaries_shipment_id",
        "shipment_document_summaries",
        ["shipment_id"],
    )


def downgrade() -> None:
    op.drop_table("shipment_document_summaries")
    op.drop_table("shipment_references")
    op.drop_table("shipment_package_contents")
    op.drop_index("uq_shipment_packages_ext_no", table_name="shipment_packages")
    op.drop_table("shipment_packages")
    op.drop_table("shipment_items")
    op.drop_table("shipments")
