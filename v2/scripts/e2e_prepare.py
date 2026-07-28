"""Prepara epic_v2_test para Playwright — reset + alembic + seed.

Uso (cwd=v2):
  .venv\\Scripts\\python.exe scripts/e2e_prepare.py

Proteções:
  - recusa qualquer URL cujo database != epic_v2_test
  - nunca toca epic_v2
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


REQUIRED_DB = "epic_v2_test"
FORBIDDEN_DB = "epic_v2"


def _database_name(url: str) -> str:
    parsed = urlparse(url)
    name = (parsed.path or "").lstrip("/")
    if not name:
        raise SystemExit(f"DATABASE_URL sem nome de banco: {url!r}")
    return name.split("?")[0]


def assert_test_database(url: str) -> str:
    name = _database_name(url)
    if name == FORBIDDEN_DB:
        raise SystemExit(
            f"REFUSADO: URL aponta para {FORBIDDEN_DB} (ops). Use apenas {REQUIRED_DB}."
        )
    if name != REQUIRED_DB:
        raise SystemExit(
            f"REFUSADO: database={name!r}. Exigido exatamente {REQUIRED_DB!r}."
        )
    return name


def main() -> int:
    # Preferência: E2E_DATABASE_URL > TEST_DATABASE_URL > DATABASE_URL
    url = (
        os.environ.get("E2E_DATABASE_URL")
        or os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "postgresql://postgres@localhost:5433/epic_v2_test"
    )
    db_name = assert_test_database(url)
    os.environ["DATABASE_URL"] = url
    os.environ["APP_ENV"] = "test"

    started = datetime.now(timezone.utc).isoformat()
    print(f"[e2e_prepare] start={started}")
    print(f"[e2e_prepare] database={db_name}")
    print(f"[e2e_prepare] url_host={urlparse(url).hostname}:{urlparse(url).port}")

    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    engine.dispose()
    print("[e2e_prepare] schema public reset")

    # Alembic upgrade head (usa DATABASE_URL do env)
    from alembic import command
    from alembic.config import Config

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "alembic"))
    command.upgrade(cfg, "head")
    print("[e2e_prepare] alembic upgrade head OK")

    # Import app após env
    sys.path.insert(0, root)
    from app.foundation.database import SessionLocal
    from app.foundation.settings import get_settings
    from app.identity.seed import ensure_seed

    get_settings.cache_clear()
    settings = get_settings()
    db = SessionLocal()
    try:
        ensure_seed(
            db,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            name=settings.seed_admin_name,
        )
        db.commit()
        print(f"[e2e_prepare] seed ok email={settings.seed_admin_email}")
    finally:
        db.close()

    print("[e2e_prepare] DONE — epic_v2 NÃO foi tocado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
