"""J4-FIN FIN-1B — cancel adiantamento + FX void audit (sem apagar FX)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.treasury.fx_money import weighted_rate


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _confirmed_order(client):
    s = client.post("/api/suppliers", json={"name": f"AdvC-{_uid()}", "country_code": "IT"}).json()
    p = client.post(
        "/api/products", json={"sku": f"ADVC-{_uid()}", "description": "Item"}
    ).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-ADVC-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
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


def _post_advance(client, order_id, *, amount, rate=None, brl=None, key=None):
    today = date.today()
    body = {
        "amount": amount,
        "payment_date": today.isoformat(),
        "execution_date": (today - timedelta(days=1)).isoformat(),
        "register_without_fx_document": True,
        "reason_code": "TEST_ADVANCE",
        "idempotency_key": key or f"adv-{_uid()}",
    }
    if rate is not None:
        body["rate"] = rate
    if brl is not None:
        body["brl_amount"] = brl
    r = client.post(f"/api/orders/{order_id}/advances", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_fin1b_cancel_removes_from_consolidated(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    a1 = _post_advance(c, order["id"], amount="1000.00", rate="6.00")
    a2 = _post_advance(c, order["id"], amount="500.00", brl="3200.00")

    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    assert listing["consolidated"]["count"] == 2
    assert Decimal(listing["consolidated"]["total_eur"]) == Decimal("1500.00")
    assert Decimal(listing["consolidated"]["total_brl"]) == Decimal("9200.00")

    # cancel first → consolidado = só a2
    v1 = next(a["version"] for a in listing["advances"] if a["payment_id"] == a1["payment_id"])
    r = c.post(
        f"/api/orders/{order['id']}/advances/{a1['payment_id']}/cancel",
        json={"expected_version": v1, "reason": "taxa errada — era 6,02"},
    )
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["consolidated"]["count"] == 1
    assert Decimal(after["consolidated"]["total_eur"]) == Decimal("500.00")
    assert Decimal(after["consolidated"]["total_brl"]) == Decimal("3200.00")
    assert Decimal(after["consolidated"]["weighted_avg_rate"]) == weighted_rate(
        Decimal("500"), Decimal("3200")
    )

    # FX preservada (não órfã apagada)
    fx_list = c.get(f"/api/payments/{a1['payment_id']}/fx-executions").json()
    assert len(fx_list) == 1
    assert Decimal(fx_list[0]["rate"]) == Decimal("6.000000")

    pay = c.get(f"/api/payments/{a1['payment_id']}").json()
    assert pay["status"] == "CANCELLED"


def test_fin1b_cancel_requires_reason(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    a1 = _post_advance(c, order["id"], amount="100.00", rate="6.10")
    r = c.post(
        f"/api/orders/{order['id']}/advances/{a1['payment_id']}/cancel",
        json={"expected_version": 1, "reason": "   "},
    )
    assert r.status_code == 400


def test_fin1b_cancel_audit_payment_and_fx(admin_client, db):
    c = admin_client
    _s, order = _confirmed_order(c)
    a1 = _post_advance(c, order["id"], amount="200.00", rate="6.20")
    fx_id = a1["fx_execution_id"]

    r = c.post(
        f"/api/orders/{order['id']}/advances/{a1['payment_id']}/cancel",
        json={"expected_version": 1, "reason": "digitou 6,20 em vez de 6,02"},
    )
    assert r.status_code == 200, r.text

    from app.audit.models import AuditLog

    pay_audits = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "payment",
            AuditLog.entity_id == str(a1["payment_id"]),
            AuditLog.action == "cancel",
        )
        .all()
    )
    assert pay_audits
    assert "digitou 6,20" in (pay_audits[-1].details or "")
    assert f"order_id={order['id']}" in (pay_audits[-1].details or "")

    fx_audits = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "fx_execution",
            AuditLog.entity_id == str(fx_id),
            AuditLog.action == "fx.realized.void_by_payment_cancel",
        )
        .all()
    )
    assert fx_audits
    det = fx_audits[-1].details or ""
    assert "eur=200.00" in det
    assert "brl=1240.00" in det or "brl=1240.0000" in det or "1240" in det
    assert "rate=6.2" in det
    assert f"order_id={order['id']}" in det


def test_fin1b_cancel_both_leaves_empty_panel(admin_client):
    c = admin_client
    _s, order = _confirmed_order(c)
    a1 = _post_advance(c, order["id"], amount="100.00", rate="6.00")
    a2 = _post_advance(c, order["id"], amount="50.00", rate="6.10")
    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    by_id = {a["payment_id"]: a for a in listing["advances"]}

    c.post(
        f"/api/orders/{order['id']}/advances/{a1['payment_id']}/cancel",
        json={"expected_version": by_id[a1["payment_id"]]["version"], "reason": "limpar a1"},
    )
    mid = c.get(f"/api/orders/{order['id']}/advances").json()
    assert mid["consolidated"]["count"] == 1

    v2 = mid["advances"][0]["version"]
    c.post(
        f"/api/orders/{order['id']}/advances/{a2['payment_id']}/cancel",
        json={"expected_version": v2, "reason": "limpar a2"},
    )
    final = c.get(f"/api/orders/{order['id']}/advances").json()
    assert final["consolidated"]["count"] == 0
    assert final["advances"] == []
    assert Decimal(final["consolidated"]["total_eur"]) == Decimal("0.00")


def test_fin1b_payments_cancel_also_voids_fx_audit(admin_client, db):
    """Mesmo caminho: cancel em /payments/{id} também audita void do FX."""
    c = admin_client
    _s, order = _confirmed_order(c)
    a1 = _post_advance(c, order["id"], amount="80.00", rate="6.00")
    pay = c.get(f"/api/payments/{a1['payment_id']}").json()
    r = c.post(
        f"/api/payments/{a1['payment_id']}/cancel",
        json={"expected_version": pay["version"], "reason_code": "PAYMENT_CANCEL_UI"},
    )
    assert r.status_code == 200, r.text

    from app.audit.models import AuditLog

    fx_audits = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "fx_execution",
            AuditLog.entity_id == str(a1["fx_execution_id"]),
            AuditLog.action == "fx.realized.void_by_payment_cancel",
        )
        .all()
    )
    assert fx_audits
