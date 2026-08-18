"""J4-FIN-CICLO — auto-link FX no adiantamento + custo BRL (soma dos câmbios)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from app.treasury.fx_money import weighted_rate


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _attach_doc(client, invoice_id: int) -> None:
    r = client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF-1.4 ciclo"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(invoice_id), "role": "official"},
    )
    assert r.status_code == 200, r.text


def _confirmed_order(client, *, qty: str, unit_price: str):
    s = client.post(
        "/api/suppliers",
        json={"name": f"TESTE-CICLO-{_uid()}", "country_code": "IT"},
    ).json()
    p = client.post(
        "/api/products",
        json={"sku": f"CICLO-{_uid()}", "description": "Item ciclo"},
    ).json()
    o = client.post(
        "/api/orders",
        json={
            "code": f"TESTE-CICLO-{_uid()}",
            "supplier_id": s["id"],
            "currency": "EUR",
            "notes": "Cenário de validação — não é compra real",
        },
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": qty,
            "unit_price": unit_price,
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    return s, o


def _issue_invoice(client, order, *, number: str, qty: str, unit_price: str, terms: list[dict]):
    inv = client.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": number},
    ).json()
    item = inv["items"][0]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": qty,
                    "unit_price_gross": unit_price,
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={"expected_version": inv["version"], "mode": "AMOUNT", "terms": terms},
    ).json()
    _attach_doc(client, inv["id"])
    inv = client.get(f"/api/invoices/{inv['id']}").json()
    issued = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert issued.status_code == 200, issued.text
    return issued.json()


def _advance(client, order_id: int, *, amount: str, rate: str, key: str):
    today = date.today()
    r = client.post(
        f"/api/orders/{order_id}/advances",
        json={
            "amount": amount,
            "rate": rate,
            "payment_date": today.isoformat(),
            "execution_date": (today - timedelta(days=1)).isoformat(),
            "register_without_fx_document": True,
            "reason_code": "TEST_CICLO",
            "idempotency_key": key,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _allocate(client, payment_id: int, version: int, payable_id: int, payable_version: int, amount: str):
    pay = client.get(f"/api/payments/{payment_id}").json()
    r = client.post(
        f"/api/payments/{payment_id}/allocations",
        json={
            "expected_version": version if version is not None else pay["version"],
            "idempotency_key": f"ciclo-{_uid()}",
            "allocations": [
                {
                    "payable_id": payable_id,
                    "amount": amount,
                    "expected_version": payable_version,
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_ciclo_advance_allocate_auto_links_cost_brl(admin_client):
    """120k @ 5.80 aplicado 36k+84k → BRL 208800 + 487200; cockpit = soma, não P&L."""
    c = admin_client
    _s, order = _confirmed_order(c, qty="2000", unit_price="60")
    due = date.today() + timedelta(days=30)
    inv = _issue_invoice(
        c,
        order,
        number=f"T001-{_uid()}",
        qty="2000",
        unit_price="60",
        terms=[
            {"due_date": due.isoformat(), "amount": "36000.00"},
            {"due_date": (due + timedelta(days=60)).isoformat(), "amount": "84000.00"},
        ],
    )
    pays = sorted(inv["payables"], key=lambda p: Decimal(p["amount"]))
    p36, p84 = pays[0], pays[1]
    assert Decimal(p36["amount"]) == Decimal("36000.00")
    assert Decimal(p84["amount"]) == Decimal("84000.00")

    adv = _advance(c, order["id"], amount="120000.00", rate="5.80", key=f"adv-{_uid()}")
    payment_id = adv["payment_id"]
    pay = c.get(f"/api/payments/{payment_id}").json()

    summary0 = c.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary0["kpis"]["cost_brl"]) == Decimal("696000.00")
    assert "fx_realized" not in summary0["kpis"]
    assert Decimal(summary0["treasury"]["cost_brl"]) == Decimal("696000.00")

    pay = _allocate(c, payment_id, pay["version"], p36["id"], p36["version"], "36000.00")
    pay = _allocate(c, payment_id, pay["version"], p84["id"], p84["version"], "84000.00")

    v36 = c.get(f"/api/payables/{p36['id']}/fx-view").json()
    v84 = c.get(f"/api/payables/{p84['id']}/fx-view").json()
    assert Decimal(v36["cost_brl"]) == Decimal("208800.00")
    assert Decimal(v84["cost_brl"]) == Decimal("487200.00")
    assert v36["realized_brl"] is None
    assert v84["realized_brl"] is None

    summary = c.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary["kpis"]["cost_brl"]) == Decimal("696000.00")
    assert Decimal(summary["kpis"]["paid"]) == Decimal("120000.00")
    assert Decimal(summary["kpis"]["advanced_credit"]) == Decimal("0.00")
    assert "fx_realized" not in summary["kpis"]


def test_ciclo_two_advances_weighted_avg_before_allocate(admin_client):
    """120k@5.80 + 60k@6.15 = BRL 1.065.000; ponderado 5.916667 (não média simples 5.975)."""
    c = admin_client
    _s, order = _confirmed_order(c, qty="10000", unit_price="60")
    _advance(c, order["id"], amount="120000.00", rate="5.80", key=f"a1-{_uid()}")
    _advance(c, order["id"], amount="60000.00", rate="6.15", key=f"a2-{_uid()}")

    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    assert Decimal(listing["consolidated"]["total_eur"]) == Decimal("180000.00")
    assert Decimal(listing["consolidated"]["total_brl"]) == Decimal("1065000.00")
    expected = weighted_rate(Decimal("180000"), Decimal("1065000"))
    assert Decimal(listing["consolidated"]["weighted_avg_rate"]) == expected
    assert expected == Decimal("5.916667")

    summary = c.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary["kpis"]["cost_brl"]) == Decimal("1065000.00")
    assert Decimal(summary["kpis"]["advanced_credit"]) == Decimal("180000.00")
    assert Decimal(summary["kpis"]["paid"]) == Decimal("0.00")
    assert summary["fx"]["weighted_avg_rate"] == "5.916667"


def test_ciclo_credit_plus_remainder_cost_sums(admin_client):
    """Crédito 60k@6.15 + saldo 30k@6.20 na mesma obrigação = 555000, não média × EUR."""
    c = admin_client
    s, order = _confirmed_order(c, qty="1500", unit_price="60")
    due = date.today() + timedelta(days=15)
    inv = _issue_invoice(
        c,
        order,
        number=f"T002-{_uid()}",
        qty="1500",
        unit_price="60",
        terms=[{"due_date": due.isoformat(), "amount": "90000.00"}],
    )
    payable = inv["payables"][0]
    adv = _advance(c, order["id"], amount="60000.00", rate="6.15", key=f"cr-{_uid()}")
    pay = c.get(f"/api/payments/{adv['payment_id']}").json()
    pay = _allocate(c, adv["payment_id"], pay["version"], payable["id"], payable["version"], "60000.00")

    payable = c.get(f"/api/payables/{payable['id']}").json()
    rem = c.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "order_id": order["id"],
            "amount": "30000.00",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_CICLO_REM",
        },
    )
    assert rem.status_code == 200, rem.text
    rem = rem.json()
    rem = _allocate(c, rem["id"], rem["version"], payable["id"], payable["version"], "30000.00")
    alloc_id = rem["allocations"][-1]["id"]

    ex = c.post(
        f"/api/payments/{rem['id']}/fx-executions",
        json={
            "foreign_amount": "30000.00",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    )
    assert ex.status_code == 200, ex.text
    link = c.post(
        "/api/fx/execution-allocations",
        json={"fx_execution_id": ex.json()["id"], "payment_allocation_id": alloc_id},
    )
    assert link.status_code == 200, link.text

    view = c.get(f"/api/payables/{payable['id']}/fx-view").json()
    assert Decimal(view["cost_brl"]) == Decimal("555000.00")
    summary = c.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary["kpis"]["cost_brl"]) == Decimal("555000.00")
    assert Decimal(summary["kpis"]["paid"]) == Decimal("90000.00")

    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    assert Decimal(listing["consolidated"]["total_eur"]) == Decimal("60000.00")
    assert Decimal(listing["consolidated"]["total_brl"]) == Decimal("369000.00")
    assert listing["consolidated"]["count"] == 1
    assert listing["advances"][0]["purpose"] == "ADVANCE"
    assert listing["advances"][0]["payment_id"] == adv["payment_id"]
    assert len(listing["settlements"]) == 1
    assert listing["settlements"][0]["purpose"] == "SETTLEMENT"
    assert listing["settlements"][0]["payment_id"] == rem["id"]
    assert Decimal(listing["settlements"][0]["amount"]) == Decimal("30000.00")


def test_ciclo_allocate_then_fx_does_not_autolink(admin_client):
    """Saldo: alocar sem câmbio não cria link; o fluxo explícito permanece."""
    c = admin_client
    s, order = _confirmed_order(c, qty="10", unit_price="100")
    due = date.today()
    inv = _issue_invoice(
        c,
        order,
        number=f"TREM-{_uid()}",
        qty="10",
        unit_price="100",
        terms=[{"due_date": due.isoformat(), "amount": "1000.00"}],
    )
    payable = inv["payables"][0]
    rem = c.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "order_id": order["id"],
            "amount": "400.00",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_CICLO_NOFX",
        },
    ).json()
    rem = _allocate(c, rem["id"], rem["version"], payable["id"], payable["version"], "400.00")
    view = c.get(f"/api/payables/{payable['id']}/fx-view").json()
    assert Decimal(view["cost_brl"]) == Decimal("0.00")
    assert view["realized_brl"] is None
    alloc_id = rem["allocations"][0]["id"]
    ex = c.post(
        f"/api/payments/{rem['id']}/fx-executions",
        json={
            "foreign_amount": "400.00",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    ).json()
    view2 = c.get(f"/api/payables/{payable['id']}/fx-view").json()
    assert Decimal(view2["cost_brl"]) == Decimal("0.00"), "register_execution não auto-liga"
    r = c.post(
        "/api/fx/execution-allocations",
        json={"fx_execution_id": ex["id"], "payment_allocation_id": alloc_id},
    )
    assert r.status_code == 200, r.text
    view3 = c.get(f"/api/payables/{payable['id']}/fx-view").json()
    assert Decimal(view3["cost_brl"]) == Decimal("2480.00")


def test_ciclo_cancel_advance_rejects_settlement(admin_client):
    """Saldo com order_id não se cancela pelo endpoint de adiantamento."""
    c = admin_client
    s, order = _confirmed_order(c, qty="10", unit_price="100")
    rem = c.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "order_id": order["id"],
            "amount": "100.00",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_CICLO_SETTLE",
        },
    )
    assert rem.status_code == 200, rem.text
    rem = rem.json()
    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    assert listing["advances"] == []
    assert listing["consolidated"]["count"] == 0
    assert listing["settlements"][0]["payment_id"] == rem["id"]
    assert rem["purpose"] == "SETTLEMENT"
    bad = c.post(
        f"/api/orders/{order['id']}/advances/{rem['id']}/cancel",
        json={"expected_version": rem["version"], "reason": "não é adiantamento"},
    )
    assert bad.status_code == 400, bad.text
    assert rem["status"] == "REGISTERED"
    still = c.get(f"/api/payments/{rem['id']}").json()
    assert still["status"] == "REGISTERED"
