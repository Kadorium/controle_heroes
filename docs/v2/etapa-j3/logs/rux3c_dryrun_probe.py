from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("doc20", c.execute(text("select id, review_status from ingestion_documents where id=20")).fetchall())
    print(
        "orders",
        c.execute(
            text(
                "select id, code, status, external_ref from orders where code like '%589%' order by id"
            )
        ).fetchall(),
    )
    print(
        "items",
        c.execute(
            text(
                "select line_kind, quantity, unit from order_items where order_id=(select id from orders where code='589' limit 1) order by id"
            )
        ).fetchall(),
    )
