from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("docs", c.execute(text("select count(*) from ingestion_documents")).scalar())
    print(
        "orders589",
        c.execute(
            text(
                "select count(*) from orders where code like '%589%' or external_ref like '%589%'"
            )
        ).scalar(),
    )
    print(
        "heroes",
        c.execute(
            text("select count(*) from suppliers where name ilike '%hero%'")
        ).scalar(),
    )
    print("batches", c.execute(text("select count(*) from ingestion_batches")).scalar())
