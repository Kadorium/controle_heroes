"""Elo 10 — CONFIRMED → CLOSED / reopen. Sem Billing/Treasury no comando."""

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION


def _create_supplier(client, name="Heroes Close SPA"):
    r = client.post("/api/suppliers", json={"name": name, "country_code": "IT"})
    assert r.status_code == 201, r.text
    return r.json()


def _create_product(client, sku="SKU-CLOSE-1", description="Raquete close"):
    r = client.post("/api/products", json={"sku": sku, "description": description})
    assert r.status_code == 201, r.text
    return r.json()


def _draft_with_item(client, *, code: str, line_kind="PRODUCT"):
    sup = _create_supplier(client, name=f"Sup {code}")
    r = client.post(
        "/api/orders",
        json={"code": code, "supplier_id": sup["id"], "currency": "EUR"},
    )
    assert r.status_code == 201, r.text
    order = r.json()
    if line_kind == "PRODUCT":
        prod = _create_product(client, sku=f"SKU-{code}")
        r = client.post(
            f"/api/orders/{order['id']}/items",
            json={
                "expected_version": order["version"],
                "product_id": prod["id"],
                "quantity": "2",
                "unit_price": "10.00",
            },
        )
    else:
        r = client.post(
            f"/api/orders/{order['id']}/items",
            json={
                "expected_version": order["version"],
                "line_kind": "COMMITMENT",
                "external_code": "I.V. CLOSE",
                "description": "compromisso sem produto",
                "quantity": "1",
                "unit_price": "10.00",
            },
        )
    assert r.status_code == 201, r.text
    order = r.json()
    r = client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_migration_031_revises_030():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("031")
    assert rev is not None
    assert rev.down_revision == "030"
    assert script.get_current_head() == "031"
    assert EXPECTED_ALEMBIC_REVISION == "031"


def test_close_reopen_audit(admin_client):
    c = admin_client
    order = _draft_with_item(c, code="CLOSE-OK-1")
    r = c.post(
        f"/api/orders/{order['id']}/close",
        json={"expected_version": order["version"], "reason_code": "STORY_COMPLETE"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "CLOSED"
    assert body["close_reason_code"] == "STORY_COMPLETE"
    assert body["closed_at"] is not None

    r = c.post(
        f"/api/orders/{order['id']}/reopen",
        json={"expected_version": body["version"], "reason_code": "NEED_CORRECTION"},
    )
    assert r.status_code == 200, r.text
    reopened = r.json()
    assert reopened["status"] == "CONFIRMED"
    assert reopened["closed_at"] is None

    audit = c.get("/api/audit", params={"entity_type": "order", "entity_id": str(order["id"])})
    assert audit.status_code == 200
    actions = {e["action"] for e in audit.json()}
    assert "close" in actions
    assert "reopen" in actions


def test_close_blocked_commitment(admin_client):
    c = admin_client
    order = _draft_with_item(c, code="CLOSE-CMT-1", line_kind="COMMITMENT")
    r = c.post(
        f"/api/orders/{order['id']}/close",
        json={"expected_version": order["version"], "reason_code": "DONE"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "commitment_open"


def test_close_requires_reason_and_confirmed(admin_client):
    c = admin_client
    order = _draft_with_item(c, code="CLOSE-RSN-1")
    r = c.post(
        f"/api/orders/{order['id']}/close",
        json={"expected_version": order["version"], "reason_code": "   "},
    )
    assert r.status_code == 422

    r = c.post(
        f"/api/orders/{order['id']}/reopen",
        json={"expected_version": order["version"], "reason_code": "TOO_EARLY"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "invalid_transition"
