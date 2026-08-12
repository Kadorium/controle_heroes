"""FIN-1C G1 — read-only inventory payments Order 31 (epic_v2)."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("alembic", c.execute(text("select version_num from alembic_version")).scalar())
    cols = c.execute(
        text(
            "select column_name from information_schema.columns "
            "where table_name='fx_executions' order by ordinal_position"
        )
    ).fetchall()
    print("fx_cols", [r[0] for r in cols])
    rows = c.execute(
        text(
            """
            select p.id, p.status, p.amount, p.currency, p.payment_date, p.order_id,
                   p.supplier_id, fx.id as fx_id, fx.rate, fx.brl_amount
            from payments p
            left join fx_executions fx on fx.payment_id = p.id
            where p.order_id = 31
            order by p.id
            """
        )
    ).fetchall()
    print("count", len(rows))
    for r in rows:
        print(dict(r._mapping))
    print(
        "reg",
        sum(1 for r in rows if r.status == "REGISTERED"),
        "can",
        sum(1 for r in rows if r.status == "CANCELLED"),
    )
    print("quotes", c.execute(text("select count(*) from fx_market_quotes")).scalar())
    o = c.execute(
        text("select id, code, status, supplier_id, currency from orders where id=31")
    ).fetchone()
    print("order", tuple(o) if o else None)
    other = c.execute(
        text(
            """
            select id, order_id, status, amount, currency from payments
            where supplier_id=:sid and currency=:cur
              and (order_id is distinct from 31)
            order by id
            """
        ),
        {"sid": o[3], "cur": o[4]},
    ).fetchall()
    print("other_same_sup_cur", len(other))
    for r in other:
        print(dict(r._mapping))
    payables = c.execute(
        text(
            """
            select p.id, p.status, p.amount, p.source_type, p.invoice_id
            from payables p
            left join invoices i on i.id = p.invoice_id
            where i.order_id = 31 or (p.source_type = 'ORDER_SCHEDULE' and p.source_id = 31)
            """
        )
    ).fetchall()
    print("payables_related", [dict(r._mapping) for r in payables])
