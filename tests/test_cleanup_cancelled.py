"""Testes resumo e purge de dados anulados."""

import uuid

import pytest

from app.models import ImportationOrder
from app.services.cleanup_cancelled import purge_cancelled_data
from app.services.reset_operational_data import RESET_ENV_VAR


@pytest.fixture
def reset_env(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv(RESET_ENV_VAR, "1")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_cancelled_summary_lists_inactive_importations(db, admin_client):
    uid = uuid.uuid4().hex[:8]
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"Sup {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    created = admin_client.post(
        "/api/importations",
        json={"po_number": f"PO-CLN-{uid}", "supplier_id": sup["id"], "currency": "EUR"},
    ).json()
    admin_client.post(f"/api/importations/{created['id']}/cancel", json={"reason": "teste limpeza"})

    res = admin_client.get("/api/imports/cancelled-summary")
    assert res.status_code == 200
    body = res.json()
    assert body["counts"]["importations_cancelled"] >= 1
    assert any(i["id"] == created["id"] for i in body["importations"])


def test_purge_cancelled_importation(db, admin_client, reset_env):
    uid = uuid.uuid4().hex[:8]
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"SupP {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    created = admin_client.post(
        "/api/importations",
        json={"po_number": f"PO-PURGE-{uid}", "supplier_id": sup["id"], "currency": "EUR"},
    ).json()
    imp_id = created["id"]
    admin_client.post(f"/api/importations/{imp_id}/cancel", json={"reason": "purge test"})

    res = admin_client.post(
        "/api/imports/purge-cancelled",
        json={"importation_ids": [imp_id]},
    )
    assert res.status_code == 200, res.text
    assert res.json()["importations_removed"] == 1
    assert db.query(ImportationOrder).filter(ImportationOrder.id == imp_id).first() is None


def test_purge_blocked_without_env(db, admin_client, monkeypatch):
    monkeypatch.delenv(RESET_ENV_VAR, raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    res = admin_client.post(
        "/api/imports/purge-cancelled",
        json={"purge_orphan_artifacts": True},
    )
    assert res.status_code == 403


def test_cancelled_summary_lists_products(db, admin_client):
    uid = uuid.uuid4().hex[:8]
    created = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-CLN-{uid}", "description": "Produto teste", "category": "OTHER"},
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    cancel = admin_client.post(f"/api/products/{pid}/cancel", json={"reason": "teste limpeza"})
    assert cancel.status_code == 200

    res = admin_client.get("/api/imports/cancelled-summary")
    assert res.status_code == 200
    body = res.json()
    assert any(p["id"] == pid for p in body["products"])


def test_purge_orphan_staging(db, reset_env):
    from app.models import StagingImportRow

    result = purge_cancelled_data(db, purge_orphan_artifacts=True)
    assert "staging_rows_removed" in result
    assert db.query(StagingImportRow).count() == 0
