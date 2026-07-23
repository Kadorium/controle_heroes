"""PATCH item — qty/preço em ordem manual vs bloqueio Heroes."""

from __future__ import annotations

import uuid

import pytest

from app.models import ImportationItem
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx
from tests.test_heroes_postmvp_53 import _commit_758


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _create_manual_order(client):
    uid = _uid()
    sup = client.post(
        "/api/suppliers",
        json={"name": f"ItemUpd Sup {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    imp = client.post(
        "/api/importations",
        json={
            "po_number": f"PO-ITEM-{uid}",
            "supplier_id": sup["id"],
            "currency": "EUR",
        },
    )
    assert imp.status_code == 201
    imp_id = imp.json()["id"]
    item = client.post(
        f"/api/importations/{imp_id}/items",
        json={
            "description": "Modelo manual",
            "quantity_ordered": 10,
            "unit_price_foreign": "12.50",
        },
    )
    assert item.status_code == 201
    return imp_id, item.json()["id"]


def test_patch_qty_manual_order_ok(admin_client):
    imp_id, item_id = _create_manual_order(admin_client)
    res = admin_client.patch(
        f"/api/importations/{imp_id}/items/{item_id}",
        json={"quantity_ordered": 25},
    )
    assert res.status_code == 200, res.text
    assert res.json()["quantity_ordered"] == 25


def test_patch_qty_heroes_order_blocked(db, admin_client):
    imp = _commit_758(db, build_ordine_758_xlsx())
    item = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == imp.id, ImportationItem.is_active.is_(True))
        .first()
    )
    assert item is not None
    res = admin_client.patch(
        f"/api/importations/{imp.id}/items/{item.id}",
        json={"quantity_ordered": 999},
    )
    assert res.status_code == 400
    assert "heroes" in res.json()["detail"].lower() or "itália" in res.json()["detail"].lower()
