"""FIN-1C-FIX-1 F5 — limpar Payments + Fx do Order 31 (epic_v2). Preserva Order/lines/docs."""
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
    if not pays:
        print("nothing_to_clean")
    else:
        fx_ids = [
            r[0]
            for r in c.execute(
                text("select id from fx_executions where payment_id = any(:ids)"),
                {"ids": pays},
            ).fetchall()
        ]
        print("fx_ids", fx_ids)
        # allocations
        c.execute(
            text("delete from payment_allocations where payment_id = any(:ids)"),
            {"ids": pays},
        )
        # document links on fx + payment
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

    left_p = c.execute(
        text("select count(1) from payments where order_id = 31")
    ).scalar()
    left_reg = c.execute(
        text(
            "select count(1) from payments where order_id = 31 and status = 'REGISTERED'"
        )
    ).scalar()
    order = c.execute(
        text(
            "select id, code, status, "
            "(select count(1) from order_items where order_id = 31) as items, "
            "(select count(1) from document_links where entity_type = 'order' "
            " and entity_id = '31') as docs "
            "from orders where id = 31"
        )
    ).fetchone()
    print("payments_left", left_p, "registered", left_reg)
    print("order", dict(order._mapping) if order else None)
