"""P0: diagnose epic_v2_test schema."""
from sqlalchemy import create_engine, text

URL = "postgresql://postgres@localhost:5433/epic_v2_test"
e = create_engine(URL)
with e.connect() as c:
    print("alembic", c.execute(text("select version_num from alembic_version")).scalar())
    print("current_db", c.execute(text("select current_database()")).scalar())
    n = c.execute(
        text("select count(*) from information_schema.tables where table_schema='public'")
    ).scalar()
    print("public_tables", n)
    rows = c.execute(
        text(
            "select table_name from information_schema.tables "
            "where table_schema='public' order by table_name"
        )
    ).fetchall()
    print("tables:", [r[0] for r in rows])
    try:
        print("orders_count", c.execute(text("select count(*) from orders")).scalar())
    except Exception as ex:
        print("orders_err", type(ex).__name__, str(ex)[:400])
