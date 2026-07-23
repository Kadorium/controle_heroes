"""Integração Catalog + Orders (Inc-1)."""

from decimal import Decimal


def _create_supplier(client, name="Heroes SPA", code=None):
    payload = {"name": name, "country_code": "IT"}
    if code is not None:
        payload["code"] = code
    r = client.post("/api/suppliers", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_product(client, sku="SKU-1", description="Raquete"):
    r = client.post("/api/products", json={"sku": sku, "description": description})
    assert r.status_code == 201, r.text
    return r.json()


def test_order_flow_draft_confirm_cancel(admin_client):
    c = admin_client
    sup = _create_supplier(c)
    prod = _create_product(c)

    r = c.post(
        "/api/orders",
        json={"code": "FLOW-758", "supplier_id": sup["id"], "currency": "EUR"},
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "DRAFT"
    assert order["code"] == "FLOW-758"
    assert order["commercial_total"] is None
    assert order["version"] == 1

    r = c.post(
        f"/api/orders/{order['id']}/items",
        json={
            "expected_version": order["version"],
            "product_id": prod["id"],
            "quantity": "2",
            "unit_price": "10.50",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["version"] == 2
    assert order["commercial_total"] == "21.0000"
    assert len(order["items"]) == 1
    item_id = order["items"][0]["id"]

    # unpriced second item → commercial_total null
    prod2 = _create_product(c, sku="SKU-2", description="Capa")
    r = c.post(
        f"/api/orders/{order['id']}/items",
        json={
            "expected_version": order["version"],
            "product_id": prod2["id"],
            "quantity": "1",
            "unit_price": None,
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["unpriced_item_count"] == 1
    assert order["commercial_total"] is None
    assert order["priced_subtotal"] == "21.0000"

    r = c.delete(
        f"/api/orders/{order['id']}/items/{order['items'][1]['id']}",
        params={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["commercial_total"] == "21.0000"

    r = c.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["status"] == "CONFIRMED"

    # edit forbidden
    r = c.post(
        f"/api/orders/{order['id']}/items",
        json={"expected_version": order["version"], "product_id": prod["id"], "quantity": "1"},
    )
    assert r.status_code == 409

    r = c.post(
        f"/api/orders/{order['id']}/cancel",
        json={"expected_version": order["version"], "reason_code": "ORDER_CANCEL_TEST"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CANCELLED"

    # audit trail
    audit = c.get("/api/audit", params={"entity_type": "order", "entity_id": str(order["id"])})
    assert audit.status_code == 200
    actions = {e["action"] for e in audit.json()}
    assert "create" in actions
    assert "confirm" in actions
    assert "cancel" in actions


def test_version_conflict(admin_client):
    c = admin_client
    sup = _create_supplier(c, name="S2")
    # unique code
    r = c.post("/api/orders", json={"code": "CONFLICT-1", "supplier_id": sup["id"]})
    order = r.json()
    r = c.patch(
        f"/api/orders/{order['id']}",
        json={"expected_version": 99, "notes": "x"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "conflict"


def test_sku_duplicate(admin_client):
    c = admin_client
    _create_product(c, sku="DUP-1")
    r = c.post("/api/products", json={"sku": "DUP-1", "description": "outro"})
    assert r.status_code == 409
