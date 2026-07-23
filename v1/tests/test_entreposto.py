"""Entreposto — movimentos RECEIPT/CONSUMPTION e quantity_chain."""

import uuid

import pytest


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


@pytest.fixture()
def supplier(admin_client):
    r = admin_client.post(
        "/api/suppliers",
        json={"name": f"Heroes {_uid()}", "country": "CN", "currency_default": "EUR"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def product(admin_client):
    r = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-{_uid()}", "description": "Produto entreposto"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation(admin_client, supplier, product):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [{"product_id": product["id"], "quantity_ordered": 100, "unit_price_foreign": "10"}],
        },
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation_item(admin_client, importation):
    items = admin_client.get(f"/api/importations/{importation['id']}/items")
    return items.json()[0]


@pytest.fixture()
def shipped_item(admin_client, importation, importation_item):
    ship = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-EP-{_uid()}",
            "modal": "OCEAN",
        },
    ).json()
    admin_client.post(
        f"/api/shipments/{ship['id']}/items",
        json={"importation_item_id": importation_item["id"], "quantity_shipped": 80},
    )
    return importation_item


def test_entreposto_receipt_and_consumption(admin_client, importation, shipped_item):
    item_id = shipped_item["id"]
    imp_id = importation["id"]

    r = admin_client.post(
        "/api/stock/entreposto-movements",
        json={
            "importation_id": imp_id,
            "importation_item_id": item_id,
            "movement_type": "RECEIPT",
            "quantity": 50,
        },
    )
    assert r.status_code == 201

    r2 = admin_client.post(
        "/api/stock/entreposto-movements",
        json={
            "importation_id": imp_id,
            "importation_item_id": item_id,
            "movement_type": "CONSUMPTION",
            "quantity": 10,
        },
    )
    assert r2.status_code == 201

    chain = admin_client.get(f"/api/stock/importations/{imp_id}/quantity-chain").json()
    row = next(c for c in chain if c["importation_item_id"] == item_id)
    assert row["quantity_entreposto_balance"] == 40
    assert row["quantity_entreposto_consumed"] == 10

    movements = admin_client.get(f"/api/stock/importations/{imp_id}/entreposto-movements").json()
    assert len(movements) == 2


def test_entreposto_receipt_exceeds_available_blocked(admin_client, importation, shipped_item):
    item_id = shipped_item["id"]
    imp_id = importation["id"]
    r = admin_client.post(
        "/api/stock/entreposto-movements",
        json={
            "importation_id": imp_id,
            "importation_item_id": item_id,
            "movement_type": "RECEIPT",
            "quantity": 90,
        },
    )
    assert r.status_code == 400


def test_entreposto_consumption_exceeds_balance_blocked(admin_client, importation, shipped_item):
    item_id = shipped_item["id"]
    imp_id = importation["id"]
    admin_client.post(
        "/api/stock/entreposto-movements",
        json={
            "importation_id": imp_id,
            "importation_item_id": item_id,
            "movement_type": "RECEIPT",
            "quantity": 20,
        },
    )
    r = admin_client.post(
        "/api/stock/entreposto-movements",
        json={
            "importation_id": imp_id,
            "importation_item_id": item_id,
            "movement_type": "CONSUMPTION",
            "quantity": 25,
        },
    )
    assert r.status_code == 400
