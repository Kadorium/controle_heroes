"""G2 — bind_commitment_product: COMMITMENT → PRODUCT em pedido CONFIRMED."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.billing.models import Invoice, InvoiceItem


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _supplier(client) -> int:
    r = client.post(
        "/api/suppliers",
        json={"name": f"G2 Sup {_uid()}", "country_code": "IT"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _product(client, *, sku: str | None = None, description: str = "cat GRAFICATE", is_active: bool = True) -> dict:
    r = client.post(
        "/api/products",
        json={
            "sku": sku or f"CAT-G2-{_uid()}",
            "description": description,
            "is_active": is_active,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _draft_commitment_order(client, *, code: str | None = None, external_code: str = "I.V. 2"):
    sid = _supplier(client)
    r = client.post(
        "/api/orders",
        json={
            "code": code or f"G2-{_uid()}",
            "supplier_id": sid,
            "currency": "EUR",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    r = client.post(
        f"/api/orders/{order['id']}/items",
        json={
            "expected_version": order["version"],
            "line_kind": "COMMITMENT",
            "external_code": external_code,
            "description": "racchette 2027 GRAFICATE",
            "quantity": "14600",
            "unit_price": "3.50",
            "unit": "PZ",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _confirmed_commitment_order(client, *, external_code: str = "I.V. 2"):
    order = _draft_commitment_order(client, external_code=external_code)
    r = client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_bind_confirmed_commitment_success_and_audit(admin_client, db):
    from app.audit import public as audit_public

    order = _confirmed_commitment_order(admin_client)
    item = order["items"][0]
    product = _product(admin_client, description="racchette 2027 GRAFICATE cat")
    qty_before = item["quantity"]
    price_before = item["unit_price"]
    unit_before = item["unit"]

    r = admin_client.post(
        f"/api/orders/{order['id']}/items/{item['id']}/bind-product",
        json={"expected_version": order["version"], "product_id": product["id"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    bound = next(i for i in body["items"] if i["id"] == item["id"])
    assert bound["line_kind"] == "PRODUCT"
    assert bound["product_id"] == product["id"]
    assert bound["external_code"] == "I.V. 2"
    assert bound["sku_snapshot"] == product["sku"]
    assert bound["description_snapshot"] == product["description"]
    assert bound["quantity"] == qty_before
    assert bound["unit_price"] == price_before
    assert bound["unit"] == unit_before

    qty = admin_client.get(f"/api/orders/{order['id']}/invoiced-quantities")
    assert qty.status_code == 200, qty.text
    row = next(x for x in qty.json() if x["order_item_id"] == item["id"])
    assert row["billable"] is True
    assert Decimal(row["available_qty"]) == Decimal(qty_before) - Decimal(row["issued_qty"])

    events = audit_public.history_by_entity(db, "order", str(order["id"]), limit=20)
    bind_ev = next((e for e in events if e.action == "bind_product"), None)
    assert bind_ev is not None
    details = json.loads(bind_ev.details or "{}")
    assert details["item_id"] == item["id"]
    assert details["from_kind"] == "COMMITMENT"
    assert details["from_external_code"] == "I.V. 2"
    assert details["from_product_id"] is None
    assert details["to_product_id"] == product["id"]
    assert details["to_sku"] == product["sku"]
    assert details["actor"]


def test_bind_issued_invoice_on_line_rejected(admin_client, db):
    order = _confirmed_commitment_order(admin_client)
    item = order["items"][0]
    product = _product(admin_client)
    dummy = _product(admin_client, sku=f"G2-ISS-{_uid()}")

    inv = Invoice(
        order_id=order["id"],
        supplier_id=order["supplier_id"],
        invoice_number=f"G2-ISS-{_uid()}",
        invoice_type="FINAL",
        status="ISSUED",
        invoice_date=date.today(),
        currency="EUR",
        created_by_actor_id="test",
        issued_at=datetime.now(timezone.utc),
    )
    db.add(inv)
    db.flush()
    db.add(
        InvoiceItem(
            invoice_id=inv.id,
            order_item_id=item["id"],
            product_id=dummy["id"],
            sku_snapshot=dummy["sku"],
            description_snapshot=dummy["description"],
            quantity=Decimal("10"),
            unit="PZ",
            unit_price_gross=Decimal("3.50"),
            discount_type="NONE",
            position=1,
        )
    )
    db.commit()

    r = admin_client.post(
        f"/api/orders/{order['id']}/items/{item['id']}/bind-product",
        json={"expected_version": order["version"], "product_id": product["id"]},
    )
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["error"] == "line_already_invoiced"
    assert "emitida" in body["message"].lower() or "ISSUED" in body["message"]


def test_bind_draft_rejected(admin_client):
    order = _draft_commitment_order(admin_client)
    item = order["items"][0]
    product = _product(admin_client)
    r = admin_client.post(
        f"/api/orders/{order['id']}/items/{item['id']}/bind-product",
        json={"expected_version": order["version"], "product_id": product["id"]},
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["error"] == "invalid_transition"
    assert "CONFIRMED" in body["message"]


def test_bind_already_product_rejected(admin_client):
    sid = _supplier(admin_client)
    product = _product(admin_client)
    r = admin_client.post(
        "/api/orders",
        json={"code": f"G2-P-{_uid()}", "supplier_id": sid, "currency": "EUR"},
    )
    assert r.status_code == 201, r.text
    order = r.json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/items",
        json={
            "expected_version": order["version"],
            "product_id": product["id"],
            "quantity": "5",
            "unit_price": "1.00",
            "unit": "PZ",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    item = order["items"][0]
    other = _product(admin_client, sku=f"G2-OTHER-{_uid()}")
    r = admin_client.post(
        f"/api/orders/{order['id']}/items/{item['id']}/bind-product",
        json={"expected_version": order["version"], "product_id": other["id"]},
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "item_not_commitment"


def test_bind_inactive_product_rejected(admin_client):
    order = _confirmed_commitment_order(admin_client)
    item = order["items"][0]
    product = _product(admin_client, sku=f"G2-OFF-{_uid()}", is_active=False)
    r = admin_client.post(
        f"/api/orders/{order['id']}/items/{item['id']}/bind-product",
        json={"expected_version": order["version"], "product_id": product["id"]},
    )
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["error"] == "invalid_product"
    assert "inativo" in body["message"].lower()


def test_bind_missing_product_rejected(admin_client):
    order = _confirmed_commitment_order(admin_client)
    item = order["items"][0]
    r = admin_client.post(
        f"/api/orders/{order['id']}/items/{item['id']}/bind-product",
        json={"expected_version": order["version"], "product_id": 9_999_999},
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "invalid_product"
