from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.begin() as c:
    links = c.execute(
        text("select entity_type, entity_id from document_links where document_id=44")
    ).fetchall()
    print("links44", links)
    c.execute(
        text(
            "delete from document_links where document_id=44 "
            "and entity_type='ingestion_document' and entity_id='29'"
        )
    )
    left = c.execute(
        text("select count(1) from document_links where document_id=44")
    ).scalar()
    print("links44_after", left)
    if left == 0:
        c.execute(text("delete from documents where id=44"))
        print("deleted document 44")
    occs = c.execute(
        text("select count(1) from ingestion_occurrences where batch_id=27")
    ).scalar()
    print("batch27_occs", occs)
    if occs == 0:
        c.execute(text("delete from ingestion_batches where id=27"))
        print("deleted batch 27")
    o31 = c.execute(text("select id, code, status from orders where id=31")).fetchone()
    print("o31", o31)
