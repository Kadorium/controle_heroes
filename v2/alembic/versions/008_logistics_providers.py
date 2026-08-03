"""J4-UX1 — logistics providers + controlled modal + carrier snapshot

Revision ID: 008
Revises: 007
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

_MODAL_CHECK = (
    "modal IS NULL OR modal IN ("
    "'SEA','AIR','ROAD','COURIER','MULTIMODAL','OTHER')"
)
_PROVIDER_TYPE_CHECK = (
    "provider_type IN ("
    "'TRANSPORTADOR','ARMADOR','FREIGHT_FORWARDER',"
    "'OPERADOR_LOGISTICO','DESPACHANTE')"
)


def upgrade() -> None:
    op.create_table(
        "logistics_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("trade_name", sa.String(255), nullable=True),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(_PROVIDER_TYPE_CHECK, name="ck_logistics_providers_type"),
    )
    op.create_index(
        "ix_logistics_providers_type_active",
        "logistics_providers",
        ["provider_type", "active"],
    )

    op.alter_column(
        "shipments",
        "carrier",
        new_column_name="carrier_name_snapshot",
        existing_type=sa.String(128),
        existing_nullable=True,
    )

    op.add_column(
        "shipments",
        sa.Column(
            "logistics_provider_id",
            sa.Integer(),
            sa.ForeignKey("logistics_providers.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_shipments_logistics_provider_id",
        "shipments",
        ["logistics_provider_id"],
    )
    op.create_index("ix_shipments_modal", "shipments", ["modal"])

    op.create_check_constraint("ck_shipments_modal", "shipments", _MODAL_CHECK)


def downgrade() -> None:
    op.drop_constraint("ck_shipments_modal", "shipments", type_="check")
    op.drop_index("ix_shipments_modal", table_name="shipments")
    op.drop_index("ix_shipments_logistics_provider_id", table_name="shipments")
    op.drop_column("shipments", "logistics_provider_id")
    op.alter_column(
        "shipments",
        "carrier_name_snapshot",
        new_column_name="carrier",
        existing_type=sa.String(128),
        existing_nullable=True,
    )
    op.drop_index("ix_logistics_providers_type_active", table_name="logistics_providers")
    op.drop_table("logistics_providers")
