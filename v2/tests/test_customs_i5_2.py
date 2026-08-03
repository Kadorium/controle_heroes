"""Customs I5-2 — Doganale versionada, divergências, provenance."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
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
    r = client.post(f"/api/invoices/{inv['id']}/issue", json={"expected_version": inv["version"]})
    assert r.status_code == 200, r.text
    return r.json()


def _process(client):
    r = client.post("/api/import-processes", json={"external_reference": f"DUIMP-{_uid()}"})
    assert r.status_code == 201, r.text
    return r.json()


def test_migration_012_revises_011():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("012")
    assert rev is not None
    assert rev.down_revision == "011"


def test_doganale_create_activate_supersede_history(admin_client):
    client = admin_client
    tag = _uid()
    _, product, order = _confirmed_order(client, tag=tag)
    inv = _issued_invoice(client, order, number=f"INV-{tag}")
    process = _process(client)
    r = client.post(
        f"/api/import-processes/{process['id']}/invoices",
        json={"expected_version": process["version"], "invoice_id": inv["id"]},
    )
    assert r.status_code == 200, r.text

    # empty doganale
    r = client.get(f"/api/import-processes/{process['id']}/doganale")
    assert r.status_code == 200
    assert r.json() is None

    # create v1
    r = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions",
        json={"notes": "v1", "idempotency_key": f"dog-{tag}-v1"},
    )
    assert r.status_code == 201, r.text
    v1 = r.json()
    assert v1["status"] == "DRAFT"
    assert v1["is_current"] is False
    assert v1["version_number"] == 1

    # idempotent create
    r2 = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions",
        json={"notes": "ignored", "idempotency_key": f"dog-{tag}-v1"},
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == v1["id"]

    # lines
    item_id = inv["items"][0]["id"]
    r = client.put(
        f"/api/import-processes/{process['id']}/doganale/versions/{v1['id']}/lines",
        json={
            "expected_version": v1["version"],
            "lines": [
                {
                    "position": 1,
                    "ncm": "84713012",
                    "description": "Notebook",
                    "quantity": "10",
                    "unit": "UN",
                    "currency": "EUR",
                    "unit_price": "100",
                    "manufacturer": "ACME",
                    "origin_country": "CN",
                    "acquisition_country": "IT",
                    "net_weight_kg": "12.5",
                    "gross_weight_kg": "15",
                    "pallet_count": "1",
                    "invoice_id": inv["id"],
                    "invoice_item_id": item_id,
                    "product_id": product["id"],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    v1 = r.json()
    assert len(v1["lines"]) == 1
    assert v1["lines"][0]["line_amount"] == "1000.0000"
    assert v1["lines"][0]["pallet_count"] == "1.0000"

    # activate
    r = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions/{v1['id']}/activate",
        json={"expected_version": v1["version"]},
    )
    assert r.status_code == 200, r.text
    v1 = r.json()
    assert v1["status"] == "ACTIVE"
    assert v1["is_current"] is True

    # immutable lines on ACTIVE
    r = client.put(
        f"/api/import-processes/{process['id']}/doganale/versions/{v1['id']}/lines",
        json={"expected_version": v1["version"], "lines": []},
    )
    assert r.status_code == 409

    # supersede → new DRAFT
    r = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions/{v1['id']}/supersede",
        json={"expected_version": v1["version"], "notes": "retificação"},
    )
    assert r.status_code == 200, r.text
    v2 = r.json()
    assert v2["version_number"] == 2
    assert v2["status"] == "DRAFT"
    assert len(v2["lines"]) == 1

    # change qty on v2 and activate → v1 SUPERSEDED
    r = client.put(
        f"/api/import-processes/{process['id']}/doganale/versions/{v2['id']}/lines",
        json={
            "expected_version": v2["version"],
            "lines": [
                {
                    "position": 1,
                    "ncm": "84713012",
                    "description": "Notebook retificado",
                    "quantity": "9",
                    "unit": "UN",
                    "currency": "EUR",
                    "unit_price": "100",
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    v2 = r.json()
    r = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions/{v2['id']}/activate",
        json={"expected_version": v2["version"]},
    )
    assert r.status_code == 200, r.text
    v2 = r.json()
    assert v2["is_current"] is True
    assert v2["status"] == "ACTIVE"

    summary = client.get(f"/api/import-processes/{process['id']}/doganale").json()
    assert summary["current_version_id"] == v2["id"]
    by_num = {v["version_number"]: v for v in summary["versions"]}
    assert by_num[1]["status"] == "SUPERSEDED"
    assert by_num[1]["is_current"] is False
    assert by_num[2]["is_current"] is True

    # only one current
    currents = [v for v in summary["versions"] if v["is_current"]]
    assert len(currents) == 1


def test_doganale_optimistic_lock_and_empty_not_zero(admin_client):
    client = admin_client
    process = _process(client)
    v = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions",
        json={},
    ).json()
    r = client.put(
        f"/api/import-processes/{process['id']}/doganale/versions/{v['id']}/lines",
        json={
            "expected_version": 999,
            "lines": [{"position": 1, "description": "x", "quantity": ""}],
        },
    )
    assert r.status_code == 409

    r = client.put(
        f"/api/import-processes/{process['id']}/doganale/versions/{v['id']}/lines",
        json={
            "expected_version": v["version"],
            "lines": [{"position": 1, "description": "sem qty", "quantity": ""}],
        },
    )
    assert r.status_code == 200, r.text
    line = r.json()["lines"][0]
    assert line["quantity"] is None
    assert line["unit_price"] is None
    assert line["line_amount"] is None


def test_divergence_and_provenance(admin_client):
    client = admin_client
    process = _process(client)
    v = client.post(
        f"/api/import-processes/{process['id']}/doganale/versions",
        json={},
    ).json()
    r = client.post(
        f"/api/import-processes/{process['id']}/divergences",
        json={
            "kind": "QTY",
            "message": "Qty doganale difere da invoice",
            "severity": "WARN",
            "doganale_version_id": v["id"],
            "field_name": "quantity",
            "expected_value": "10",
            "actual_value": "9",
        },
    )
    assert r.status_code == 201, r.text
    divs = client.get(f"/api/import-processes/{process['id']}/divergences").json()
    assert len(divs) == 1
    assert divs[0]["kind"] == "QTY"

    r = client.post(
        f"/api/import-processes/{process['id']}/provenances",
        json={
            "entity_type": "doganale_version",
            "entity_id": str(v["id"]),
            "source_kind": "MANUAL_UI",
            "adapter_key": "j5-i5-2",
        },
    )
    assert r.status_code == 201, r.text
    # idempotent upsert same entity/source
    r2 = client.post(
        f"/api/import-processes/{process['id']}/provenances",
        json={
            "entity_type": "doganale_version",
            "entity_id": str(v["id"]),
            "source_kind": "MANUAL_UI",
            "notes": "updated",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == r.json()["id"]
    assert r2.json()["notes"] == "updated"


def test_doganale_rbac_read_only(client, db, admin_client):
    import json

    from app.identity.models import Role, User
    from app.identity.security import hash_password

    role = Role(
        name=f"dog_ro_{_uid()}",
        description="ro",
        permissions_json=json.dumps(["customs:read"]),
    )
    db.add(role)
    db.flush()
    email = f"dogro-{_uid()}@example.com"
    user = User(
        email=email,
        name="ro",
        password_hash=hash_password("test123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    process = _process(admin_client)
    r = client.post("/api/auth/login", json={"email": email, "password": "test123"})
    assert r.status_code == 200
    assert client.get(f"/api/import-processes/{process['id']}/doganale").status_code == 200
    assert (
        client.post(
            f"/api/import-processes/{process['id']}/doganale/versions",
            json={},
        ).status_code
        == 403
    )
