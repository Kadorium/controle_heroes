"""FIN-1-CLEAN — delete orphan demo FxExecutions for cancelled payments 10/11."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.begin() as c:
    fx_ids = [
        r[0]
        for r in c.execute(
            text("select id from fx_executions where payment_id in (10,11)")
        ).fetchall()
    ]
    print("fx_ids", fx_ids)
    if fx_ids:
        # detach document links if any
        c.execute(
            text(
                "delete from document_links where entity_type='fx_execution' "
                "and entity_id = any(:ids)"
            ),
            {"ids": [str(i) for i in fx_ids]},
        )
        c.execute(
            text("delete from fx_executions where id = any(:ids)"),
            {"ids": fx_ids},
        )
    left = c.execute(
        text("select count(1) from fx_executions where payment_id in (10,11)")
    ).scalar()
    print("fx_left", left)
    print(
        "registered_on_31",
        c.execute(
            text(
                "select count(1) from payments where order_id=31 and status='REGISTERED'"
            )
        ).scalar(),
    )
