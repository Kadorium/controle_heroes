"""Rebuild epic_v2_test schema to Alembic head. Never touches epic_v2."""
from __future__ import annotations

from sqlalchemy import create_engine, text

URL = "postgresql://postgres@localhost:5433/epic_v2_test"

engine = create_engine(URL)
with engine.begin() as conn:
    db = conn.execute(text("select current_database()")).scalar()
    if db != "epic_v2_test":
        raise SystemExit(f"REFUSED: current_database={db!r} (expected epic_v2_test)")
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
print("public schema recreated on epic_v2_test")
