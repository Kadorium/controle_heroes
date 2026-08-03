"""Customs I5-1 API tests — ImportProcess core."""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from io import BytesIO

import pytest
from sqlalchemy.orm import Session

from app.identity.models import Role, User
from app.identity.security import hash_password


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


def _shipment_with_item(client, order, *, tag: str, qty="4"):
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


def test_create_get_list_unique_code(admin_client):
    c = admin_client
    r = c.post("/api/import-processes", json={"external_reference": "DUIMP-A", "notes": "n1"})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["code"].startswith("IMP-")
    assert p["status"] == "DRAFT"
    assert p["version"] == 1

    r = c.get(f"/api/import-processes/{p['id']}")
    assert r.status_code == 200
    assert r.json()["code"] == p["code"]

    rows = c.get("/api/import-processes").json()
    assert any(x["id"] == p["id"] for x in rows)


def test_link_invoices_unique_and_issued_only(admin_client):
    c = admin_client
    tag = _uid()
    _, _, o1 = _confirmed_order(c, tag=f"I1{tag}", qty="10")
    _, _, o2 = _confirmed_order(c, tag=f"I2{tag}", qty="10")
    inv1 = _issued_invoice(c, o1, number=f"INV-{tag}-1")
    inv2 = _issued_invoice(c, o2, number=f"INV-{tag}-2")

    # draft invoice
    draft = c.post(f"/api/orders/{o1['id']}/invoices", json={"invoice_number": f"DR-{tag}"}).json()

    p = c.post("/api/import-processes", json={"external_reference": f"D-{tag}"}).json()
    r = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": draft["id"]},
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "invoice_not_issued"

    r = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv1["id"]},
    )
    assert r.status_code == 200, r.text
    p = r.json()
    r = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv2["id"]},
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert len(p["invoices"]) == 2

    p2 = c.post("/api/import-processes", json={"external_reference": f"D2-{tag}"}).json()
    r = c.post(
        f"/api/import-processes/{p2['id']}/invoices",
        json={"expected_version": p2["version"], "invoice_id": inv1["id"]},
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "invoice_already_linked"


def test_invoice_item_allocation_and_over(admin_client):
    c = admin_client
    tag = _uid()
    _, _, o = _confirmed_order(c, tag=f"IA{tag}", qty="10")
    inv = _issued_invoice(c, o, number=f"INV-A-{tag}", qty="10")
    item_id = inv["items"][0]["id"]

    p = c.post("/api/import-processes", json={"external_reference": f"DA-{tag}"}).json()
    p = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv["id"]},
    ).json()

    r = c.post(
        f"/api/import-processes/{p['id']}/invoice-items/allocate",
        json={
            "expected_version": p["version"],
            "invoice_item_id": item_id,
            "allocated_qty": "4",
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert len(p["invoice_item_allocations"]) == 1

    r = c.post(
        f"/api/import-processes/{p['id']}/invoice-items/allocate",
        json={
            "expected_version": p["version"],
            "invoice_item_id": item_id,
            "allocated_qty": "11",
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "over_allocation"

    residuals = c.get(f"/api/import-processes/{p['id']}/residuals/invoice-items").json()
    assert residuals[0]["allocated_qty"].startswith("4")


def test_multi_shipment_alloc_unique(admin_client):
    c = admin_client
    tag = _uid()
    _, _, o = _confirmed_order(c, tag=f"S{tag}", qty="20")
    inv = _issued_invoice(c, o, number=f"INV-S-{tag}", qty="20")
    sh1 = _shipment_with_item(c, o, tag=f"S1{tag}", qty="5")
    sh2 = _shipment_with_item(c, o, tag=f"S2{tag}", qty="5")

    p = c.post("/api/import-processes", json={"external_reference": f"DS-{tag}"}).json()
    p = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv["id"]},
    ).json()
    p = c.post(
        f"/api/import-processes/{p['id']}/shipments",
        json={"expected_version": p["version"], "shipment_id": sh1["id"]},
    ).json()
    p = c.post(
        f"/api/import-processes/{p['id']}/shipments",
        json={"expected_version": p["version"], "shipment_id": sh2["id"]},
    ).json()
    assert len(p["shipments"]) == 2

    si = sh1["items"][0]["id"]
    p = c.post(
        f"/api/import-processes/{p['id']}/shipment-items/allocate",
        json={
            "expected_version": p["version"],
            "shipment_item_id": si,
            "allocated_qty": "3",
        },
    ).json()
    r = c.post(
        f"/api/import-processes/{p['id']}/shipment-items/allocate",
        json={
            "expected_version": p["version"],
            "shipment_item_id": si,
            "allocated_qty": "9",
        },
    )
    assert r.status_code == 409

    p2 = c.post("/api/import-processes", json={"external_reference": f"DS2-{tag}"}).json()
    r = c.post(
        f"/api/import-processes/{p2['id']}/shipments",
        json={"expected_version": p2["version"], "shipment_id": sh1["id"]},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "shipment_already_linked"


def test_submit_cancel_lock_structure(admin_client):
    c = admin_client
    tag = _uid()
    _, _, o = _confirmed_order(c, tag=f"L{tag}", qty="10")
    inv = _issued_invoice(c, o, number=f"INV-L-{tag}")
    p = c.post("/api/import-processes", json={}).json()
    r = c.post(
        f"/api/import-processes/{p['id']}/submit",
        json={"expected_version": p["version"]},
    )
    assert r.status_code == 422
    assert r.json()["error"] == "external_reference_required"

    p = c.patch(
        f"/api/import-processes/{p['id']}",
        json={"expected_version": p["version"], "external_reference": f"DU-{tag}"},
    ).json()
    r = c.post(
        f"/api/import-processes/{p['id']}/submit",
        json={"expected_version": p["version"]},
    )
    assert r.status_code == 422
    assert r.json()["error"] == "invoice_required"

    p = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv["id"]},
    ).json()
    p = c.post(
        f"/api/import-processes/{p['id']}/submit",
        json={"expected_version": p["version"]},
    ).json()
    assert p["status"] == "SUBMITTED"
    assert p["submitted_at"]

    r = c.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv["id"]},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "process_not_draft"

    # stale version
    r = c.post(
        f"/api/import-processes/{p['id']}/cancel",
        json={"expected_version": 1, "reason": "stale"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "conflict"

    p = c.post(
        f"/api/import-processes/{p['id']}/cancel",
        json={"expected_version": p["version"], "reason": "abort test"},
    ).json()
    assert p["status"] == "CANCELLED"
    assert p["cancel_reason"] == "abort test"


def test_documents_link_import_process(admin_client):
    c = admin_client
    p = c.post("/api/import-processes", json={"external_reference": "DOC-1"}).json()
    r = c.post(
        "/api/documents",
        files={"file": ("duimp.pdf", BytesIO(b"%PDF-1.4 d"), "application/pdf")},
        data={"entity_type": "import_process", "entity_id": str(p["id"]), "role": "official"},
    )
    assert r.status_code == 200, r.text
    docs = c.get(f"/api/documents?entity_type=import_process&entity_id={p['id']}")
    assert docs.status_code == 200
    assert len(docs.json()) >= 1


def test_customs_rbac(client, db: Session, admin_client):
    role = Role(
        name="customs_ro",
        description="ro",
        permissions_json=json.dumps(["customs:read"]),
    )
    db.add(role)
    db.flush()
    user = User(
        email="customsro@example.com",
        name="ro",
        password_hash=hash_password("test123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    p = admin_client.post("/api/import-processes", json={"external_reference": "RBAC"}).json()
    r = client.post("/api/auth/login", json={"email": "customsro@example.com", "password": "test123"})
    assert r.status_code == 200
    assert client.get("/api/import-processes").status_code == 200
    assert client.get(f"/api/import-processes/{p['id']}").status_code == 200
    assert (
        client.post("/api/import-processes", json={"external_reference": "NOPE"}).status_code == 403
    )


def test_migration_011_revises_010():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("011")
    assert rev is not None
    assert rev.down_revision == "010"


def test_audit_on_create(admin_client, db: Session):
    from app.audit.models import AuditLog

    p = admin_client.post("/api/import-processes", json={"external_reference": "AUD"}).json()
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "import_process",
            AuditLog.entity_id == str(p["id"]),
            AuditLog.action == "import_process.create",
        )
        .all()
    )
    assert len(rows) >= 1
