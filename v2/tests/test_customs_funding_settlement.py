"""CUSTOMS-FUNDING settlement — Payment → Allocation → Payable."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _process(client):
    r = client.post("/api/import-processes", json={"external_reference": f"DUIMP-{_uid()}"})
    assert r.status_code == 201, r.text
    return r.json()


def _payee(client, *, name="Bechtrans", tax_id=None):
    body = {"name": name}
    if tax_id is not None:
        body["tax_id"] = tax_id
    r = client.post("/api/customs/payees", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _funding(client, process_id: int, payee_id: int, *, declared_total="1500.00", **extra):
    body = {
        "payee_id": payee_id,
        "currency": "BRL",
        "declared_total": declared_total,
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        **extra,
    }
    r = client.post(f"/api/import-processes/{process_id}/funding-requests", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _confirm(client, process_id: int, fr: dict) -> dict:
    r = client.post(
        f"/api/import-processes/{process_id}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _register_customs_payment(client, payable_id: int, amount: str, **kw):
    r = client.post(
        "/api/payments",
        json={
            "payable_id": payable_id,
            "amount": amount,
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
            **kw,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _allocate(client, payment: dict, payable: dict, amount: str, *, key: str | None = None):
    r = client.post(
        f"/api/payments/{payment['id']}/allocations",
        json={
            "expected_version": payment["version"],
            "idempotency_key": key or f"alloc-{_uid()}",
            "allocations": [
                {
                    "payable_id": payable["id"],
                    "amount": amount,
                    "expected_version": payable["version"],
                }
            ],
        },
    )
    return r


def test_migration_028_revises_027():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("028")
    assert rev is not None
    assert rev.down_revision == "027"
    assert script.get_current_head() == "031"
    assert EXPECTED_ALEMBIC_REVISION == "031"


def test_scenario_a_full_settlement(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}", tax_id="12345678000199")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="100.00"))
    payable_id = fr["payable_links"][0]["payable_id"]
    p = c.get(f"/api/payables/{payable_id}").json()
    assert p["source_id"] == fr["id"]
    assert p["payee_tax_id"] == "12345678000199"
    assert p["source_type"] == "CUSTOMS_FUNDING"

    pay = _register_customs_payment(c, payable_id, "100.00")
    assert pay["supplier_id"] is None
    assert pay["payee_display_name"] == payee["name"]
    assert pay["purpose"] == "SETTLEMENT"
    assert pay["currency"] == "BRL"
    assert pay["order_id"] is None
    assert pay["amount_unallocated"] == "100.00"

    summary = c.get(
        "/api/payables/settlement-summary",
        params={"source_type": "CUSTOMS_FUNDING", "source_id": fr["id"]},
    ).json()
    assert summary["derived_status"] == "TO_PAY"
    assert summary["balance"] == "100.00"

    r = _allocate(c, pay, p, "100.00")
    assert r.status_code == 200, r.text
    p2 = c.get(f"/api/payables/{payable_id}").json()
    assert p2["status"] == "PAID"
    assert Decimal(p2["balance"]) == Decimal("0")

    summary = c.get(
        "/api/payables/settlement-summary",
        params={"source_type": "CUSTOMS_FUNDING", "source_id": fr["id"]},
    ).json()
    assert summary["derived_status"] == "PAID"
    assert summary["derived_status_label"] == "Pago"
    assert summary["balance"] == "0.00"
    assert summary["allocations"]

    funding = c.get(f"/api/customs/funding-requests/{fr['id']}").json()
    assert funding["status"] == "CONFIRMED"
    assert funding["settlement_summary"]["derived_status"] == "PAID"


def test_scenario_b_partial_then_residual(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="100.00"))
    pid = fr["payable_links"][0]["payable_id"]
    p = c.get(f"/api/payables/{pid}").json()

    pay1 = _register_customs_payment(c, pid, "40.00")
    r = _allocate(c, pay1, p, "40.00")
    assert r.status_code == 200, r.text
    p = c.get(f"/api/payables/{pid}").json()
    assert p["status"] == "PARTIALLY_PAID"
    summary = c.get(
        "/api/payables/settlement-summary",
        params={"source_type": "CUSTOMS_FUNDING", "source_id": fr["id"]},
    ).json()
    assert summary["derived_status"] == "PARTIALLY_PAID"

    pay2 = _register_customs_payment(c, pid, "60.00")
    r = _allocate(c, pay2, p, "60.00")
    assert r.status_code == 200, r.text
    p = c.get(f"/api/payables/{pid}").json()
    assert p["status"] == "PAID"
    summary = c.get(
        "/api/payables/settlement-summary",
        params={"source_type": "CUSTOMS_FUNDING", "source_id": fr["id"]},
    ).json()
    assert summary["derived_status"] == "PAID"


def test_scenario_c_payment_larger_than_payable(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="100.00"))
    pid = fr["payable_links"][0]["payable_id"]
    p = c.get(f"/api/payables/{pid}").json()
    pay = _register_customs_payment(c, pid, "120.00")
    r = _allocate(c, pay, p, "100.00")
    assert r.status_code == 200, r.text
    pay = c.get(f"/api/payments/{pay['id']}").json()
    assert pay["amount_unallocated"] == "20.00"
    p = c.get(f"/api/payables/{pid}").json()
    assert p["status"] == "PAID"
    r2 = _allocate(c, pay, p, "20.00")
    assert r2.status_code == 400


def test_create_derives_payee_and_rejects_client_stamp(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="50.00"))
    pid = fr["payable_links"][0]["payable_id"]

    r = c.post(
        "/api/payments",
        json={
            "payable_id": pid,
            "payee_display_name": "Adulterado",
            "amount": "50.00",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    )
    assert r.status_code == 422

    r = c.post(
        "/api/payments",
        json={
            "payable_id": pid,
            "supplier_id": 1,
            "amount": "50.00",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    )
    assert r.status_code == 400

    r = c.post(
        "/api/payments",
        json={
            "payable_id": pid,
            "currency": "EUR",
            "amount": "50.00",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    )
    assert r.status_code == 400


def test_identity_tax_id_and_name_rules(admin_client, db):
    from app.billing import public as billing_public
    from app.billing.liquidation import customs_identity_matches

    assert customs_identity_matches(
        left_name="Bechtrans Ltda",
        left_tax_id="12.345.678/0001-99",
        right_name="Outro",
        right_tax_id="12345678000199",
    )
    assert not customs_identity_matches(
        left_name="Bechtrans",
        left_tax_id="123",
        right_name="Bechtrans",
        right_tax_id=None,
    )
    assert customs_identity_matches(
        left_name="  BECHTRANS  LTDA ",
        left_tax_id=None,
        right_name="bechtrans ltda",
        right_tax_id=None,
    )
    assert not customs_identity_matches(
        left_name="Bechtrans",
        left_tax_id=None,
        right_name="Bechtrans Despachos",
        right_tax_id=None,
    )

    c = admin_client
    process = _process(c)
    a = _payee(c, name="Alfa Despachos", tax_id="11111111000191")
    b = _payee(c, name="Alfa Despachos", tax_id="22222222000100")
    fr_a = _confirm(c, process["id"], _funding(c, process["id"], a["id"], declared_total="10.00"))
    fr_b = _confirm(c, process["id"], _funding(c, process["id"], b["id"], declared_total="10.00"))
    pa = c.get(f"/api/payables/{fr_a['payable_links'][0]['payable_id']}").json()
    pb = c.get(f"/api/payables/{fr_b['payable_links'][0]['payable_id']}").json()
    pay = _register_customs_payment(c, pa["id"], "10.00")
    r = _allocate(c, pay, pb, "10.00")
    assert r.status_code == 400
    eligible = billing_public.list_eligible_payables(
        db,
        currency="BRL",
        payee_display_name=pay["payee_display_name"],
        payee_tax_id=pay["payee_tax_id"],
        source_type="CUSTOMS_FUNDING",
    )
    ids = {p.id for p in eligible}
    assert pa["id"] in ids
    assert pb["id"] not in ids


def test_scenario_d_multi_payable_technical(admin_client, db):
    from datetime import date as d
    from app.billing import public as billing_public

    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="80.00"))
    first_id = fr["payable_links"][0]["payable_id"]
    second = billing_public.create_customs_payable_from_funding(
        db,
        funding_request_id=fr["id"],
        source_id=fr["id"],
        sequence=2,
        due_date=d.today(),
        amount=Decimal("20.00"),
        currency="BRL",
        payee_display_name=payee["name"],
        idempotent=False,
    )
    db.commit()
    pay = _register_customs_payment(c, first_id, "80.00")
    p1 = c.get(f"/api/payables/{first_id}").json()
    r = _allocate(c, pay, p1, "80.00")
    assert r.status_code == 200, r.text
    summary = c.get(
        "/api/payables/settlement-summary",
        params={"source_type": "CUSTOMS_FUNDING", "source_id": fr["id"]},
    ).json()
    assert summary["derived_status"] == "PARTIALLY_PAID"
    p2 = c.get(f"/api/payables/{second.id}").json()
    assert p2["status"] == "OPEN"


def test_cancel_funding_blocked_after_partial(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="200.00"))
    pid = fr["payable_links"][0]["payable_id"]
    p = c.get(f"/api/payables/{pid}").json()
    pay = _register_customs_payment(c, pid, "50.00")
    r = _allocate(c, pay, p, "50.00")
    assert r.status_code == 200, r.text
    fr = c.get(f"/api/customs/funding-requests/{fr['id']}").json()
    cancel = c.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/cancel",
        json={"expected_version": fr["version"]},
    )
    assert cancel.status_code == 409


def test_cancel_allocated_payment_blocked(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="30.00"))
    pid = fr["payable_links"][0]["payable_id"]
    p = c.get(f"/api/payables/{pid}").json()
    pay = _register_customs_payment(c, pid, "30.00")
    r = _allocate(c, pay, p, "30.00")
    assert r.status_code == 200, r.text
    pay = r.json()
    cancel = c.post(
        f"/api/payments/{pay['id']}/cancel",
        json={"expected_version": pay["version"]},
    )
    assert cancel.status_code in (400, 409)


def test_idempotency_replay_and_create_without_allocate(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="70.00"))
    pid = fr["payable_links"][0]["payable_id"]
    p = c.get(f"/api/payables/{pid}").json()
    key = f"pay-{_uid()}"
    pay = _register_customs_payment(c, pid, "70.00", idempotency_key=key)
    again = _register_customs_payment(c, pid, "70.00", idempotency_key=key)
    assert again["id"] == pay["id"]
    summary = c.get(
        "/api/payables/settlement-summary",
        params={"source_type": "CUSTOMS_FUNDING", "source_id": fr["id"]},
    ).json()
    assert summary["derived_status"] == "TO_PAY"
    assert summary["balance"] == "70.00"

    alloc_key = f"al-{_uid()}"
    r1 = _allocate(c, pay, p, "70.00", key=alloc_key)
    assert r1.status_code == 200, r1.text
    pay = r1.json()
    r2 = _allocate(c, pay, p, "70.00", key=alloc_key)
    assert r2.status_code == 200
    assert r2.json()["version"] == pay["version"]


def test_invoice_path_still_requires_supplier(admin_client):
    c = admin_client
    r = c.post(
        "/api/payments",
        json={
            "amount": "10.00",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    )
    assert r.status_code == 400


def test_with_document_form_payable_id(admin_client):
    c = admin_client
    process = _process(c)
    payee = _payee(c, name=f"Bechtrans-{_uid()}")
    fr = _confirm(c, process["id"], _funding(c, process["id"], payee["id"], declared_total="15.00"))
    pid = fr["payable_links"][0]["payable_id"]
    r = c.post(
        "/api/payments/with-document",
        data={
            "payable_id": str(pid),
            "amount": "15.00",
            "payment_date": date.today().isoformat(),
        },
        files={"file": ("recibo.pdf", BytesIO(b"%PDF-ensaio"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["supplier_id"] is None
    assert body["payee_display_name"] == payee["name"]
    assert body["documents"]
