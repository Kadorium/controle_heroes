"""product master fields — lifecycle, grupo, fiscal, archive

Revision ID: 011
Revises: 010
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("lifecycle_status", sa.String(32), nullable=False, server_default="ACTIVE"),
    )
    op.add_column(
        "products",
        sa.Column("product_group", sa.String(64), nullable=False, server_default="Sem grupo"),
    )
    op.add_column("products", sa.Column("product_subgroup", sa.String(64), nullable=True))
    op.add_column("products", sa.Column("supplier_code", sa.String(128), nullable=True))
    op.add_column("products", sa.Column("default_supplier_id", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("country_of_origin", sa.String(8), nullable=True))
    op.add_column("products", sa.Column("unit_of_measure", sa.String(16), nullable=True))
    op.add_column("products", sa.Column("fiscal_description", sa.Text(), nullable=True))
    op.add_column(
        "products",
        sa.Column("fiscal_review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("products", sa.Column("launch_date", sa.Date(), nullable=True))
    op.add_column("products", sa.Column("commercial_notes", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("archived_by_id", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("archive_reason", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_products_default_supplier_id",
        "products",
        "suppliers",
        ["default_supplier_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_products_archived_by_id",
        "products",
        "users",
        ["archived_by_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            "UPDATE products SET product_group = 'Sem grupo' "
            "WHERE product_group IS NULL OR TRIM(product_group) = ''"
        )
    )
    op.execute(
        sa.text(
            "UPDATE products SET lifecycle_status = 'ACTIVE' "
            "WHERE lifecycle_status IS NULL OR TRIM(lifecycle_status) = ''"
        )
    )
    op.execute(
        sa.text(
            "UPDATE products SET lifecycle_status = 'ARCHIVED' "
            "WHERE is_active = false AND cancelled_at IS NOT NULL"
        )
    )

    op.create_index("ix_products_lifecycle_status", "products", ["lifecycle_status"])
    op.create_index("ix_products_product_group", "products", ["product_group"])
    op.create_index("ix_products_ncm", "products", ["ncm"])
    op.create_index("ix_products_default_supplier_id", "products", ["default_supplier_id"])
    op.create_index("ix_products_supplier_code", "products", ["supplier_code"])


def downgrade() -> None:
    op.drop_index("ix_products_supplier_code", table_name="products")
    op.drop_index("ix_products_default_supplier_id", table_name="products")
    op.drop_index("ix_products_ncm", table_name="products")
    op.drop_index("ix_products_product_group", table_name="products")
    op.drop_index("ix_products_lifecycle_status", table_name="products")
    op.drop_constraint("fk_products_archived_by_id", "products", type_="foreignkey")
    op.drop_constraint("fk_products_default_supplier_id", "products", type_="foreignkey")
    for col in (
        "archive_reason",
        "archived_by_id",
        "archived_at",
        "commercial_notes",
        "launch_date",
        "fiscal_review_required",
        "fiscal_description",
        "unit_of_measure",
        "country_of_origin",
        "default_supplier_id",
        "supplier_code",
        "product_subgroup",
        "product_group",
        "lifecycle_status",
    ):
        op.drop_column("products", col)
