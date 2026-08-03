"""Billing API — SC-01/SC-02 e matriz Inc-2."""

import uuid
from datetime import date, timedelta
from io import BytesIO


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _sup_prod(client, sku=None):
    sku = sku or f"BILL-{_uid()}"
    s = client.post("/api/suppliers", json={"name": f"Heroes-{_uid()}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    assert "id" in p, p
    return s, p


def _confirmed_order(client, *, code: str | None = None, qty="10", price="100", sku=None):
    code = code or f"ORD-{_uid()}"
    s, p = _sup_prod(client, sku=sku)
    r = client.post(
        "/api/orders",
        json={"code": code, "supplier_id": s["id"], "currency": "EUR"},
    )
    assert r.status_code == 201, r.text
    o = r.json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": qty,
            "unit_price": price,
        },
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/confirm",
        json={"expected_version": o["version"]},
    ).json()
    return o, s


def _attach_doc(client, invoice_id: int):
    r = client.post(
        "/api/documents",
        files={"file": ("fattura.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(invoice_id), "role": "official"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _set_discount_percent(client, inv, pct="10"):
    item = inv["items"][0]
    r = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": item["quantity"],
                    "unit_price_gross": item["unit_price_gross"],
                    "discount_type": "PERCENT",
                    "discount_percent": pct,
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _set_terms_percent(client, inv, parts=None):
    parts = parts or [("30", 30), ("70", 60)]
    today = date.today()
    terms = []
    for pct, days in parts:
        terms.append({"due_date": (today + timedelta(days=days)).isoformat(), "percent": pct})
    r = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={"expected_version": inv["version"], "mode": "PERCENT", "terms": terms},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_sc01_sc02_issue_payables(admin_client):
    """SC-01 order→invoice; SC-02 N scadenze → N payables; saldo = Σ."""
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-SC01", qty="10", price="100")
    r = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-202", "invoice_type": "FINAL"},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["status"] == "DRAFT"
    assert inv["supplier_id"] == order["supplier_id"]
    assert inv["currency"] == "EUR"
    assert inv["incomplete_line_count"] >= 1

    inv = _set_discount_percent(c, inv, "10")
    assert inv["net_amount"] == "900.00"
    assert inv["items"][0]["line_gross_amount"] == "1000.00"
    assert inv["items"][0]["line_discount_amount"] == "100.00"

    inv = _set_terms_percent(c, inv)
    assert len(inv["payables_preview"]) == 2
    assert inv["payables_preview"][0]["amount"] == "270.00"
    assert inv["payables_preview"][1]["amount"] == "630.00"

    _attach_doc(c, inv["id"])
    inv = c.get(f"/api/invoices/{inv['id']}").json()
    assert inv["blockers"] == []

    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["status"] == "ISSUED"
    assert len(inv["payables"]) == 2
    assert inv["payables_sum"] == "900.00"
    assert inv["balance"] == "900.00"
    assert sum(float(p["amount"]) for p in inv["payables"]) == 900.0

    # idempotent issue
    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["payables"]) == 2

    # immutable
    r = c.patch(
        f"/api/invoices/{inv['id']}",
        json={"expected_version": inv["version"], "notes": "x"},
    )
    assert r.status_code == 409

    pays = c.get("/api/payables", params={"invoice_id": inv["id"]}).json()
    assert len(pays) == 2


def test_discount_none_and_unit_amount(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-DISC", qty="2", price="50", sku="D1")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-D1"},
    ).json()
    item = inv["items"][0]
    inv = c.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "2",
                    "unit_price_gross": "50",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    assert inv["net_amount"] == "100.00"

    order2, _ = _confirmed_order(c, code="INV-DISC2", qty="2", price="50", sku="D2")
    inv2 = c.post(
        f"/api/orders/{order2['id']}/invoices",
        json={"invoice_number": "F-D2"},
    ).json()
    item = inv2["items"][0]
    inv2 = c.put(
        f"/api/invoices/{inv2['id']}/items",
        json={
            "expected_version": inv2["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "2",
                    "unit_price_gross": "50",
                    "discount_type": "UNIT_AMOUNT",
                    "discount_unit_amount": "5",
                }
            ],
        },
    ).json()
    assert inv2["items"][0]["line_discount_amount"] == "10.00"
    assert inv2["net_amount"] == "90.00"


def test_undefined_discount_blocks_issue(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-UNDEF", sku="U1")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-U1"},
    ).json()
    inv = _set_terms_percent(c, inv)
    _attach_doc(c, inv["id"])
    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 400
    assert "Desconto indefinido" in r.json()["message"]


def test_terms_amount_and_mixed_forbidden(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-AMT", qty="1", price="100", sku="A1")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-A1"},
    ).json()
    inv = _set_discount_percent(c, inv, "0")
    # force NONE via percent 0 → net 100; use NONE
    item = inv["items"][0]
    inv = c.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "1",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    today = date.today()
    r = c.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [
                {"due_date": today.isoformat(), "amount": "40"},
                {"due_date": (today + timedelta(days=30)).isoformat(), "amount": "60"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["terms_mode"] == "AMOUNT"

    r = c.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "PERCENT",
            "terms": [{"due_date": today.isoformat(), "percent": "50", "amount": "10"}],
        },
    )
    assert r.status_code == 400


def test_partial_invoicing_and_overbill(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-PART", qty="10", price="10", sku="P1")
    # first invoice 4 units
    inv1 = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-P1", "order_item_ids": [order["items"][0]["id"]]},
    ).json()
    item = inv1["items"][0]
    inv1 = c.put(
        f"/api/invoices/{inv1['id']}/items",
        json={
            "expected_version": inv1["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "4",
                    "unit_price_gross": "10",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    inv1 = _set_terms_percent(c, inv1, [("100", 0)])
    _attach_doc(c, inv1["id"])
    inv1 = c.post(
        f"/api/invoices/{inv1['id']}/issue",
        json={"expected_version": inv1["version"]},
    ).json()
    assert inv1["status"] == "ISSUED"

    qty = c.get(f"/api/orders/{order['id']}/invoiced-quantities").json()
    assert qty[0]["issued_qty"] == "4.0000"
    assert qty[0]["available_qty"] == "6.0000"

    # second invoice tries 7 → fail
    inv2 = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-P2"},
    ).json()
    item = inv2["items"][0]
    inv2 = c.put(
        f"/api/invoices/{inv2['id']}/items",
        json={
            "expected_version": inv2["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "7",
                    "unit_price_gross": "10",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    inv2 = _set_terms_percent(c, inv2, [("100", 0)])
    _attach_doc(c, inv2["id"])
    r = c.post(
        f"/api/invoices/{inv2['id']}/issue",
        json={"expected_version": inv2["version"]},
    )
    assert r.status_code == 400
    assert "excede" in r.json()["message"]

    # second invoice 6 → ok
    inv2 = c.put(
        f"/api/invoices/{inv2['id']}/items",
        json={
            "expected_version": inv2["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "6",
                    "unit_price_gross": "10",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    # terms still valid
    inv2 = c.get(f"/api/invoices/{inv2['id']}").json()
    r = c.post(
        f"/api/invoices/{inv2['id']}/issue",
        json={"expected_version": inv2["version"]},
    )
    assert r.status_code == 200, r.text


def test_duplicate_number_and_conflict(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-DUP", sku="DUP1")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "SAME"},
    ).json()
    r = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "SAME"},
    )
    assert r.status_code == 400

    r = c.patch(
        f"/api/invoices/{inv['id']}",
        json={"expected_version": 999, "notes": "x"},
    )
    assert r.status_code == 409


def test_document_required_and_override(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-DOC", qty="1", price="10", sku="DOC1")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-DOC"},
    ).json()
    inv = _set_discount_percent(c, inv, "0")
    item = inv["items"][0]
    inv = c.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "1",
                    "unit_price_gross": "10",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    inv = _set_terms_percent(c, inv, [("100", 0)])
    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 400

    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={
            "expected_version": inv["version"],
            "issue_without_document": True,
            "reason_code": "DOC_OVERRIDE_TEST",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["issue_without_document"] is True


def test_cancel_draft_only(admin_client):
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-CAN", sku="C1")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-C1"},
    ).json()
    r = c.post(
        f"/api/invoices/{inv['id']}/cancel",
        json={"expected_version": inv["version"], "reason_code": "DRAFT_ABORT"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"


def test_get_payable_by_id(admin_client):
    """D0.5 — GET /api/payables/{id} sem scan list(limit=100)."""
    c = admin_client
    order, _ = _confirmed_order(c, code="INV-PAY-BY-ID", qty="10", price="100")
    inv = c.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": "F-PAY-ID"},
    ).json()
    inv = _set_discount_percent(c, inv, "0")
    inv = _set_terms_percent(c, inv)
    _attach_doc(c, inv["id"])
    inv = c.get(f"/api/invoices/{inv['id']}").json()
    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 200, r.text
    pays = r.json()["payables"]
    assert len(pays) >= 1
    pid = pays[0]["id"]

    got = c.get(f"/api/payables/{pid}")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["id"] == pid
    assert body["invoice_id"] == inv["id"]
    assert body["currency"] == "EUR"
    assert "balance" in body
    assert "sequence" in body

    missing = c.get("/api/payables/999999001")
    assert missing.status_code == 404
