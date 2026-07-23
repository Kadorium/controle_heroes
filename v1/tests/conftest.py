import os
import tempfile

# Definir banco de testes antes de importar a aplicação
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql://postgres@localhost:5433/epic_importacao_test",
)
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["APP_ENV"] = "test"
_test_attachments = tempfile.mkdtemp(prefix="epic_attachments_test_")
_test_imports = tempfile.mkdtemp(prefix="epic_imports_test_")
os.environ["ATTACHMENTS_PATH"] = _test_attachments
os.environ["IMPORTS_PATH"] = _test_imports

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Role, User
from app.services.seed import run_initial_seed

get_settings.cache_clear()
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    db = TestingSession()
    try:
        run_initial_seed(db, "admin@epic.com.br", "admin123", "Administrador")
        role = db.query(Role).filter(Role.name == "operador").first()
        if not db.query(User).filter(User.email == "operador@epic.com.br").first():
            db.add(
                User(
                    email="operador@epic.com.br",
                    name="Operador Teste",
                    password_hash=hash_password("oper123"),
                    role_id=role.id,
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
