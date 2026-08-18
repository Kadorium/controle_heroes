"""Rebuild epic_v2_test to Alembic 025 + seed. Never touches epic_v2."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

URL = "postgresql://postgres@localhost:5433/epic_v2_test"
ROOT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle")
V2 = ROOT / "v2"


def main() -> None:
    engine = create_engine(URL)
    with engine.begin() as conn:
        db = conn.execute(text("select current_database()")).scalar()
        if db != "epic_v2_test":
            raise SystemExit(f"REFUSED: current_database={db!r}")
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    print("public schema recreated on epic_v2_test")

    env = os.environ.copy()
    env["DATABASE_URL"] = URL
    env["APP_ENV"] = "test"
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(V2),
        env=env,
        check=False,
    )
    if r.returncode != 0:
        raise SystemExit(f"alembic upgrade failed: {r.returncode}")

    os.environ["DATABASE_URL"] = URL
    os.environ["APP_ENV"] = "test"
    sys.path.insert(0, str(V2))
    from sqlalchemy.orm import sessionmaker

    from app.foundation.settings import get_settings
    from app.identity.seed import ensure_seed
    from app.inventory.repository import ensure_default_locations

    get_settings.cache_clear()
    settings = get_settings()
    seed_engine = create_engine(URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=seed_engine)
    db = SessionLocal()
    try:
        ensure_seed(
            db,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            name=settings.seed_admin_name,
        )
        ensure_default_locations(db)
        db.commit()
    finally:
        db.close()
    print("seed admin + DOMESTIC-MAIN ok")


if __name__ == "__main__":
    main()
