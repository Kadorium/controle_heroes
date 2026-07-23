"""Liquidação em BRL deve refletir em total_paid EUR via câmbio da fatura."""

import uuid
from decimal import Decimal

import pytest


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


@pytest.fixture()
def importation_with_item(admin_client):
    supplier = admin_client.post(
        "/api/suppliers",
        json={"name": f"BRL Supplier {_uid()}", "country": "CN", "currency_default": "EUR"},
    ).json()
    product = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-BRL-{_uid()}", "description": "Item", "ncm": "95069900"},
    ).json()
    return admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-BRL-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity_ordered": 100,
                    "unit_price_foreign": "10",
                }
            ],
        },
    ).json()


def test_brl_settlement_uses_invoice_provision_rate(admin_client, importation_with_item):
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": importation_with_item["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-BRL-{_uid()}",
            "currency": "EUR",
            "amount": "1000",
            "expected_exchange_rate": "5.00",
            "items": [{"importation_item_id": items[0]["id"], "quantity": 10}],
        },
    ).json()

    planned = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "ADVANCE",
            "due_date": "2026-12-01",
            "amount_foreign": "5000",
            "currency_foreign": "BRL",
        },
    )
    assert planned.status_code == 201
    pay_id = planned.json()["id"]

    settled = admin_client.patch(
        f"/api/finance/payments/{pay_id}",
        json={
            "payment_date": "2026-06-26",
            "receipt_reference": f"REC-{_uid()}",
        },
    )
    assert settled.status_code == 200

    oh = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central").json()[
        "operational_header"
    ]
    assert oh["settled_eur"] is not None
    assert Decimal(oh["settled_eur"]) == Decimal("1000")
    assert oh["settled_brl"] is not None
    assert Decimal(oh["settled_brl"]) == Decimal("5000")
    assert Decimal(oh["balance_to_settle_eur"]) == Decimal("0")
