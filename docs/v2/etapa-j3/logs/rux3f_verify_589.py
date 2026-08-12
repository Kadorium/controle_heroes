from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print(c.execute(text("select id, code, status from orders where id=31")).fetchall())
