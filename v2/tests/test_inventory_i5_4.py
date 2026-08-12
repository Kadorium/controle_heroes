"""J#5 I5-4 — Nationalization + Inventory + SkuPosition."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from alembic.config import Config
from alembic.script import ScriptDirectory


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _confirmed_order(client, *, tag: str, qty="10"):
    s = client.post("/api/suppliers", json={"name": f"Sup-{tag}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": f"SKU-{tag}", "description": f"P {tag}"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{tag}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": qty,
            "unit_price": "100",
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    return s, p, o


def _issued_invoice(client, order, *, number: str, qty: str | None = None):
    inv = client.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": number, "invoice_type": "FINAL"},
    ).json()
    oi = order["items"][0]["id"]
    use_qty = qty or order["items"][0]["quantity"]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": oi,
                    "quantity": use_qty,
                    "unit_price_gross": "100",
                    "discount_type": "PERCENT",
                    "discount_percent": "0",
                }
            ],
        },
    ).json()
    today = date.today()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "PERCENT",
            "terms": [{"due_date": (today + timedelta(days=30)).isoformat(), "percent": "100"}],
        },
    ).json()
    r = client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF-1.4 x"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    assert r.status_code == 200, r.text
    inv = client.get(f"/api/invoices/{inv['id']}").json()
    r = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _shipment_with_item(client, order, *, tag: str, qty="10"):
    provider = client.post(
        "/api/logistics-providers",
        json={
            "legal_name": f"Carrier {tag}",
            "provider_type": "TRANSPORTADOR",
            "active": True,
        },
    ).json()
    sh = client.post(
        "/api/shipments",
        json={"modal": "SEA", "logistics_provider_id": provider["id"]},
    ).json()
    oi = order["items"][0]["id"]
    sh = client.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": oi, "quantity": qty},
    ).json()
    return sh


def _advance_to_arrived(client, shipment):
    today = date.today().isoformat()
    sh = shipment
    for _ in range(3):
        r = client.post(
            f"/api/shipments/{sh['id']}/advance",
            json={"expected_version": sh["version"], "event_date": today},
        )
        assert r.status_code == 200, r.text
        sh = r.json()
    assert sh["status"] == "ARRIVED"
    return sh


def _submitted_process_with_alloc(client, *, tag: str, qty="10"):
    _, product, order = _confirmed_order(client, tag=tag, qty=qty)
    inv = _issued_invoice(client, order, number=f"INV-{tag}", qty=qty)
    sh = _shipment_with_item(client, order, tag=tag, qty=qty)
    p = client.post("/api/import-processes", json={"external_reference": f"DUIMP-{tag}"}).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv["id"]},
    ).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/shipments",
        json={"expected_version": p["version"], "shipment_id": sh["id"]},
    ).json()
    inv_item_id = inv["items"][0]["id"]
    shp_item_id = sh["items"][0]["id"]
    p = client.post(
        f"/api/import-processes/{p['id']}/invoice-items/allocate",
        json={
            "expected_version": p["version"],
            "invoice_item_id": inv_item_id,
            "allocated_qty": qty,
        },
    ).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/shipment-items/allocate",
        json={
            "expected_version": p["version"],
            "shipment_item_id": shp_item_id,
            "allocated_qty": qty,
        },
    ).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/submit",
        json={"expected_version": p["version"]},
    ).json()
    assert p["status"] == "SUBMITTED"
    return {
        "process": p,
        "product": product,
        "order": order,
        "invoice": inv,
        "shipment": sh,
        "invoice_item_id": inv_item_id,
        "shipment_item_id": shp_item_id,
    }


def _nationalize(client, process_id, *, product_id, qty, shipment_item_id=None, invoice_item_id=None):
    r = client.post(f"/api/import-processes/{process_id}/nationalizations", json={})
    assert r.status_code == 201, r.text
    nat = r.json()
    item = {"quantity": str(qty), "product_id": product_id}
    if shipment_item_id is not None:
        item["shipment_item_id"] = shipment_item_id
    if invoice_item_id is not None:
        item["invoice_item_id"] = invoice_item_id
    r = client.post(
        f"/api/import-processes/{process_id}/nationalizations/{nat['id']}/items",
        json={"expected_version": nat["version"], "items": [item]},
    )
    assert r.status_code == 200, r.text
    nat = r.json()
    r = client.post(
        f"/api/import-processes/{process_id}/nationalizations/{nat['id']}/confirm",
        json={"expected_version": nat["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_migration_015_revises_014():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("015")
    assert rev is not None
    assert rev.down_revision == "014"
    assert script.get_revision("014").down_revision == "013"


def test_arrived_does_not_create_stock(admin_client):
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="8")
    _advance_to_arrived(c, ctx["shipment"])
    product_id = ctx["product"]["id"]

    bal = c.get(
        f"/api/inventory/balances?product_id={product_id}&location_code=BONDED-MAIN"
    ).json()
    assert Decimal(bal["qty"]) == 0

    movs = c.get(f"/api/inventory/movements?product_id={product_id}").json()
    assert movs == []


def test_bonded_before_nationalization_ok(admin_client):
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="10")
    product_id = ctx["product"]["id"]

    r = c.post(
        "/api/inventory/receipts",
        json={
            "location_code": "BONDED-MAIN",
            "process_id": ctx["process"]["id"],
            "receipt_type": "BONDED_IN",
        },
    )
    assert r.status_code == 201, r.text
    receipt = r.json()
    r = c.post(
        f"/api/inventory/receipts/{receipt['id']}/lines",
        json={
            "expected_version": receipt["version"],
            "lines": [{"product_id": product_id, "quantity": "6"}],
        },
    )
    assert r.status_code == 200, r.text
    receipt = r.json()
    r = c.post(
        f"/api/inventory/receipts/{receipt['id']}/confirm",
        json={"expected_version": receipt["version"]},
    )
    assert r.status_code == 200, r.text

    bal = c.get(
        f"/api/inventory/balances?product_id={product_id}&location_code=BONDED-MAIN"
    ).json()
    assert Decimal(bal["qty"]) == Decimal("6")


def test_domestic_requires_nationalization(admin_client):
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="10")
    product_id = ctx["product"]["id"]

    r = c.post(
        "/api/inventory/receipts",
        json={
            "location_code": "DOMESTIC-MAIN",
            "process_id": ctx["process"]["id"],
            "receipt_type": "DOMESTIC_IN",
        },
    )
    assert r.status_code == 201, r.text
    receipt = r.json()
    r = c.post(
        f"/api/inventory/receipts/{receipt['id']}/lines",
        json={
            "expected_version": receipt["version"],
            "lines": [{"product_id": product_id, "quantity": "3"}],
        },
    )
    # may accept draft lines then fail on confirm
    if r.status_code == 409:
        assert r.json()["error"] == "nationalization_required"
        return
    assert r.status_code == 200, r.text
    receipt = r.json()
    r = c.post(
        f"/api/inventory/receipts/{receipt['id']}/confirm",
        json={"expected_version": receipt["version"]},
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "nationalization_required"


def test_partial_nat_and_receipt_sc09(admin_client):
    """SC-09: nacionalização parcial + receipt domestic consome residual."""
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="10")
    product_id = ctx["product"]["id"]

    nat = _nationalize(
        c,
        ctx["process"]["id"],
        product_id=product_id,
        qty="4",
        shipment_item_id=ctx["shipment_item_id"],
    )
    assert nat["status"] == "CONFIRMED"
    nat_item_id = nat["items"][0]["id"]

    proc = c.get(f"/api/import-processes/{ctx['process']['id']}").json()
    assert proc["status"] == "PARTIALLY_CLEARED"

    r = c.post(
        "/api/inventory/receipts",
        json={
            "location_code": "DOMESTIC-MAIN",
            "process_id": ctx["process"]["id"],
            "nationalization_id": nat["id"],
            "receipt_type": "DOMESTIC_IN",
        },
    )
    assert r.status_code == 201, r.text
    receipt = r.json()
    r = c.post(
        f"/api/inventory/receipts/{receipt['id']}/lines",
        json={
            "expected_version": receipt["version"],
            "lines": [
                {
                    "product_id": product_id,
                    "quantity": "4",
                    "nationalization_item_id": nat_item_id,
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    receipt = r.json()
    r = c.post(
        f"/api/inventory/receipts/{receipt['id']}/confirm",
        json={"expected_version": receipt["version"]},
    )
    assert r.status_code == 200, r.text

    bal = c.get(
        f"/api/inventory/balances?product_id={product_id}&location_code=DOMESTIC-MAIN"
    ).json()
    assert Decimal(bal["qty"]) == Decimal("4")

    pos = c.get(f"/api/inventory/sku/{product_id}/position").json()
    assert Decimal(pos["available_qty"]) == Decimal("4")
    assert Decimal(pos["cleared_not_received_qty"]) == Decimal("0")
    assert pos["future_order_qty"] is None


def test_full_clear_and_oversubscription_409(admin_client):
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="5")
    product_id = ctx["product"]["id"]

    nat = _nationalize(
        c,
        ctx["process"]["id"],
        product_id=product_id,
        qty="5",
        shipment_item_id=ctx["shipment_item_id"],
    )
    proc = c.get(f"/api/import-processes/{ctx['process']['id']}").json()
    assert proc["status"] == "CLEARED"

    r = c.post(f"/api/import-processes/{ctx['process']['id']}/nationalizations", json={})
    assert r.status_code == 422 or r.status_code == 409, r.text

    # Oversubscribe via second draft on same shipment item — create new process scenario
    tag2 = _uid()
    ctx2 = _submitted_process_with_alloc(c, tag=tag2, qty="3")
    # First nat 2 of 3
    _nationalize(
        c,
        ctx2["process"]["id"],
        product_id=ctx2["product"]["id"],
        qty="2",
        shipment_item_id=ctx2["shipment_item_id"],
    )
    r = c.post(f"/api/import-processes/{ctx2['process']['id']}/nationalizations", json={})
    assert r.status_code == 201, r.text
    nat2 = r.json()
    r = c.post(
        f"/api/import-processes/{ctx2['process']['id']}/nationalizations/{nat2['id']}/items",
        json={
            "expected_version": nat2["version"],
            "items": [
                {
                    "quantity": "2",
                    "product_id": ctx2["product"]["id"],
                    "shipment_item_id": ctx2["shipment_item_id"],
                }
            ],
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "over_nationalization"


def test_receipt_reversal_and_rebuild_sc10(admin_client, db):
    """SC-10: entrada entreposto + reverse append-only + rebuild balances."""
    from app.inventory.models import InventoryMovement, StockBalance

    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="10")
    product_id = ctx["product"]["id"]

    # Bonded receipt
    r = c.post(
        "/api/inventory/receipts",
        json={
            "location_code": "BONDED-MAIN",
            "process_id": ctx["process"]["id"],
            "receipt_type": "BONDED_IN",
        },
    ).json()
    r = c.post(
        f"/api/inventory/receipts/{r['id']}/lines",
        json={
            "expected_version": r["version"],
            "lines": [{"product_id": product_id, "quantity": "7"}],
        },
    ).json()
    r = c.post(
        f"/api/inventory/receipts/{r['id']}/confirm",
        json={"expected_version": r["version"]},
    ).json()
    assert r["status"] == "CONFIRMED"

    before = db.query(InventoryMovement).filter(InventoryMovement.product_id == product_id).count()
    assert before >= 1

    rev = c.post(
        f"/api/inventory/receipts/{r['id']}/reverse",
        json={"expected_version": r["version"]},
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["status"] == "REVERSED"

    after = db.query(InventoryMovement).filter(InventoryMovement.product_id == product_id).count()
    assert after == before + 1  # inverse movement appended

    bal = c.get(
        f"/api/inventory/balances?product_id={product_id}&location_code=BONDED-MAIN"
    ).json()
    assert Decimal(bal["qty"]) == Decimal("0")

    # Corrupt cache then rebuild
    row = (
        db.query(StockBalance)
        .filter(StockBalance.product_id == product_id)
        .first()
    )
    if row:
        row.qty = Decimal("999")
        db.commit()

    rr = c.post("/api/inventory/rebuild-balances", params={"product_id": product_id})
    assert rr.status_code == 200, rr.text
    bal = c.get(
        f"/api/inventory/balances?product_id={product_id}&location_code=BONDED-MAIN"
    ).json()
    assert Decimal(bal["qty"]) == Decimal("0")


def test_double_domestic_from_same_nat_item_blocked(admin_client):
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="10")
    product_id = ctx["product"]["id"]
    nat = _nationalize(
        c,
        ctx["process"]["id"],
        product_id=product_id,
        qty="5",
        shipment_item_id=ctx["shipment_item_id"],
    )
    nat_item_id = nat["items"][0]["id"]

    def _domestic(qty: str):
        r = c.post(
            "/api/inventory/receipts",
            json={
                "location_code": "DOMESTIC-MAIN",
                "process_id": ctx["process"]["id"],
                "nationalization_id": nat["id"],
                "receipt_type": "DOMESTIC_IN",
            },
        ).json()
        r = c.post(
            f"/api/inventory/receipts/{r['id']}/lines",
            json={
                "expected_version": r["version"],
                "lines": [
                    {
                        "product_id": product_id,
                        "quantity": qty,
                        "nationalization_item_id": nat_item_id,
                    }
                ],
            },
        ).json()
        return c.post(
            f"/api/inventory/receipts/{r['id']}/confirm",
            json={"expected_version": r["version"]},
        )

    r1 = _domestic("5")
    assert r1.status_code == 200, r1.text
    r2 = _domestic("1")
    assert r2.status_code == 409, r2.text
    assert r2.json()["error"] == "over_receipt"


def test_sku_position_buckets(admin_client):
    c = admin_client
    tag = _uid()
    ctx = _submitted_process_with_alloc(c, tag=tag, qty="10")
    product_id = ctx["product"]["id"]

    # bonded 3
    r = c.post(
        "/api/inventory/receipts",
        json={
            "location_code": "BONDED-MAIN",
            "process_id": ctx["process"]["id"],
            "receipt_type": "BONDED_IN",
        },
    ).json()
    r = c.post(
        f"/api/inventory/receipts/{r['id']}/lines",
        json={
            "expected_version": r["version"],
            "lines": [{"product_id": product_id, "quantity": "3"}],
        },
    ).json()
    c.post(
        f"/api/inventory/receipts/{r['id']}/confirm",
        json={"expected_version": r["version"]},
    )

    nat = _nationalize(
        c,
        ctx["process"]["id"],
        product_id=product_id,
        qty="4",
        shipment_item_id=ctx["shipment_item_id"],
    )
    # domestic 2 of 4 cleared via RECLASS (conservação física)
    r = c.post(
        "/api/inventory/receipts",
        json={
            "location_code": "DOMESTIC-MAIN",
            "from_location_code": "BONDED-MAIN",
            "process_id": ctx["process"]["id"],
            "nationalization_id": nat["id"],
            "receipt_type": "RECLASS",
        },
    ).json()
    r = c.post(
        f"/api/inventory/receipts/{r['id']}/lines",
        json={
            "expected_version": r["version"],
            "lines": [
                {
                    "product_id": product_id,
                    "quantity": "2",
                    "nationalization_item_id": nat["items"][0]["id"],
                }
            ],
        },
    ).json()
    c.post(
        f"/api/inventory/receipts/{r['id']}/confirm",
        json={"expected_version": r["version"]},
    )

    pos = c.get(f"/api/inventory/sku/{product_id}/position").json()
    assert Decimal(pos["bonded_qty"]) == Decimal("1")
    assert Decimal(pos["available_qty"]) == Decimal("2")
    assert Decimal(pos["cleared_not_received_qty"]) == Decimal("2")
    assert Decimal(pos["bonded_qty"]) + Decimal(pos["available_qty"]) == Decimal("3")
    assert pos["future_order_qty"] is None


def test_default_locations_seeded(admin_client):
    locs = admin_client.get("/api/inventory/locations").json()
    codes = {x["code"] for x in locs}
    assert {"BONDED-MAIN", "DOMESTIC-MAIN", "QUARANTINE-MAIN"} <= codes
