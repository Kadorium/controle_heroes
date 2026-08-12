from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print(
        "orders",
        c.execute(
            text(
                "select id, code, status, external_ref from orders "
                "where code like '%589%' or external_ref like '%589%' order by id"
            )
        ).fetchall(),
    )
    print(
        "docs",
        c.execute(
            text(
                "select id, review_status, created_order_id from ingestion_documents "
                "where id in (20,21,22) order by id"
            )
        ).fetchall(),
    )
    print(
        "items28",
        c.execute(
            text(
                "select line_kind, quantity from order_items "
                "where order_id=(select id from orders where code='589-DRYRUN' limit 1) "
                "order by id"
            )
        ).fetchall(),
    )
