"""P0: alembic + sanity on epic_v2_test. Read-only."""
from sqlalchemy import create_engine, text

URL = "postgresql://postgres@localhost:5433/epic_v2_test"
e = create_engine(URL)
with e.connect() as c:
    print("alembic", c.execute(text("select version_num from alembic_version")).scalar())
    for table in ("orders", "invoices", "payments", "shipments", "users"):
        try:
            n = c.execute(text(f"select count(*) from {table}")).scalar()
            print(table, n)
        except Exception as ex:
            print(table, "ERR", type(ex).__name__)
