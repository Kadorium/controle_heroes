import os
import tempfile

os.environ.setdefault("TEST_DATABASE_URL", "postgresql://postgres@localhost:5433/epic_v2_test")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["APP_ENV"] = "test"
_tmp = tempfile.mkdtemp(prefix="epic_v2_att_")
os.environ["ATTACHMENTS_PATH"] = _tmp

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.foundation.create_app import create_app
from app.foundation.database import Base, get_db
from app.foundation.settings import get_settings
from app.identity.seed import ensure_seed
import app.identity.models  # noqa: F401
import app.audit.models  # noqa: F401
import app.documents.models  # noqa: F401
import app.catalog.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.billing.models  # noqa: F401
import app.treasury.models  # noqa: F401
import app.treasury.fx_models  # noqa: F401
import app.logistics.models  # noqa: F401
import app.customs.models  # noqa: F401
import app.inventory.models  # noqa: F401

get_settings.cache_clear()
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    db = SessionLocal()
    try:
        settings = get_settings()
        ensure_seed(
            db,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            name=settings.seed_admin_name,
        )
        from app.inventory.repository import ensure_default_locations

        ensure_default_locations(db)
        db.commit()
    finally:
        db.close()
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app = create_app()

    def _get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(client):
    r = client.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    assert r.status_code == 200, r.text
    return client
