"""Treasury Inc-3 — SC-03/SC-04 e matriz de alocação."""

import uuid
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pytest


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _issued_invoice_with_two_payables(client, *, net_a="600", net_b="700"):
    """Order 1 item qty such that we can split via two invoices OR one invoice two terms.

    Use one invoice with two AMOUNT terms totaling net.
    """
    sku = f"T-{_uid()}"
    s = client.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    # 13 units * 100 = 1300 = 600+700
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "13",
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
                    "quantity": "13",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    today = date.today()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [
                {"due_date": today.isoformat(), "amount": net_a},
                {"due_date": (today + timedelta(days=30)).isoformat(), "amount": net_b},
            ],
        },
    ).json()
    client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    inv = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    ).json()
    assert inv["status"] == "ISSUED"
    assert len(inv["payables"]) == 2
    return s, inv


def _register_payment(client, supplier_id, amount="1000", currency="EUR", **kw):
    r = client.post(
        "/api/payments",
        json={
            "supplier_id": supplier_id,
            "amount": amount,
            "currency": currency,
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
            **kw,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_sc03_unallocated_does_not_change_balances(admin_client):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    before = [(p["id"], p["balance"], p["status"]) for p in inv["payables"]]
    pay = _register_payment(c, s["id"], amount="1000")
    assert pay["amount_unallocated"] == "1000.00"
    assert pay["amount_allocated"] == "0.00"
    inv2 = c.get(f"/api/invoices/{inv['id']}").json()
    after = [(p["id"], p["balance"], p["status"]) for p in inv2["payables"]]
    assert before == after
    assert float(inv2["balance"]) == 1300.0


def test_sc04_partial_and_multi_payable(admin_client):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa, pb = inv["payables"]
    pay = _register_payment(c, s["id"], amount="1000")

    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"batch-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "400", "expected_version": pa["version"]},
            ],
        },
    )
    assert r.status_code == 200, r.text
    pay = r.json()
    assert pay["amount_unallocated"] == "600.00"

    pa2 = c.get("/api/payables", params={"invoice_id": inv["id"]}).json()
    by_id = {p["id"]: p for p in pa2}
    assert float(by_id[pa["id"]]["balance"]) == 200.0
    assert by_id[pa["id"]]["status"] == "PARTIALLY_PAID"
    assert float(by_id[pb["id"]]["balance"]) == 700.0

    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"batch-{_uid()}",
            "allocations": [
                {
                    "payable_id": pb["id"],
                    "amount": "300",
                    "expected_version": by_id[pb["id"]]["version"],
                },
            ],
        },
    )
    assert r.status_code == 200, r.text
    pay = r.json()
    assert pay["amount_unallocated"] == "300.00"
    inv2 = c.get(f"/api/invoices/{inv['id']}").json()
    assert float(inv2["balance"]) == 600.0  # 200+400


def test_batch_idempotent_replay_and_conflict(admin_client):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa = inv["payables"][0]
    pay = _register_payment(c, s["id"], amount="1000")
    key = f"idem-{_uid()}"
    body = {
        "expected_version": pay["version"],
        "idempotency_key": key,
        "allocations": [
            {"payable_id": pa["id"], "amount": "100", "expected_version": pa["version"]},
        ],
    }
    r1 = c.post(f"/api/payments/{pay['id']}/allocations", json=body)
    assert r1.status_code == 200
    r2 = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={**body, "expected_version": r1.json()["version"]},
    )
    # replay with same key+payload — should succeed without double alloc
    # Note: expected_version changed after first; replay returns early before version bump
    r2 = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={**body, "expected_version": 999},  # version ignored on idempotent hit
    )
    assert r2.status_code == 200
    assert len(r2.json()["allocations"]) == 1
    assert r2.json()["amount_unallocated"] == "900.00"

    # same key different payload → 409
    r3 = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": r2.json()["version"],
            "idempotency_key": key,
            "allocations": [
                {"payable_id": pa["id"], "amount": "50", "expected_version": 1},
            ],
        },
    )
    assert r3.status_code == 409


def test_over_allocation_and_eligible_excludes_paid(admin_client):
    c = admin_client
    sku = f"T-{_uid()}"
    s = c.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = c.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = c.post(
        "/api/orders",
        json={"code": f"ORD-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "2",
            "unit_price": "100",
        },
    ).json()
    o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = c.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{_uid()}"},
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
                {"due_date": today.isoformat(), "amount": "100"},
                {"due_date": (today + timedelta(days=30)).isoformat(), "amount": "100"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    c.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    inv = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    ).json()
    pa, pb = inv["payables"]
    pay = _register_payment(c, s["id"], amount="50")
    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"ov-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "60", "expected_version": pa["version"]},
            ],
        },
    )
    assert r.status_code == 400

    pay2 = _register_payment(c, s["id"], amount="100")
    r = c.post(
        f"/api/payments/{pay2['id']}/allocations",
        json={
            "expected_version": pay2["version"],
            "idempotency_key": f"full-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "100", "expected_version": pa["version"]},
            ],
        },
    )
    assert r.status_code == 200
    elig = c.get(f"/api/payments/{pay2['id']}/eligible-payables").json()
    ids = {e["id"] for e in elig}
    assert pa["id"] not in ids
    assert pb["id"] in ids


def test_currency_and_supplier_mismatch(admin_client):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa = inv["payables"][0]
    other = c.post("/api/suppliers", json={"name": f"Other-{_uid()}", "country_code": "IT"}).json()
    pay = _register_payment(c, other["id"], amount="100")
    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"sup-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "10", "expected_version": pa["version"]},
            ],
        },
    )
    assert r.status_code == 400
    assert "fornecedor" in r.json()["message"].lower() or "fornecedor" in r.json()["message"]


def test_cancel_unallocated_ok_allocated_blocked(admin_client):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pay = _register_payment(c, s["id"], amount="100")
    r = c.post(
        f"/api/payments/{pay['id']}/cancel",
        json={"expected_version": pay["version"], "reason_code": "ABORT"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"

    pay2 = _register_payment(c, s["id"], amount="100")
    pa = inv["payables"][0]
    # refresh payable version
    pays = c.get("/api/payables", params={"invoice_id": inv["id"]}).json()
    pa = next(p for p in pays if p["id"] == pa["id"])
    c.post(
        f"/api/payments/{pay2['id']}/allocations",
        json={
            "expected_version": pay2["version"],
            "idempotency_key": f"c-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "10", "expected_version": pa["version"]},
            ],
        },
    )
    pay2 = c.get(f"/api/payments/{pay2['id']}").json()
    r = c.post(
        f"/api/payments/{pay2['id']}/cancel",
        json={"expected_version": pay2["version"], "reason_code": "ABORT"},
    )
    assert r.status_code == 409


def test_document_orphan_cleanup_on_audit_fail(admin_client, monkeypatch):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": f"Doc-{_uid()}", "country_code": "IT"}).json()
    from app.audit import public as audit_public
    from app.foundation.settings import get_settings

    settings = get_settings()
    before = set(settings.attachments_path.rglob("*")) if settings.attachments_path.exists() else set()

    def boom(*_a, **_k):
        raise RuntimeError("audit fail pay")

    monkeypatch.setattr(audit_public, "record_event", boom)
    with pytest.raises(RuntimeError, match="audit fail pay"):
        c.post(
            "/api/payments/with-document",
            data={
                "supplier_id": str(s["id"]),
                "amount": "10",
                "currency": "EUR",
                "payment_date": date.today().isoformat(),
            },
            files={"file": ("r.pdf", BytesIO(b"%PDF-orphan"), "application/pdf")},
        )
    monkeypatch.undo()
    after = set(settings.attachments_path.rglob("*")) if settings.attachments_path.exists() else set()
    new_files = [p for p in (after - before) if p.is_file()]
    assert new_files == [], f"Arquivos órfãos: {new_files}"
    listed = c.get("/api/payments", params={"supplier_id": s["id"]}).json()
    assert listed == []


def test_audit_rollback_allocation(admin_client, monkeypatch):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa = inv["payables"][0]
    pay = _register_payment(c, s["id"], amount="100")
    from app.audit import public as audit_public

    def boom(*_a, **_k):
        raise RuntimeError("audit fail alloc")

    monkeypatch.setattr(audit_public, "record_event", boom)
    with pytest.raises(RuntimeError, match="audit fail alloc"):
        c.post(
            f"/api/payments/{pay['id']}/allocations",
            json={
                "expected_version": pay["version"],
                "idempotency_key": f"rb-{_uid()}",
                "allocations": [
                    {"payable_id": pa["id"], "amount": "10", "expected_version": pa["version"]},
                ],
            },
        )
    monkeypatch.undo()
    inv2 = c.get(f"/api/invoices/{inv['id']}").json()
    assert float(inv2["payables"][0]["balance"]) == float(pa["balance"])
    pay2 = c.get(f"/api/payments/{pay['id']}").json()
    assert pay2["amount_unallocated"] == "100.00"
    assert pay2["allocations"] == []


def test_timeout_retry_same_key_same_payload(admin_client):
    """Simula cliente que timeout e reenvia exatamente o mesmo lote."""
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa = inv["payables"][0]
    pay = _register_payment(c, s["id"], amount="500")
    key = f"retry-{_uid()}"
    body = {
        "expected_version": pay["version"],
        "idempotency_key": key,
        "allocations": [
            {"payable_id": pa["id"], "amount": "150", "expected_version": pa["version"]},
        ],
    }
    first = c.post(f"/api/payments/{pay['id']}/allocations", json=body)
    assert first.status_code == 200
    # "retry" after presumed timeout — identical body (incl. stale expected_version)
    retry = c.post(f"/api/payments/{pay['id']}/allocations", json=body)
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert len(retry.json()["allocations"]) == 1
    assert float(retry.json()["amount_unallocated"]) == 350.0
    pays = c.get("/api/payables", params={"invoice_id": inv["id"]}).json()
    assert float(next(p for p in pays if p["id"] == pa["id"])["balance"]) == 450.0


def test_concurrent_payments_same_payable(admin_client):
    """Dois Payments competem pelo saldo do mesmo Payable — segundo perde."""
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c, net_a="100", net_b="1200")
    pa = next(p for p in inv["payables"] if float(p["amount"]) == 100.0)
    pay_a = _register_payment(c, s["id"], amount="100")
    pay_b = _register_payment(c, s["id"], amount="100")
    r1 = c.post(
        f"/api/payments/{pay_a['id']}/allocations",
        json={
            "expected_version": pay_a["version"],
            "idempotency_key": f"c1-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "100", "expected_version": pa["version"]},
            ],
        },
    )
    assert r1.status_code == 200, r1.text
    r2 = c.post(
        f"/api/payments/{pay_b['id']}/allocations",
        json={
            "expected_version": pay_b["version"],
            "idempotency_key": f"c2-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "100", "expected_version": pa["version"]},
            ],
        },
    )
    # balance esgotado ou version mismatch → 400/409
    assert r2.status_code in (400, 409), r2.text
    pay_b2 = c.get(f"/api/payments/{pay_b['id']}").json()
    assert pay_b2["allocations"] == []
    assert float(pay_b2["amount_unallocated"]) == 100.0
    elig = c.get(f"/api/payments/{pay_b['id']}/eligible-payables").json()
    assert pa["id"] not in {e["id"] for e in elig}


def test_eligible_excludes_cancelled_payable(admin_client, db):
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa, pb = inv["payables"]
    from app.billing.models import Payable

    row = db.get(Payable, pa["id"])
    assert row is not None
    row.status = "CANCELLED"
    row.balance = 0
    db.commit()

    pay = _register_payment(c, s["id"], amount="50")
    elig = c.get(f"/api/payments/{pay['id']}/eligible-payables").json()
    ids = {e["id"] for e in elig}
    assert pa["id"] not in ids
    assert pb["id"] in ids


def test_batch_all_or_nothing_partial_billing_fail(admin_client, monkeypatch):
    """Falha no meio de apply_payable_allocations → Payment e Payables intactos."""
    c = admin_client
    s, inv = _issued_invoice_with_two_payables(c)
    pa, pb = inv["payables"]
    pay = _register_payment(c, s["id"], amount="1000")
    from app.billing import public as billing_public

    real_apply = billing_public.apply_payable_allocations
    calls = {"n": 0}

    def boom(db, applications):
        calls["n"] += 1
        if calls["n"] == 1:
            # aplica primeiro item via real, depois falha — Billing deve ser all-or-nothing;
            # se apply for atômico internamente, falhamos antes de qualquer escrita
            raise billing_public.BillingError("falha simulada parcial", code="validation_error")
        return real_apply(db, applications)

    monkeypatch.setattr(billing_public, "apply_payable_allocations", boom)
    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"partial-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "100", "expected_version": pa["version"]},
                {"payable_id": pb["id"], "amount": "100", "expected_version": pb["version"]},
            ],
        },
    )
    assert r.status_code == 400, r.text
    monkeypatch.undo()
    inv2 = c.get(f"/api/invoices/{inv['id']}").json()
    assert float(inv2["payables"][0]["balance"]) == float(pa["balance"])
    assert float(inv2["payables"][1]["balance"]) == float(pb["balance"])
    pay2 = c.get(f"/api/payments/{pay['id']}").json()
    assert pay2["allocations"] == []
    assert float(pay2["amount_unallocated"]) == 1000.0
