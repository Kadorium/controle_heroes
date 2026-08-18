"""FIN-4 — cronograma de pagamento no pedido (planejamento Orders)."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

from app.billing.models import Payable
from app.treasury.models import Payment


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _supplier(client) -> int:
    r = client.post(
        "/api/suppliers",
        json={"name": f"F4 Sup {_uid()}", "country_code": "IT"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _product(client) -> dict:
    r = client.post(
        "/api/products",
        json={"sku": f"F4-{_uid()}", "description": "sku fin4", "is_active": True},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _draft_order(client, *, priced: bool = True, qty: str = "10", price: str | None = "50"):
    sid = _supplier(client)
    prod = _product(client)
    r = client.post(
        "/api/orders",
        json={"code": f"F4-{_uid()}", "supplier_id": sid, "currency": "EUR"},
    )
    assert r.status_code == 201, r.text
    order = r.json()
    body = {
        "expected_version": order["version"],
        "product_id": prod["id"],
        "quantity": qty,
    }
    if priced:
        body["unit_price"] = price
    r = client.post(f"/api/orders/{order['id']}/items", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _put_schedule(client, order, *, mode, lines, reason_code=None):
    payload = {
        "expected_version": order["version"],
        "mode": mode,
        "lines": lines,
    }
    if reason_code is not None:
        payload["reason_code"] = reason_code
    return client.put(f"/api/orders/{order['id']}/payment-schedule", json=payload)


def test_empty_schedule_default(admin_client):
    order = _draft_order(admin_client)
    r = admin_client.get(f"/api/orders/{order['id']}/payment-schedule")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lines"] == []
    assert body["mode"] is None
    assert body["coherence"] is None
    assert body["delta"] is None
    assert body["commercial_total"] == "500.0000"


def test_percent_unpriced_derived_null_not_zero(admin_client):
    order = _draft_order(admin_client, priced=False)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[
            {"condition_text": "bonifico anticipato", "percent": "50"},
            {"condition_text": "saldo 90 GG DFFM", "percent": "50"},
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "PERCENT"
    assert body["commercial_total"] is None
    assert body["amount_sum"] is None
    assert body["delta"] is None
    assert body["coherence"] == "unverifiable"
    assert all(ln["derived_amount"] is None for ln in body["lines"])
    assert sum(Decimal(ln["percent"]) for ln in body["lines"]) == Decimal("100")


def test_reject_line_without_when(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"percent": "100"}],
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "schedule_when_required"


def test_due_date_or_condition_ok(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[
            {"due_date": "2026-09-01", "condition_text": "na confirmacao", "percent": "40"},
            {"due_date": "2026-12-01", "percent": "60"},
        ],
    )
    assert r.status_code == 200, r.text
    assert r.json()["lines"][0]["condition_text"] == "na confirmacao"
    assert r.json()["lines"][1]["due_date"] == "2026-12-01"


def test_percent_must_sum_100(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "a", "percent": "40"}],
    )
    assert r.status_code == 400, r.text


def test_amount_draft_may_diverge(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "anticipo", "amount": "100.00"}],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["coherence"] == "divergent"
    assert Decimal(body["delta"]) == Decimal("-400.00")
    assert body["commercial_total"] == "500.0000"


def test_item_change_does_not_mutate_schedule(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "anticipo", "amount": "500.00"}],
    )
    assert r.status_code == 200, r.text
    sched = r.json()
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    item_id = order["items"][0]["id"]
    r = admin_client.patch(
        f"/api/orders/{order['id']}/items/{item_id}",
        json={"expected_version": order["version"], "quantity": "20"},
    )
    assert r.status_code == 200, r.text
    after = admin_client.get(f"/api/orders/{order['id']}/payment-schedule").json()
    assert after["lines"][0]["amount"] == sched["lines"][0]["amount"]
    assert after["coherence"] == "divergent"


def test_confirm_blocks_divergent_amount_when_total_known(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "anticipo", "amount": "100.00"}],
    )
    assert r.status_code == 200, r.text
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "schedule_amount_mismatch"


def test_confirm_allows_amount_when_total_null(admin_client):
    order = _draft_order(admin_client, priced=False)
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "anticipo", "amount": "100.00"}],
    )
    assert r.status_code == 200, r.text
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    sched = admin_client.get(f"/api/orders/{order['id']}/payment-schedule").json()
    assert sched["coherence"] == "unverifiable"
    assert sched["delta"] is None


def test_confirmed_edit_requires_reason_and_audits(admin_client, db):
    from app.audit import public as audit_public

    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[
            {"condition_text": "anticipato", "percent": "50"},
            {"condition_text": "saldo", "percent": "50"},
        ],
    )
    assert r.status_code == 200, r.text
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "100% antecipado", "percent": "100"}],
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "reason_required"
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "100% antecipado", "percent": "100"}],
        reason_code="COMMERCIAL_TERMS_UPDATE",
    )
    assert r.status_code == 200, r.text
    events = audit_public.history_by_entity(db, "order", str(order["id"]), limit=20)
    sched_ev = next(e for e in events if e.action == "set_payment_schedule" and e.reason_code == "COMMERCIAL_TERMS_UPDATE")
    details = json.loads(sched_ev.details or "{}")
    assert details["before"]
    assert Decimal(details["after"][0]["percent"]) == Decimal("100")
    assert len(details["before"]) == 2


def test_cancelled_blocks_schedule(admin_client):
    order = _draft_order(admin_client)
    r = admin_client.post(
        f"/api/orders/{order['id']}/cancel",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "x", "percent": "100"}],
    )
    assert r.status_code == 409, r.text


def test_stale_version_409(admin_client):
    order = _draft_order(admin_client)
    stale = dict(order)
    stale["version"] = order["version"]
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "a", "percent": "100"}],
    )
    assert r.status_code == 200, r.text
    r = _put_schedule(
        admin_client,
        stale,
        mode="PERCENT",
        lines=[{"condition_text": "b", "percent": "100"}],
    )
    assert r.status_code == 409, r.text


def test_empty_list_clears(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "a", "percent": "100"}],
    )
    assert r.status_code == 200, r.text
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = _put_schedule(admin_client, order, mode=None, lines=[])
    assert r.status_code == 200, r.text
    assert r.json()["lines"] == []
    assert r.json()["mode"] is None


def test_schedule_does_not_create_financial_facts(admin_client, db):
    pays_before = db.query(Payment).count()
    payables_before = db.query(Payable).count()
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "anticipato", "percent": "100"}],
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.query(Payment).count() == pays_before
    assert db.query(Payable).count() == payables_before


def test_mixed_mode_rejected(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[
            {"condition_text": "a", "percent": "50"},
            {"condition_text": "b", "amount": "250"},
        ],
    )
    assert r.status_code == 400, r.text


def test_confirmed_amount_must_match_when_total_known(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "full", "amount": "500.00"}],
    )
    assert r.status_code == 200, r.text
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "parcial", "amount": "100.00"}],
        reason_code="ADJUST",
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "schedule_amount_mismatch"


def test_percent_derived_when_total_known(admin_client):
    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[
            {"condition_text": "50%", "percent": "50"},
            {"condition_text": "saldo", "percent": "50"},
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["coherence"] == "aligned"
    assert body["delta"] == "0.00"
    assert Decimal(body["lines"][0]["derived_amount"]) == Decimal("250.00")
    assert Decimal(body["lines"][1]["derived_amount"]) == Decimal("250.00")


def test_cockpit_schedule_does_not_change_financial_kpis(admin_client):
    order = _draft_order(admin_client)
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    before = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "anticipato", "percent": "100"}],
        reason_code="TERMS",
    )
    assert r.status_code == 200, r.text
    after = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert after["schedule"]["mode"] == "PERCENT"
    assert after["kpis"]["paid"] == before["kpis"]["paid"]
    assert after["kpis"]["advanced_credit"] == before["kpis"]["advanced_credit"]
    assert after["kpis"]["fx_exposure"] == before["kpis"]["fx_exposure"]
    assert after["kpis"]["invoiced"] == before["kpis"]["invoiced"]
    assert after["kpis"]["balance"] == before["kpis"]["balance"]
    assert "Previsto" not in json.dumps(after["kpis"])


def test_schedule_edit_does_not_reclassify_advance(admin_client, db):
    from datetime import date

    order = _draft_order(admin_client)
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    adv = admin_client.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "100.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "5.80",
            "register_without_fx_document": True,
        },
    )
    assert adv.status_code == 200, adv.text
    payment_id = adv.json()["payment_id"]
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "anticipato", "percent": "100"}],
        reason_code="TERMS",
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    pay = db.query(Payment).filter(Payment.id == payment_id).one()
    assert pay.purpose == "ADVANCE"
    listing = admin_client.get(f"/api/orders/{order['id']}/advances").json()
    assert listing["advances"][0]["purpose"] == "ADVANCE"
    summary = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary["kpis"]["advanced_credit"]) == Decimal("100.00")
    assert Decimal(summary["kpis"]["paid"]) == Decimal("0.00")


def _attach_pdf(client, invoice_id: int) -> None:
    from io import BytesIO

    r = client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF-1.4 fin4"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(invoice_id), "role": "official"},
    )
    assert r.status_code == 200, r.text


def _issue_full_invoice(client, order, *, number: str, amount: str, due: str):
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
                    "quantity": "10",
                    "unit_price_gross": "50",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": due, "amount": amount}],
        },
    ).json()
    _attach_pdf(client, inv["id"])
    inv = client.get(f"/api/invoices/{inv['id']}").json()
    issued = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert issued.status_code == 200, issued.text
    return issued.json()


def test_invoice_issue_does_not_consume_or_replace_schedule(admin_client, db):
    from datetime import date, timedelta

    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[
            {"condition_text": "bonifico anticipato", "percent": "50"},
            {"condition_text": "saldo 90 GG DFFM", "percent": "50"},
        ],
    )
    assert r.status_code == 200, r.text
    before = r.json()["lines"]
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    due = (date.today() + timedelta(days=30)).isoformat()
    inv = _issue_full_invoice(
        admin_client, order, number=f"F4INV-{_uid()}", amount="500.00", due=due
    )
    assert inv["status"] == "ISSUED"
    after = admin_client.get(f"/api/orders/{order['id']}/payment-schedule").json()
    assert after["mode"] == "PERCENT"
    assert [ln["percent"] for ln in after["lines"]] == [ln["percent"] for ln in before]
    assert [ln["condition_text"] for ln in after["lines"]] == [
        ln["condition_text"] for ln in before
    ]
    payables_after = db.query(Payable).filter(Payable.invoice_id == inv["id"]).count()
    assert payables_after >= 1
    summary = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary["kpis"]["invoiced"]) == Decimal("500.00")
    assert Decimal(summary["kpis"]["paid"]) == Decimal("0.00")
    assert summary["schedule"]["mode"] == "PERCENT"
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "100% antecipado", "percent": "100"}],
        reason_code="TERMS",
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.query(Payable).filter(Payable.invoice_id == inv["id"]).count() == payables_after
    summary2 = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(summary2["kpis"]["invoiced"]) == Decimal("500.00")
    assert Decimal(summary2["kpis"]["balance"]) == Decimal(summary["kpis"]["balance"])


def test_prepaid_schedule_is_not_advanced_credit(admin_client):
    from datetime import date

    order = _draft_order(admin_client)
    r = _put_schedule(
        admin_client,
        order,
        mode="PERCENT",
        lines=[{"condition_text": "100% anticipato", "percent": "100"}],
    )
    assert r.status_code == 200, r.text
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    mid = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(mid["kpis"]["advanced_credit"]) == Decimal("0.00")
    assert Decimal(mid["kpis"]["paid"]) == Decimal("0.00")
    adv = admin_client.post(
        f"/api/orders/{order['id']}/advances",
        json={
            "amount": "500.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "5.80",
            "register_without_fx_document": True,
        },
    )
    assert adv.status_code == 200, adv.text
    after = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert after["schedule"]["mode"] == "PERCENT"
    assert Decimal(after["kpis"]["advanced_credit"]) == Decimal("500.00")
    assert Decimal(after["kpis"]["paid"]) == Decimal("0.00")


def test_fx_exposure_ignores_schedule(admin_client):
    from datetime import date, timedelta

    order = _draft_order(admin_client)
    r = admin_client.post(
        f"/api/orders/{order['id']}/confirm",
        json={"expected_version": order["version"]},
    )
    assert r.status_code == 200, r.text
    order = r.json()
    due = (date.today() + timedelta(days=15)).isoformat()
    _issue_full_invoice(
        admin_client, order, number=f"F4FX-{_uid()}", amount="500.00", due=due
    )
    before = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert Decimal(before["kpis"]["fx_exposure"]) == Decimal("500.00")
    order = admin_client.get(f"/api/orders/{order['id']}").json()
    r = _put_schedule(
        admin_client,
        order,
        mode="AMOUNT",
        lines=[{"condition_text": "planejado", "amount": "500.00"}],
        reason_code="TERMS",
    )
    assert r.status_code == 200, r.text
    after = admin_client.get(f"/api/orders/{order['id']}/summary").json()
    assert after["kpis"]["fx_exposure"] == before["kpis"]["fx_exposure"]
    assert after["kpis"]["paid"] == before["kpis"]["paid"]
    assert after["schedule"]["mode"] == "AMOUNT"
