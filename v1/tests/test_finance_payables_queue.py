"""Fila global payables-queue — KPIs, agrupamento, null-rate, cascade PATCH."""

import uuid
from decimal import Decimal

import pytest


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _create_order(client, *, rate: str | None = "5.00"):
    uid = _uid()
    sup = client.post(
        "/api/suppliers",
        json={"name": f"PayQ Sup {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    body = {
        "po_number": f"PO-PAYQ-{uid}",
        "supplier_id": sup["id"],
        "currency": "EUR",
        "estimated_total": "10000",
    }
    if rate is not None:
        body["opening_exchange_rate"] = rate
    return client.post("/api/importations", json=body).json()


def test_payables_queue_null_rate_no_500(admin_client):
    """Ordem sem câmbio — HTTP 200, KPIs null/zero, sem divide-by-zero."""
    imp = _create_order(admin_client, rate=None)
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": imp["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-NULL-{ _uid() }",
            "currency": "EUR",
            "amount": "1000",
        },
    ).json()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "ADVANCE",
            "amount_foreign": "500",
            "currency_foreign": "EUR",
            "payment_date": "2026-06-01",
            "receipt_reference": "ACCONTO-1",
        },
    )
    res = admin_client.get("/api/finance/payables-queue")
    assert res.status_code == 200
    data = res.json()
    assert "kpis" in data
    assert data["kpis"]["total_settled_brl"] is None or Decimal(data["kpis"]["total_settled_brl"] or "0") >= 0
    order = next(o for o in data["orders"] if o["importation_id"] == imp["id"])
    pay = order["invoices"][0]["payments"][0]
    assert pay["display_brl"] is None
    assert pay["display_rate"] is None


def test_payables_queue_with_provision_estimated_brl(admin_client):
    imp = _create_order(admin_client, rate="5.00")
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": imp["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-PQ-{ _uid() }",
            "currency": "EUR",
            "amount": "1000",
            "expected_exchange_rate": "5.00",
        },
    ).json()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "ADVANCE",
            "amount_foreign": "200",
            "currency_foreign": "EUR",
            "payment_date": "2026-06-01",
            "receipt_reference": "ACCONTO-EUR",
        },
    )
    res = admin_client.get("/api/finance/payables-queue")
    assert res.status_code == 200
    order = next(o for o in res.json()["orders"] if o["importation_id"] == imp["id"])
    pay = order["invoices"][0]["payments"][0]
    assert Decimal(pay["display_brl"]) == Decimal("1000.00")
    assert pay["brl_is_estimated"] is True
    assert Decimal(order["opening_exchange_rate"]) == Decimal("5.00")


def test_payables_queue_patch_invoice_recalculates_display_brl(admin_client):
    imp = _create_order(admin_client, rate="5.00")
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": imp["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-CAS-{ _uid() }",
            "currency": "EUR",
            "amount": "100",
            "expected_exchange_rate": "5.00",
        },
    ).json()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "ADVANCE",
            "amount_foreign": "100",
            "currency_foreign": "EUR",
            "payment_date": "2026-06-01",
            "receipt_reference": "ACCONTO",
        },
    )
    before = admin_client.get("/api/finance/payables-queue").json()
    pay_before = next(
        p
        for o in before["orders"]
        if o["importation_id"] == imp["id"]
        for i in o["invoices"]
        if i["id"] == inv["id"]
        for p in i["payments"]
    )
    assert pay_before["display_brl"] == "500.00"

    patch = admin_client.patch(
        f"/api/invoices/{inv['id']}",
        json={"expected_exchange_rate": "6.00", "rate_change_reason": "Revisão operacional teste"},
    )
    assert patch.status_code == 200

    after = admin_client.get("/api/finance/payables-queue").json()
    pay_after = next(
        p
        for o in after["orders"]
        if o["importation_id"] == imp["id"]
        for i in o["invoices"]
        if i["id"] == inv["id"]
        for p in i["payments"]
    )
    assert pay_after["display_brl"] == "600.00"
    assert pay_after["brl_is_estimated"] is True


def test_payables_queue_requires_reason_on_rate_change(admin_client):
    imp = _create_order(admin_client, rate="5.00")
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": imp["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-RSN-{ _uid() }",
            "currency": "EUR",
            "amount": "100",
            "expected_exchange_rate": "5.00",
        },
    ).json()
    res = admin_client.patch(
        f"/api/invoices/{inv['id']}",
        json={"expected_exchange_rate": "5.50"},
    )
    assert res.status_code == 400


def test_invoice_number_normalize_parser():
    from app.services.heroes_xlsx_parser import _normalize_invoice_number

    assert _normalize_invoice_number(72) == "72"
    assert _normalize_invoice_number(72.0) == "72"
    assert _normalize_invoice_number("72.0") == "72"
    assert _normalize_invoice_number("F-100") == "F-100"
