"""Testes reset operacional seguro."""

import pytest

from app.models import ImportationOrder, Supplier, User
from app.services.reset_operational_data import RESET_ENV_VAR, reset_operational_test_data


@pytest.fixture
def reset_env(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv(RESET_ENV_VAR, "1")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_reset_blocked_without_confirmation(db, monkeypatch):
    monkeypatch.delenv(RESET_ENV_VAR, raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(RuntimeError, match=RESET_ENV_VAR):
        reset_operational_test_data(db, skip_backup=True)


def test_reset_preserves_users_and_heroes(db, reset_env, admin_client):
    admin_client.post("/api/demo/seed")
    heroes_before = db.query(Supplier).filter(Supplier.name.ilike("%heroes%")).count()
    users_before = db.query(User).count()
    imps_before = db.query(ImportationOrder).count()
    assert imps_before > 0

    result = reset_operational_test_data(db, skip_backup=True)
    assert result["users_preserved"] is True
    assert result["heroes_supplier_preserved"] is True
    assert result["importations_remaining"] is False
    assert db.query(User).count() == users_before
    assert db.query(Supplier).filter(Supplier.name.ilike("%heroes%")).count() >= heroes_before


def test_dashboard_after_reset(db, reset_env, admin_client):
    admin_client.post("/api/demo/seed")
    reset_operational_test_data(db, skip_backup=True)
    r = admin_client.get("/api/dashboard/importations")
    assert r.status_code == 200


def test_reset_api_requires_env(admin_client, monkeypatch):
    monkeypatch.delenv(RESET_ENV_VAR, raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    r = admin_client.post("/api/imports/reset-operational")
    assert r.status_code == 403
