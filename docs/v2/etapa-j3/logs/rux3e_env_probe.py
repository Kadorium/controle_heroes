from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("dbname", c.execute(text("select current_database()")).scalar())
    print("docs", c.execute(text("select count(*) from ingestion_documents")).scalar())
    print(
        "orders589",
        c.execute(
            text(
                "select id, code, external_ref from orders "
                "where code like '%589%' or external_ref like '%589%' or code like 'ING-%'"
            )
        ).fetchall(),
    )
    print(
        "heroes",
        c.execute(
            text(
                "select id, name, code from suppliers "
                "where name ilike '%hero%' or code like '%02610500395%'"
            )
        ).fetchall(),
    )
    print("batches", c.execute(text("select count(*) from ingestion_batches")).scalar())
