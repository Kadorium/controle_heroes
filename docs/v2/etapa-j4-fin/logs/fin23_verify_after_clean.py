from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("o31", c.execute(text("select id, code, status from orders where id=31")).fetchone())
    print(
        "docs31",
        c.execute(
            text(
                "select d.id, d.original_filename from documents d "
                "join document_links l on l.document_id=d.id "
                "where l.entity_type='order' and l.entity_id='31'"
            )
        ).fetchall(),
    )
    print("items31", c.execute(text("select count(1) from order_items where order_id=31")).scalar())
    print("o32", c.execute(text("select id from orders where id=32")).fetchone())
    print(
        "inv244",
        c.execute(text("select id from invoices where invoice_number='244'")).fetchall(),
    )
    print(
        "batch2728",
        c.execute(text("select id from ingestion_batches where id in (27,28)")).fetchall(),
    )
    print(
        "fattura_docs",
        c.execute(
            text("select id, original_filename from documents where original_filename like '%Fattura_244%'")
        ).fetchall(),
    )
    print(
        "sku",
        c.execute(text("select id, sku from products where sku='8057628953586'")).fetchall(),
    )
    print(
        "heroes",
        c.execute(text("select id, name from suppliers where name = $$Heroe's Srl$$")).fetchall(),
    )
