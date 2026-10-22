"""CAT-PIM Onda 1 — taxonomy, commercial identity, attributes, provenance.

Revision ID: 027
Revises: 026
Create Date: 2026-08-19

Additive. Product consumers keep sku/description/is_active/L-006.
Does not create ProductFamily/Variant, media, or 020.
Not applied to epic_v2 until a separate promotion authorization.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("product_categories.id"), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_product_categories_slug", "product_categories", ["slug"], unique=True)

    op.create_table(
        "product_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommended_attributes", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_product_types_slug", "product_types", ["slug"], unique=True)

    op.create_table(
        "catalog_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_actor_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("products", sa.Column("commercial_name", sa.String(length=512), nullable=True))
    op.add_column("products", sa.Column("short_description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("long_description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("fiscal_description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("lifecycle_status", sa.String(length=16), nullable=True))
    op.add_column("products", sa.Column("supplier_sku", sa.String(length=64), nullable=True))
    op.add_column("products", sa.Column("category_id", sa.Integer(), sa.ForeignKey("product_categories.id"), nullable=True))
    op.add_column("products", sa.Column("product_type_id", sa.Integer(), sa.ForeignKey("product_types.id"), nullable=True))
    op.add_column("products", sa.Column("subcategory", sa.String(length=128), nullable=True))
    op.add_column("products", sa.Column("taxonomy_status", sa.String(length=16), nullable=True))
    op.add_column("products", sa.Column("taxonomy_reason", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("import_decision", sa.String(length=16), nullable=True))
    op.add_column(
        "products",
        sa.Column("short_generic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("products", sa.Column("attributes", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("products", sa.Column("provenance", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("products", sa.Column("source_kind", sa.String(length=32), nullable=True))
    op.add_column("products", sa.Column("import_batch_id", sa.Integer(), sa.ForeignKey("catalog_import_batches.id"), nullable=True))

    op.create_check_constraint(
        "ck_products_taxonomy_status",
        "products",
        "taxonomy_status IS NULL OR taxonomy_status IN ('CONFIDENT', 'REVIEW')",
    )
    op.create_check_constraint(
        "ck_products_lifecycle_status",
        "products",
        "lifecycle_status IS NULL OR lifecycle_status IN ('ACTIVE', 'DISCONTINUED', 'UNKNOWN')",
    )
    op.create_check_constraint(
        "ck_products_import_decision",
        "products",
        "import_decision IS NULL OR import_decision IN ('APROVAR', 'EDITAR', 'REVISAR', 'IGNORAR')",
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_product_type_id", "products", ["product_type_id"])
    op.create_index("ix_products_taxonomy_status", "products", ["taxonomy_status"])
    op.create_index("ix_products_source_kind", "products", ["source_kind"])
    op.create_index("ix_products_import_decision", "products", ["import_decision"])

    op.execute("UPDATE products SET commercial_name = description WHERE commercial_name IS NULL")
    op.execute(
        "UPDATE products SET lifecycle_status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'DISCONTINUED' END "
        "WHERE lifecycle_status IS NULL"
    )
    op.alter_column("products", "commercial_name", existing_type=sa.String(length=512), nullable=False)

    bind = op.get_bind()
    session = Session(bind=bind)
    from app.catalog.taxonomy import ensure_taxonomy

    ensure_taxonomy(session)
    session.commit()
    session.close()


def downgrade() -> None:
    op.drop_index("ix_products_import_decision", table_name="products")
    op.drop_index("ix_products_source_kind", table_name="products")
    op.drop_index("ix_products_taxonomy_status", table_name="products")
    op.drop_index("ix_products_product_type_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_constraint("ck_products_import_decision", "products", type_="check")
    op.drop_constraint("ck_products_lifecycle_status", "products", type_="check")
    op.drop_constraint("ck_products_taxonomy_status", "products", type_="check")
    op.drop_column("products", "import_batch_id")
    op.drop_column("products", "short_generic")
    op.drop_column("products", "import_decision")
    op.drop_column("products", "source_kind")
    op.drop_column("products", "provenance")
    op.drop_column("products", "attributes")
    op.drop_column("products", "taxonomy_reason")
    op.drop_column("products", "taxonomy_status")
    op.drop_column("products", "subcategory")
    op.drop_column("products", "product_type_id")
    op.drop_column("products", "category_id")
    op.drop_column("products", "supplier_sku")
    op.drop_column("products", "lifecycle_status")
    op.drop_column("products", "fiscal_description")
    op.drop_column("products", "long_description")
    op.drop_column("products", "short_description")
    op.drop_column("products", "commercial_name")
    op.drop_table("catalog_import_batches")
    op.drop_index("ix_product_types_slug", table_name="product_types")
    op.drop_table("product_types")
    op.drop_index("ix_product_categories_slug", table_name="product_categories")
    op.drop_table("product_categories")
