"""Prove Order 31 clean after G6 dryrun."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    pays = c.execute(
        text("select id, status, amount from payments where order_id = 31")
    ).fetchall()
    order = c.execute(
        text(
            "select id, code, status, "
            "(select count(1) from order_items where order_id = 31) as items "
            "from orders where id = 31"
        )
    ).mappings().first()
    docs = c.execute(
        text(
            "select d.id, d.original_filename "
            "from documents d "
            "join document_links l on l.document_id = d.id "
            "where l.entity_type = 'order' and l.entity_id = '31' "
            "order by d.id"
        )
    ).mappings().all()
    print("payments", [dict(r._mapping) for r in pays] if pays and hasattr(pays[0], "_mapping") else pays)
    print("order", dict(order) if order else None)
    print("docs", [dict(r) for r in docs])
