"""RUX-3B (1/2) — OrderItem commitment lines.

- order_items.product_id nullable (só para line_kind=COMMITMENT)
- line_kind EXPLÍCITO NOT NULL (PRODUCT | COMMITMENT); backfill PRODUCT em todas as linhas
- external_code nullable (código do documento para compromisso)

Revision ID: 021
Revises: 019
Create Date: 2026-08-06

NÃO reutiliza a 020 isolada (RUX-3A Catalog — fora da árvore).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "019"
branch_labels = None
depends_on = None

LINE_KIND_PRODUCT = "PRODUCT"
LINE_KIND_COMMITMENT = "COMMITMENT"


def upgrade() -> None:
    # --- aditivo e seguro: line_kind + external_code ---
    op.add_column(
        "order_items",
        sa.Column(
            "line_kind",
            sa.String(length=32),
            nullable=True,  # temporário até backfill
        ),
    )
    op.add_column(
        "order_items",
        sa.Column("external_code", sa.String(length=128), nullable=True),
    )

    # Backfill: TODAS as linhas existentes = PRODUCT (linha normal)
    op.execute(
        sa.text(
            f"UPDATE order_items SET line_kind = '{LINE_KIND_PRODUCT}' "
            f"WHERE line_kind IS NULL"
        )
    )

    op.alter_column(
        "order_items",
        "line_kind",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default=LINE_KIND_PRODUCT,
    )

    op.create_check_constraint(
        "ck_order_items_line_kind",
        "order_items",
        f"line_kind IN ('{LINE_KIND_PRODUCT}', '{LINE_KIND_COMMITMENT}')",
    )
    op.create_check_constraint(
        "ck_order_items_line_kind_product_id",
        "order_items",
        f"(line_kind = '{LINE_KIND_PRODUCT}' AND product_id IS NOT NULL) OR "
        f"(line_kind = '{LINE_KIND_COMMITMENT}' AND product_id IS NULL)",
    )

    # --- irreversível na prática se existir COMMITMENT: product_id nullable ---
    op.alter_column(
        "order_items",
        "product_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade honesto.

    - ``line_kind`` / ``external_code``: removíveis se não houver COMMITMENT.
    - ``product_id`` NOT NULL: só se ZERO linhas com product_id NULL.
      Se existir qualquer nulo, falha alto — não finge reversibilidade.
    """
    conn = op.get_bind()

    null_products = conn.execute(
        sa.text("SELECT count(1) FROM order_items WHERE product_id IS NULL")
    ).scalar()
    if null_products and int(null_products) > 0:
        raise RuntimeError(
            f"downgrade 021 recusado: {null_products} order_item(s) com product_id NULL. "
            "Tornar product_id NOT NULL de novo apagaria ou forçaria dados — "
            "remova/resolva as linhas COMMITMENT antes de downgrade."
        )

    commitment_rows = conn.execute(
        sa.text(
            f"SELECT count(1) FROM order_items WHERE line_kind = '{LINE_KIND_COMMITMENT}'"
        )
    ).scalar()
    if commitment_rows and int(commitment_rows) > 0:
        raise RuntimeError(
            f"downgrade 021 recusado: {commitment_rows} order_item(s) line_kind=COMMITMENT. "
            "Converta ou remova antes de dropar line_kind."
        )

    op.drop_constraint("ck_order_items_line_kind_product_id", "order_items", type_="check")
    op.drop_constraint("ck_order_items_line_kind", "order_items", type_="check")

    op.alter_column(
        "order_items",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column("order_items", "external_code")
    op.drop_column("order_items", "line_kind")
