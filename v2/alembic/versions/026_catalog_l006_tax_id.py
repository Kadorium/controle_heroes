"""MDM-4 — Product L-006 + Supplier.tax_id.

Não é RUX-3A / 020. Sem refs, sequence ou EPIC-*.
Backfill: NONE (colunas nullable).

Revision ID: 026
Revises: 025
Create Date: 2026-08-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("ean", sa.String(length=18), nullable=True))
    op.add_column("products", sa.Column("size", sa.String(length=64), nullable=True))
    op.add_column("products", sa.Column("color", sa.String(length=64), nullable=True))
    op.add_column("products", sa.Column("ncm", sa.String(length=8), nullable=True))
    op.add_column("products", sa.Column("country_of_origin", sa.String(length=2), nullable=True))
    op.add_column("products", sa.Column("unit", sa.String(length=16), nullable=True))
    op.add_column("products", sa.Column("net_weight_kg", sa.Numeric(18, 4), nullable=True))
    op.create_check_constraint(
        "ck_products_net_weight_positive",
        "products",
        "net_weight_kg IS NULL OR net_weight_kg > 0",
    )
    op.create_index(
        "uq_products_ean_not_null",
        "products",
        ["ean"],
        unique=True,
        postgresql_where=sa.text("ean IS NOT NULL"),
    )

    op.add_column("suppliers", sa.Column("tax_id", sa.String(length=32), nullable=True))
    op.create_index(
        "uq_suppliers_country_tax_id",
        "suppliers",
        ["country_code", "tax_id"],
        unique=True,
        postgresql_where=sa.text("tax_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_suppliers_country_tax_id", table_name="suppliers")
    op.drop_column("suppliers", "tax_id")
    op.drop_index("uq_products_ean_not_null", table_name="products")
    op.drop_constraint("ck_products_net_weight_positive", "products", type_="check")
    op.drop_column("products", "net_weight_kg")
    op.drop_column("products", "unit")
    op.drop_column("products", "country_of_origin")
    op.drop_column("products", "ncm")
    op.drop_column("products", "color")
    op.drop_column("products", "size")
    op.drop_column("products", "ean")
