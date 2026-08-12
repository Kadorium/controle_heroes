"""RUX-3B (1/2) — OrderItem COMMITMENT + guards Billing.

Gates:
- Order com 2 linhas COMMITMENT via API pública
- confirm_order variante A + Audit ORDER_CONFIRM_WITH_COMMITMENT
- create_invoice falha com 'nenhuma linha faturável' sem criar Product
- Order com PRODUCT continua faturando
"""

from __future__ import annotations

import json
import uuid

import pytest


def _supplier(db) -> int:
    from app.catalog import public as catalog_public

    name = f"RUX3B Sup {uuid.uuid4().hex[:8]}"
    return catalog_public.create_supplier(db, name=name, country_code="IT").id


def _product(db, sku: str) -> int:
    from app.catalog import public as catalog_public

    try:
        return catalog_public.get_product_by_sku(db, sku).id
    except Exception:
        return catalog_public.create_product(
            db, sku=sku, description=f"desc {sku}"
        ).id


def test_commitment_order_confirm_and_invoice_blocked(admin_client, db):
    from app.audit import public as audit_public
    from app.catalog.models import Product

    products_before = db.query(Product).count()
    sid = _supplier(db)
    db.commit()

    r = admin_client.post(
        "/api/orders",
        json={
            "code": f"RUX3B-C-{uuid.uuid4().hex[:8]}",
            "supplier_id": sid,
            "currency": "EUR",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    oid = order["id"]
    ver = order["version"]

    for idx, code in enumerate(("I.V. 2", "I.V. 1")):
        r = admin_client.post(
            f"/api/orders/{oid}/items",
            json={
                "expected_version": ver,
                "line_kind": "COMMITMENT",
                "external_code": code,
                "description": f"racchette compromisso {code}",
                "quantity": "100",
                "unit_price": "10.00",
                "unit": "PZ",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        ver = body["version"]
        item = body["items"][idx]
        assert item["line_kind"] == "COMMITMENT"
        assert item["product_id"] is None
        assert item["external_code"] == code

    assert len(body["items"]) == 2

    r = admin_client.post(
        f"/api/orders/{oid}/confirm",
        json={"expected_version": ver},
    )
    assert r.status_code == 200, r.text
    confirmed = r.json()
    assert confirmed["status"] == "CONFIRMED"
    ver = confirmed["version"]

    events = audit_public.history_by_entity(db, "order", str(oid), limit=20)
    confirm_ev = next(
        (e for e in events if e.action == "confirm"),
        None,
    )
    assert confirm_ev is not None
    assert confirm_ev.reason_code == "ORDER_CONFIRM_WITH_COMMITMENT"
    details = json.loads(confirm_ev.details or "{}")
    assert details["commitment_count"] == 2
    assert details["product_count"] == 0
    assert details["total_items"] == 2

    # RUX-3F: disponibilidade honesta — COMMITMENT não é "Disponível" faturável
    qty = admin_client.get(f"/api/orders/{oid}/invoiced-quantities")
    assert qty.status_code == 200, qty.text
    qty_rows = qty.json()
    assert len(qty_rows) == 2
    for row in qty_rows:
        assert row["billable"] is False
        assert row["line_kind"] == "COMMITMENT"
        assert row["available_qty"] in ("0", "0.0000", "0.0")
        assert row.get("description")

    r = admin_client.post(
        f"/api/orders/{oid}/invoices",
        json={
            "invoice_number": f"INV-RUX3B-{uuid.uuid4().hex[:6]}",
            "invoice_type": "FINAL",
        },
    )
    assert r.status_code == 400, r.text
    assert "nenhuma linha faturável" in r.text

    products_after = db.query(Product).count()
    assert products_after == products_before, "create_invoice não deve inventar Product"


def test_product_order_still_invoices(admin_client, db):
    """Regressão: Order só PRODUCT continua faturando."""
    sid = _supplier(db)
    pid = _product(db, f"RUX3B-SKU-{uuid.uuid4().hex[:8]}")
    db.commit()

    r = admin_client.post(
        "/api/orders",
        json={
            "code": f"RUX3B-P-{uuid.uuid4().hex[:8]}",
            "supplier_id": sid,
            "currency": "EUR",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    oid = order["id"]
    ver = order["version"]

    r = admin_client.post(
        f"/api/orders/{oid}/items",
        json={
            "expected_version": ver,
            "product_id": pid,
            "quantity": "5",
            "unit_price": "12.50",
            "unit": "PZ",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["items"][0]["line_kind"] == "PRODUCT"
    assert body["items"][0]["product_id"] == pid
    ver = body["version"]

    r = admin_client.post(
        f"/api/orders/{oid}/confirm",
        json={"expected_version": ver},
    )
    assert r.status_code == 200, r.text

    r = admin_client.post(
        f"/api/orders/{oid}/invoices",
        json={
            "invoice_number": f"INV-OK-{uuid.uuid4().hex[:6]}",
            "invoice_type": "FINAL",
        },
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["status"] == "DRAFT"
    assert len(inv["items"]) == 1
    assert inv["items"][0]["product_id"] == pid


def test_mixed_order_invoice_only_product_lines(admin_client, db):
    """create_invoice inclui só linhas com product_id."""
    sid = _supplier(db)
    pid = _product(db, f"RUX3B-MIX-{uuid.uuid4().hex[:8]}")
    db.commit()

    r = admin_client.post(
        "/api/orders",
        json={
            "code": f"RUX3B-M-{uuid.uuid4().hex[:8]}",
            "supplier_id": sid,
            "currency": "EUR",
        },
    )
    oid = r.json()["id"]
    ver = r.json()["version"]

    r = admin_client.post(
        f"/api/orders/{oid}/items",
        json={
            "expected_version": ver,
            "product_id": pid,
            "quantity": "1",
            "unit_price": "9.00",
        },
    )
    ver = r.json()["version"]
    r = admin_client.post(
        f"/api/orders/{oid}/items",
        json={
            "expected_version": ver,
            "line_kind": "COMMITMENT",
            "external_code": "I.V. X",
            "description": "só compromisso",
            "quantity": "50",
            "unit_price": "1.00",
        },
    )
    ver = r.json()["version"]

    r = admin_client.post(
        f"/api/orders/{oid}/confirm",
        json={"expected_version": ver},
    )
    assert r.status_code == 200, r.text

    # RUX-3F I1: qty availability — PRODUCT billable; COMMITMENT not
    qty = admin_client.get(f"/api/orders/{oid}/invoiced-quantities")
    assert qty.status_code == 200, qty.text
    by_kind = {row["line_kind"]: row for row in qty.json()}
    assert by_kind["PRODUCT"]["billable"] is True
    assert by_kind["PRODUCT"]["available_qty"] not in ("0", "0.0", "0.0000")
    assert by_kind["COMMITMENT"]["billable"] is False
    assert by_kind["COMMITMENT"]["available_qty"] in ("0", "0.0", "0.0000")
    assert by_kind["COMMITMENT"].get("description")

    r = admin_client.post(
        f"/api/orders/{oid}/invoices",
        json={
            "invoice_number": f"INV-MIX-{uuid.uuid4().hex[:6]}",
            "invoice_type": "FINAL",
        },
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert len(inv["items"]) == 1
    assert inv["items"][0]["product_id"] == pid
