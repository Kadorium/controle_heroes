"""J4-FIN FIN-1 — adiantamento Order (Payment.order_id + FxExecution)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from app.treasury.fx_money import money2, rate6, weighted_rate


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _confirmed_order(client):
    s = client.post("/api/suppliers", json={"name": f"Adv-{_uid()}", "country_code": "IT"}).json()
    p = client.post(
        "/api/products", json={"sku": f"ADV-{_uid()}", "description": "Item"}
    ).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-ADV-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "10",
            "unit_price": "100",
        },
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}
    ).json()
    return s, o


def test_fin1_advance_eur_rate_dates_distinct(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    pay_d = date.today()
    exec_d = pay_d - timedelta(days=3)
    r = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "1000.00",
            "payment_date": pay_d.isoformat(),
            "execution_date": exec_d.isoformat(),
            "rate": "6.20",
            "register_without_fx_document": True,
            "reason_code": "TEST_ADVANCE",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["order_id"] == order["id"]
    assert Decimal(body["amount"]) == Decimal("1000.00")
    assert Decimal(body["brl_amount"]) == Decimal("6200.00")
    assert Decimal(body["rate"]) == Decimal("6.200000")
    assert body["payment_date"] == pay_d.isoformat()
    assert body["execution_date"] == exec_d.isoformat()

    payables = c.get(f"/api/payables?order_id={order['id']}").json()
    assert payables == []


def test_fin1_advance_eur_brl_rate_derived(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    # 12398.88 / 2000 = 6.19944 → rate6
    r = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "2000.00",
            "brl_amount": "12398.88",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "register_without_fx_document": True,
            "reason_code": "TEST_ADVANCE",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(body["brl_amount"]) == Decimal("12398.88")
    assert Decimal(body["rate"]) == rate6(Decimal("12398.88") / Decimal("2000"))


def test_fin1_n_advances_consolidated_weighted_avg(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    today = date.today()
    r1 = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "1000.00",
            "rate": "6.00",
            "payment_date": today.isoformat(),
            "execution_date": (today - timedelta(days=1)).isoformat(),
            "register_without_fx_document": True,
            "reason_code": "TEST_ADVANCE",
            "idempotency_key": f"adv1-{_uid()}",
        },
    )
    assert r1.status_code == 200, r1.text
    r2 = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "500.00",
            "brl_amount": "3200.00",
            "payment_date": today.isoformat(),
            "execution_date": today.isoformat(),
            "register_without_fx_document": True,
            "reason_code": "TEST_ADVANCE",
            "idempotency_key": f"adv2-{_uid()}",
        },
    )
    assert r2.status_code == 200, r2.text

    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    assert listing["consolidated"]["count"] == 2
    assert Decimal(listing["consolidated"]["total_eur"]) == Decimal("1500.00")
    # 6000 + 3200 = 9200 (soma brl; não recálculo)
    assert Decimal(listing["consolidated"]["total_brl"]) == Decimal("9200.00")
    expected_avg = weighted_rate(Decimal("1500"), Decimal("9200"))
    assert Decimal(listing["consolidated"]["weighted_avg_rate"]) == expected_avg

    payables = c.get(f"/api/payables?order_id={order['id']}").json()
    assert payables == [], "adiantamento não pode criar Payable"


def test_fin1_advance_with_fx_pdf(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    today = date.today()
    r = c.post(
        f"/api/orders/{order['id']}/advances/with-document",
        data={
            "amount": "300.00",
            "rate": "6.15",
            "payment_date": today.isoformat(),
            "execution_date": (today - timedelta(days=2)).isoformat(),
        },
        files={"file": ("cambio.pdf", BytesIO(b"%PDF-1.4 fx"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fx_documents"]
    assert Decimal(body["brl_amount"]) == money2(Decimal("300") * Decimal("6.15"))

    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    assert listing["consolidated"]["count"] == 1
    assert listing["advances"][0]["fx_documents"]


def test_fin1_advance_manual_without_pdf(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    today = date.today()
    r = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "100.00",
            "rate": "6.10",
            "payment_date": today.isoformat(),
            "execution_date": today.isoformat(),
            "register_without_fx_document": True,
            "reason_code": "TEST_ADVANCE",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["fx_documents"] == []
