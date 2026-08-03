"""J4-UX2 — PackageContent documentary snapshots + DocumentSummary provenance

Revision ID: 009
Revises: 008
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

_PROVENANCE_CHECK = (
    "declared_provenance IS NULL OR declared_provenance IN ("
    "'PACKING_LIST','FATTURA_DOGANALE','MANUAL','OTHER')"
)


def upgrade() -> None:
    op.add_column(
        "shipment_package_contents",
        sa.Column("source_ncm", sa.String(16), nullable=True),
    )
    op.add_column(
        "shipment_package_contents",
        sa.Column("source_description", sa.String(512), nullable=True),
    )
    op.add_column(
        "shipment_package_contents",
        sa.Column("units_per_package", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "shipment_package_contents",
        sa.Column("unit_net_weight_kg", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "shipment_package_contents",
        sa.Column("unit_gross_weight_kg", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "shipment_package_contents",
        sa.Column("source_total_net_weight_kg", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "shipment_package_contents",
        sa.Column("source_total_gross_weight_kg", sa.Numeric(18, 4), nullable=True),
    )

    op.add_column(
        "shipment_document_summaries",
        sa.Column("declared_provenance", sa.String(32), nullable=True),
    )
    op.create_check_constraint(
        "ck_shipment_doc_summary_provenance",
        "shipment_document_summaries",
        _PROVENANCE_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_shipment_doc_summary_provenance",
        "shipment_document_summaries",
        type_="check",
    )
    op.drop_column("shipment_document_summaries", "declared_provenance")
    op.drop_column("shipment_package_contents", "source_total_gross_weight_kg")
    op.drop_column("shipment_package_contents", "source_total_net_weight_kg")
    op.drop_column("shipment_package_contents", "unit_gross_weight_kg")
    op.drop_column("shipment_package_contents", "unit_net_weight_kg")
    op.drop_column("shipment_package_contents", "units_per_package")
    op.drop_column("shipment_package_contents", "source_description")
    op.drop_column("shipment_package_contents", "source_ncm")
