from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("allocs", c.execute(text("select payment_id, amount from payment_allocations limit 20")).fetchall())
    print(
        "pays",
        c.execute(
            text(
                "select id, status, amount, order_id from payments "
                "where status = 'REGISTERED' order by id desc limit 15"
            )
        ).fetchall(),
    )
    print(
        "payables",
        c.execute(
            text(
                "select id, status, amount, balance, currency from payables "
                "where status != 'CANCELLED' order by id desc limit 10"
            )
        ).fetchall(),
    )
