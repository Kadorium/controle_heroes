from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.begin() as c:
    n = c.execute(text("DELETE FROM order_items WHERE external_code = 'TEST-DOWN'")).rowcount
    rev = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print("deleted", n, "rev", rev)
