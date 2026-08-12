"""Inc-5 Reporting — AP queue + order cockpit."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import pytest


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _issued_two_payables(client, *, amount1="400", amount2="600"):
    sku = f"R-{_uid()}"
    s = client.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"UX0-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
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
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = client.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{_uid()}"},
    ).json()
    item = inv["items"][0]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "10",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    d1 = date.today() - timedelta(days=3)
    d2 = date.today() + timedelta(days=10)
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [
                {"due_date": d1.isoformat(), "amount": amount1},
                {"due_date": d2.isoformat(), "amount": amount2},
            ],
        },
    )
    assert inv.status_code == 200, inv.text
    inv = inv.json()
    client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    issued = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert issued.status_code == 200, issued.text
    inv = issued.json()
    return s, o, inv


def test_ap_queue_sort_overdue_first_and_kpis(admin_client):
    c = admin_client
    _, order, inv = _issued_two_payables(c)
    r = c.get("/api/reporting/ap-queue", params={"order_id": order["id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 2
    assert body["kpis"]["overdue_count"] >= 1
    assert "kpis_by_currency" in body["kpis"]
    assert isinstance(body["kpis"]["kpis_by_currency"], list)
    assert "open_balance" not in body["kpis"]
    dates = [row["due_date"] for row in body["items"]]
    assert dates == sorted(dates) or body["items"][0]["days_overdue"] >= body["items"][-1]["days_overdue"]
    # overdue first
    assert body["items"][0]["days_overdue"] > 0
    assert "unallocated_candidates" in body
    assert body["note"]


def test_ap_queue_kpis_never_mix_currencies(admin_client, db):
    """EUR + BRL must not produce a single EUR total (H-J5C-1 / H-CLOSE-3)."""
    from app.billing.models import Payable

    c = admin_client
    _, _order, _inv = _issued_two_payables(c)

    brl_before = c.get("/api/reporting/ap-queue", params={"currency": "BRL", "limit": 200}).json()
    brl_before_open = Decimal("0")
    if brl_before["kpis"]["kpis_by_currency"]:
        brl_before_open = Decimal(brl_before["kpis"]["kpis_by_currency"][0]["open_balance"])

    # inject BRL customs-like payable without Invoice
    p = Payable(
        invoice_id=None,
        payment_term_id=None,
        sequence=1,
        due_date=date.today(),
        amount=Decimal("1500.00"),
        balance=Decimal("1500.00"),
        currency="BRL",
        status="OPEN",
        source_type="CUSTOMS_FUNDING",
        source_id=999001,
        payee_display_name="Bechtrans KPI",
        version=1,
    )
    db.add(p)
    db.commit()

    all_q = c.get("/api/reporting/ap-queue", params={"pending": "OPEN_BALANCE", "limit": 200})
    assert all_q.status_code == 200, all_q.text
    kpis = all_q.json()["kpis"]
    assert "open_balance" not in kpis
    by_cur = {e["currency"]: e for e in kpis["kpis_by_currency"]}
    assert "EUR" in by_cur and "BRL" in by_cur
    assert kpis["mixed_currency"] is True
    assert Decimal(by_cur["BRL"]["open_balance"]) == brl_before_open + Decimal("1500.00")
    # never EUR 1900-style mix of ~400 EUR + 1500 BRL into one EUR figure
    assert by_cur["EUR"]["open_balance"] != "1900.00"
    assert Decimal(by_cur["EUR"]["open_balance"]) != Decimal(by_cur["EUR"]["open_balance"]) + Decimal(
        "1500.00"
    )

    only_eur = c.get("/api/reporting/ap-queue", params={"currency": "EUR", "limit": 200}).json()
    assert all(row["currency"] == "EUR" for row in only_eur["items"])
    assert only_eur["kpis"]["mixed_currency"] is False
    assert len(only_eur["kpis"]["kpis_by_currency"]) == 1
    assert only_eur["kpis"]["kpis_by_currency"][0]["currency"] == "EUR"

    only_brl = c.get("/api/reporting/ap-queue", params={"currency": "BRL", "limit": 200}).json()
    assert all(row["currency"] == "BRL" for row in only_brl["items"])
    assert Decimal(only_brl["kpis"]["kpis_by_currency"][0]["open_balance"]) == brl_before_open + Decimal(
        "1500.00"
    )
    assert "EUR" not in {e["currency"] for e in only_brl["kpis"]["kpis_by_currency"]}


def test_ap_queue_rbac_requires_reporting_read(client, db, admin_client):
    import json
    from app.identity.models import Role, User
    from app.identity.security import hash_password

    role = Role(
        name=f"norep-{_uid()}",
        description="no reporting",
        permissions_json=json.dumps(["billing:read"]),
    )
    db.add(role)
    db.flush()
    email = f"norep-{_uid()}@epic.com.br"
    db.add(
        User(
            email=email,
            name="NoRep",
            password_hash=hash_password("test123"),
            role_id=role.id,
            is_active=True,
        )
    )
    db.commit()
    assert client.post("/api/auth/login", json={"email": email, "password": "test123"}).status_code == 200
    r = client.get("/api/reporting/ap-queue")
    assert r.status_code == 403


def test_order_summary_paid_via_allocations_only(admin_client):
    c = admin_client
    s, order, inv = _issued_two_payables(c, amount1="400", amount2="600")
    payable = inv["payables"][0]
    # unallocated payment — must NOT count as paid
    pay = c.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "amount": "50",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST",
        },
    ).json()
    r = c.get(f"/api/orders/{order['id']}/summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kpis"]["paid"] == "0.00"
    assert any(x.get("relation") is False for x in body["treasury"]["unallocated_candidates"])

    # allocate 50 → paid becomes 50
    alloc = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"sum-{_uid()}",
            "allocations": [
                {"payable_id": payable["id"], "amount": "50", "expected_version": payable["version"]},
            ],
        },
    )
    assert alloc.status_code == 200, alloc.text
    body2 = c.get(f"/api/orders/{order['id']}/summary").json()
    assert body2["kpis"]["paid"] == "50.00"
    assert "documents" in body2 and body2["documents"]["truncated"] is True
    assert "audit" in body2 and body2["audit"]["truncated"] is True


def test_ap_queue_volume_no_n1_smoke(admin_client):
    """Cria várias obrigações e garante resposta paginada + KPI total > page."""
    c = admin_client
    last_order = None
    for _ in range(3):
        _, last_order, _ = _issued_two_payables(c)
    r = c.get("/api/reporting/ap-queue", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 2
    assert body["total"] >= 6
    assert body["kpis"]["total_count"] == body["total"]


def test_ap_queue_supplier_resolved_via_bulk_once(admin_client, monkeypatch):
    """Vários payables do mesmo supplier → 1× get_suppliers_bulk; get_supplier proibido."""
    c = admin_client
    s, order, _ = _issued_two_payables(c, amount1="400", amount2="600")
    # mais payables do mesmo fornecedor
    for _ in range(4):
        _issued_two_payables_same_supplier(c, supplier_id=s["id"])

    calls = {"bulk": 0}

    import app.reporting.queries as rq
    from app.catalog import public as catalog_public

    real_bulk = catalog_public.get_suppliers_bulk

    def counting_bulk(db, ids):
        calls["bulk"] += 1
        return real_bulk(db, ids)

    def forbid_single(*_a, **_k):
        raise AssertionError("ap_queue must not call get_supplier (use get_suppliers_bulk)")

    monkeypatch.setattr(rq.catalog_public, "get_suppliers_bulk", counting_bulk)
    monkeypatch.setattr(rq.catalog_public, "get_supplier", forbid_single)

    r = c.get("/api/reporting/ap-queue", params={"supplier_id": s["id"], "limit": 50})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 10
    assert calls["bulk"] == 1
    names = {row["supplier_name"] for row in body["items"]}
    assert names == {s["name"]}
    assert all(row.get("supplier_resolved") is True for row in body["items"])


def test_ap_queue_missing_supplier_explicit_null(db, monkeypatch):
    """Supplier ausente no bulk → supplier_name null (não inventa '#id')."""
    from datetime import date

    import app.reporting.queries as rq

    core = {
        "items": [
            {
                "id": 9001,
                "supplier_id": 999999,
                "invoice_id": 1,
                "order_id": 1,
                "invoice_number": "X",
                "currency": "EUR",
                "amount": "10.00",
                "allocated": "0.00",
                "balance": "10.00",
                "status": "OPEN",
                "due_date": date.today().isoformat(),
                "days_overdue": 0,
            }
        ],
        "total": 1,
        "limit": 50,
        "offset": 0,
        "kpis": {
            "mixed_currency": False,
            "total_count": 1,
            "overdue_count": 0,
            "kpis_by_currency": [
                {
                    "currency": "EUR",
                    "total_count": 1,
                    "open_balance": "10.00",
                    "overdue_balance": "0.00",
                    "overdue_count": 0,
                    "due_today_balance": "10.00",
                    "next_7d_balance": "0.00",
                }
            ],
        },
    }

    monkeypatch.setattr(rq.billing_public, "payables_queue", lambda *a, **k: core)
    monkeypatch.setattr(rq.catalog_public, "get_suppliers_bulk", lambda db, ids: {})
    monkeypatch.setattr(rq.treasury_public.fx, "get_current_plans_bulk", lambda db, ids: {})
    monkeypatch.setattr(rq.treasury_public.fx, "get_latest_quote", lambda *a, **k: None)
    monkeypatch.setattr(rq, "_unallocated_candidates", lambda db, rows: [])

    out = rq.ap_queue(db, limit=50, offset=0)
    row = out["items"][0]
    assert row["supplier_name"] is None
    assert row["supplier_resolved"] is False
    assert row["supplier_name"] != "#999999"


def _issued_two_payables_same_supplier(client, *, supplier_id: int):
    sku = f"R-{_uid()}"
    p = client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"UX0-{_uid()}", "supplier_id": supplier_id, "currency": "EUR"},
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
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = client.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{_uid()}"},
    ).json()
    item = inv["items"][0]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "10",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    d1 = date.today() - timedelta(days=1)
    d2 = date.today() + timedelta(days=14)
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [
                {"due_date": d1.isoformat(), "amount": "400"},
                {"due_date": d2.isoformat(), "amount": "600"},
            ],
        },
    )
    assert inv.status_code == 200, inv.text
    inv = inv.json()
    client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    issued = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert issued.status_code == 200, issued.text
    return issued.json()


def test_orders_list_enrichment_absence_is_null(admin_client):
    """GET /api/reporting/orders-list — sem fatura: financeiros None (não zero)."""
    c = admin_client
    sku = f"OL-{_uid()}"
    s = c.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = c.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = c.post(
        "/api/orders",
        json={"code": f"OL-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "2",
            "unit_price": "10",
        },
    ).json()
    r = c.get("/api/reporting/orders-list")
    assert r.status_code == 200, r.text
    row = next(x for x in r.json() if x["id"] == o["id"])
    assert row["supplier_name"] == s["name"]
    assert row["commercial_total"] is not None
    assert row["invoiced_amount"] is None
    assert row["open_balance"] is None
    assert row["next_due_date"] is None
    assert row["invoiced_amount"] != "0.00"
    assert row["open_balance"] != "0.00"


def test_orders_list_enrichment_after_issue(admin_client):
    c = admin_client
    s, o, inv = _issued_two_payables(c, amount1="400", amount2="600")
    r = c.get("/api/reporting/orders-list")
    assert r.status_code == 200, r.text
    row = next(x for x in r.json() if x["id"] == o["id"])
    assert row["supplier_name"] == s["name"]
    assert row["invoiced_amount"] == "1000.00"
    assert row["open_balance"] == "1000.00"
    assert row["next_due_date"] is not None

    inv_list = c.get("/api/invoices")
    assert inv_list.status_code == 200, inv_list.text
    inv_row = next(x for x in inv_list.json() if x["id"] == inv["id"])
    assert inv_row["supplier_name"] == s["name"]
    assert inv_row["payable_count"] == 2

def test_invoice_list_and_ap_queue_order_code(admin_client):
    c = admin_client
    s, inv, o = None, None, None
    s = c.post("/api/suppliers", json={"name": "Heroes OrderCode", "country_code": "IT"}).json()
    p = c.post("/api/products", json={"sku": "OC-1", "description": "Item"}).json()
    o = c.post("/api/orders", json={"code": "OC-ORDER-1", "supplier_id": s["id"], "currency": "EUR"}).json()
    o = c.post(f"/api/orders/{o['id']}/items", json={"expected_version": o["version"], "product_id": p["id"], "quantity": "1", "unit_price": "10"}).json()
    o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = c.post(f"/api/orders/{o['id']}/invoices", json={"invoice_number": "OC-INV-1"}).json()
    item = inv["items"][0]
    inv = c.put(f"/api/invoices/{inv['id']}/items", json={"expected_version": inv["version"], "items": [{"order_item_id": item["order_item_id"], "quantity": "1", "unit_price_gross": "10", "discount_type": "NONE"}]}).json()
    from datetime import date
    from io import BytesIO
    inv = c.put(f"/api/invoices/{inv['id']}/terms", json={"expected_version": inv["version"], "mode": "amount", "terms": [{"due_date": date.today().isoformat(), "amount": "10"}]}).json()
    c.post("/api/documents", files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")}, data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"})
    inv = c.post(f"/api/invoices/{inv['id']}/issue", json={"expected_version": inv["version"]}).json()
    listed = c.get("/api/invoices").json()
    row = next(x for x in listed if x["id"] == inv["id"])
    assert row["order_code"] == "OC-ORDER-1"
    ap = c.get("/api/reporting/ap-queue", params={"order_id": o["id"]}).json()
    assert ap["items"]
    assert ap["items"][0]["order_code"] == "OC-ORDER-1"


# --- FIN-1C-FIX-1 ---


def _confirmed_order_eur(client, *, supplier_id: int | None = None):
    if supplier_id is None:
        s = client.post(
            "/api/suppliers", json={"name": f"Fix1-{_uid()}", "country_code": "IT"}
        ).json()
        supplier_id = s["id"]
    else:
        s = {"id": supplier_id}
    p = client.post(
        "/api/products", json={"sku": f"FIX1-{_uid()}", "description": "Item"}
    ).json()
    o = client.post(
        "/api/orders",
        json={
            "code": f"ORD-FIX1-{_uid()}",
            "supplier_id": supplier_id,
            "currency": "EUR",
        },
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


def test_fin1c_f1_cockpit_payments_order_scoped(admin_client):
    """F1: lista principal do cockpit só com order_id; candidatos podem ser do outro pedido."""
    c = admin_client
    s, order_a = _confirmed_order_eur(c)
    _, order_b = _confirmed_order_eur(c, supplier_id=s["id"])

    adv_a = c.post(
        f"/api/orders/{order_a['id']}/advances",
        json={
            "amount": "100.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "5.50",
            "register_without_fx_document": True,
            "reason_code": "TEST",
        },
    )
    assert adv_a.status_code == 200, adv_a.text
    pay_a = adv_a.json()["payment_id"]

    adv_b = c.post(
        f"/api/orders/{order_b['id']}/advances",
        json={
            "amount": "999.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "5.50",
            "register_without_fx_document": True,
            "reason_code": "TEST",
        },
    )
    assert adv_b.status_code == 200, adv_b.text
    pay_b = adv_b.json()["payment_id"]

    summary = c.get(f"/api/orders/{order_a['id']}/summary").json()
    main_ids = {p["id"] for p in summary["treasury"]["payments"]}
    assert pay_a in main_ids
    assert pay_b not in main_ids

    cand_ids = {x["payment_id"] for x in summary["treasury"]["unallocated_candidates"]}
    assert pay_a in cand_ids
    assert pay_b in cand_ids
    assert any(
        x["payment_id"] == pay_b and x.get("relation") is False
        for x in summary["treasury"]["unallocated_candidates"]
    )


def test_fin1c_f2_cancelled_residual_null(admin_client):
    """F2: CANCELLED na lista do pedido com status e amount_unallocated null."""
    c = admin_client
    _s, order = _confirmed_order_eur(c)
    adv = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "200.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "6.00",
            "register_without_fx_document": True,
            "reason_code": "TEST",
        },
    ).json()
    payment_id = adv["payment_id"]
    listing = c.get(f"/api/orders/{order['id']}/advances").json()
    version = listing["advances"][0]["version"]
    cancel = c.post(
        f"/api/orders/{order['id']}/advances/{payment_id}/cancel",
        json={"expected_version": version, "reason": "teste F2"},
    )
    assert cancel.status_code == 200, cancel.text

    summary = c.get(f"/api/orders/{order['id']}/summary").json()
    row = next(p for p in summary["treasury"]["payments"] if p["id"] == payment_id)
    assert row["status"] == "CANCELLED"
    assert row["amount_unallocated"] is None
    assert Decimal(summary["kpis"]["advanced_credit"]) == Decimal("0.00")


def test_fin1c_f3_advanced_credit_kpi(admin_client):
    """F3: Pago (alocado) vs Adiantado (crédito) honestos."""
    c = admin_client
    _s, order = _confirmed_order_eur(c)
    before = c.get(f"/api/orders/{order['id']}/summary").json()
    assert before["kpis"]["paid"] == "0.00"
    assert before["kpis"]["advanced_credit"] == "0.00"

    adv = c.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "25000.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "5.91",
            "register_without_fx_document": True,
            "reason_code": "TEST",
        },
    )
    assert adv.status_code == 200, adv.text

    after = c.get(f"/api/orders/{order['id']}/summary").json()
    assert after["kpis"]["paid"] == "0.00"
    assert after["kpis"]["advanced_credit"] == "25000.00"
    assert after["treasury"]["advanced_credit"] == "25000.00"
    # Sem Fattura: Faturado/Saldo continuam 0 (honestos para obrigações)
    assert after["kpis"]["invoiced"] == "0.00"
    assert after["kpis"]["balance"] == "0.00"
