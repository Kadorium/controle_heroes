"""FIN-1-G6-DRYRUN cleanup — payments order 31 + accidental dryrun order doc."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.begin() as c:
    pays = [
        r[0]
        for r in c.execute(
            text("select id from payments where order_id = 31 order by id")
        ).fetchall()
    ]
    print("payment_ids", pays)
    if pays:
        fx_ids = [
            r[0]
            for r in c.execute(
                text("select id from fx_executions where payment_id = any(:ids)"),
                {"ids": pays},
            ).fetchall()
        ]
        print("fx_ids", fx_ids)
        c.execute(
            text("delete from payment_allocations where payment_id = any(:ids)"),
            {"ids": pays},
        )
        if fx_ids:
            c.execute(
                text(
                    "delete from document_links where entity_type = 'fx_execution' "
                    "and entity_id = any(:ids)"
                ),
                {"ids": [str(i) for i in fx_ids]},
            )
            c.execute(
                text("delete from fx_executions where id = any(:ids)"),
                {"ids": fx_ids},
            )
        c.execute(
            text(
                "delete from document_links where entity_type = 'payment' "
                "and entity_id = any(:ids)"
            ),
            {"ids": [str(i) for i in pays]},
        )
        c.execute(text("delete from payments where id = any(:ids)"), {"ids": pays})

    # accidental order doc from dryrun file-picker miss
    docs = c.execute(
        text(
            """
            select d.id, d.original_filename
            from documents d
            join document_links l on l.document_id = d.id
            where l.entity_type = 'order' and l.entity_id = '31'
            order by d.id
            """
        )
    ).fetchall()
    print("order_docs_before", [dict(r._mapping) for r in docs])
    for d in docs:
        if str(d.original_filename).startswith("dryrun"):
            c.execute(
                text(
                    "delete from document_links where document_id = :id "
                    "and entity_type = 'order' and entity_id = '31'"
                ),
                {"id": d.id},
            )
            # leave blob if shared; only unlink from order
            print("unlinked_order_doc", d.id, d.original_filename)

    left_p = c.execute(
        text("select count(1) from payments where order_id = 31")
    ).scalar()
    docs_after = c.execute(
        text(
            """
            select d.id, d.original_filename
            from documents d
            join document_links l on l.document_id = d.id
            where l.entity_type = 'order' and l.entity_id = '31'
            order by d.id
            """
        )
    ).fetchall()
    order = c.execute(
        text(
            "select id, code, status, "
            "(select count(1) from order_items where order_id = 31) as items "
            "from orders where id = 31"
        )
    ).fetchone()
    print("payments_left", left_p)
    print("order_docs_after", [dict(r._mapping) for r in docs_after])
    print("order", dict(order._mapping) if order else None)
