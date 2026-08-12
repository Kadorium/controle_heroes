"""FIN-23: inspect sample order 32 graph before cleanup. Never touches order 31."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("order32", c.execute(text("select id, code, status from orders where id=32")).fetchall())
    print("order31", c.execute(text("select id, code, status from orders where id=31")).fetchall())
    inv = c.execute(text("select id, invoice_number, status from invoices where order_id=32")).fetchall()
    print("invoices", inv)
    pays = c.execute(text("select id, amount, status, invoice_id from payables where order_id=32")).fetchall()
    print("payables", pays)
    pmts = c.execute(text("select id, amount, order_id from payments where order_id=32")).fetchall()
    print("payments", pmts)
    print(
        "payables_order31",
        c.execute(text("select count(1) from payables where order_id=31")).scalar(),
    )
    print(
        "payments_order31",
        c.execute(text("select count(1) from payments where order_id=31")).scalar(),
    )
    print(
        "invoices_order31",
        c.execute(text("select count(1) from invoices where order_id=31")).scalar(),
    )
