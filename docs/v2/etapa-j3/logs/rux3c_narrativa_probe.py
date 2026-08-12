from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print(
        "docs",
        c.execute(
            text(
                "select id, review_status from ingestion_documents order by id"
            )
        ).fetchall(),
    )
    print(
        "orders",
        c.execute(
            text(
                "select id, code, status, external_ref from orders "
                "where code like '%589%' order by id"
            )
        ).fetchall(),
    )
