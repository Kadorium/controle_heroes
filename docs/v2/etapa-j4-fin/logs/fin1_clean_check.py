"""FIN-1-CLEAN — verify payments 10/11 cancelled; FX leftovers; order 31 intact."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    pays = c.execute(
        text(
            "select id, status, order_id, amount, cancel_reason_code "
            "from payments where id in (10,11) order by id"
        )
    ).fetchall()
    print("payments", pays)
    fxs = c.execute(
        text(
            "select id, payment_id, foreign_amount, brl_amount, rate "
            "from fx_executions where payment_id in (10,11) order by id"
        )
    ).fetchall()
    print("fx_executions", fxs)
    links = c.execute(
        text(
            "select count(1) from fx_execution_allocations fea "
            "join fx_executions fe on fe.id = fea.fx_execution_id "
            "where fe.payment_id in (10,11)"
        )
    ).scalar()
    print("fx_alloc_links", links)
    order = c.execute(
        text(
            "select id, code, status, "
            "(select count(1) from order_items oi where oi.order_id=31) as items "
            "from orders where id=31"
        )
    ).fetchone()
    print("order31", order)
    reg = c.execute(
        text(
            "select count(1) from payments "
            "where order_id=31 and status='REGISTERED'"
        )
    ).scalar()
    print("registered_advances_on_31", reg)
