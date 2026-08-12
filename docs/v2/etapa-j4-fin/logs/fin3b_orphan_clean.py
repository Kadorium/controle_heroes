from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.begin() as c:
    links = c.execute(
        text("select entity_type, entity_id from document_links where document_id=45")
    ).fetchall()
    print("links45", [tuple(r) for r in links])
    c.execute(
        text(
            "delete from document_links where document_id=45 "
            "and entity_type='ingestion_document' and entity_id='30'"
        )
    )
    left = c.execute(
        text("select count(1) from document_links where document_id=45")
    ).scalar()
    print("links45_after", left)
    if left == 0:
        c.execute(text("delete from documents where id=45"))
        print("deleted document 45")
    o31 = c.execute(text("select id, code, status from orders where id=31")).fetchone()
    o33 = c.execute(text("select id from orders where id=33")).fetchone()
    inv24 = c.execute(text("select id from invoices where id=24")).fetchone()
    print("o31", tuple(o31) if o31 else None, "o33", o33, "inv24", inv24)
    assert o31[1] == "589" and o33 is None and inv24 is None
