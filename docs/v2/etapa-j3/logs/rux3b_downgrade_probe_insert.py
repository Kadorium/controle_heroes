"""Prova downgrade 021: com COMMITMENT presente, falha alto (não finge reversibilidade)."""
from __future__ import annotations

from sqlalchemy import create_engine, text

URL = "postgresql://postgres@localhost:5433/epic_v2"


def main() -> None:
    eng = create_engine(URL)
    with eng.begin() as conn:
        # insert synthetic commitment row
        order_id = conn.execute(
            text("SELECT id FROM orders ORDER BY id LIMIT 1")
        ).scalar()
        if order_id is None:
            print("SKIP: no orders")
            return
        conn.execute(
            text(
                """
                INSERT INTO order_items
                  (order_id, product_id, line_kind, external_code,
                   sku_snapshot, description_snapshot, quantity, position)
                VALUES
                  (:oid, NULL, 'COMMITMENT', 'TEST-DOWN',
                   'TEST-DOWN', 'downgrade probe', 1, 9999)
                """
            ),
            {"oid": order_id},
        )
        nulls = conn.execute(
            text("SELECT count(1) FROM order_items WHERE product_id IS NULL")
        ).scalar()
        print("null_product_rows", nulls)
    print("probe_row_inserted")


if __name__ == "__main__":
    main()
