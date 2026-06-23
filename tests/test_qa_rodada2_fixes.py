"""QA Rodada 2 — regressões dos bugs HIGH/MEDIUM do E2E QA-UI-001."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.models import ImportationItem, Shipment, ShipmentItem


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
def supplier(admin_client):
    r = admin_client.post(
        "/api/suppliers",
        json={"name": f"QA Supplier {_uid()}", "country": "CN", "currency_default": "EUR"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation_with_item(admin_client, supplier):
    product = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-QA-{_uid()}", "description": "Item QA", "ncm": "95069900"},
    ).json()
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-QA-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity_ordered": 100,
                    "unit_price_foreign": "12.50",
                }
            ],
        },
    ).json()
    return imp


def test_qa_high_001_total_paid_null_without_settlement(admin_client, importation_with_item):
    """Acconto versado: sem liquidação → total_paid null (UI mostra —)."""
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": importation_with_item["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-{_uid()}",
            "currency": "EUR",
            "amount": "500",
            "items": [{"importation_item_id": items[0]["id"], "quantity": 50}],
        },
    ).json()
    # Pagamento planejado (não liquidado)
    planned = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "PARTIAL",
            "amount_foreign": "250",
            "due_date": "2026-12-01",
        },
    )
    assert planned.status_code == 201

    central = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central").json()
    assert central["kpis"]["total_paid"] is None

    summary = admin_client.get(f"/api/finance/importations/{importation_with_item['id']}/summary").json()
    assert summary["total_paid"] is None


def test_qa_high_001_total_paid_not_null_after_settlement(admin_client, importation_with_item):
    """Após liquidação real, total_paid deixa de ser null."""
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": importation_with_item["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-P-{_uid()}",
            "currency": "EUR",
            "amount": "100",
            "items": [{"importation_item_id": items[0]["id"], "quantity": 10}],
        },
    ).json()
    pay = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "PARTIAL",
            "amount_foreign": "100",
            "exchange_rate": "5.20",
            "receipt_reference": f"REC-{_uid()}",
        },
    )
    assert pay.status_code == 201

    central = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central").json()
    assert central["kpis"]["total_paid"] is not None
    assert Decimal(central["kpis"]["total_paid"]) == Decimal("100")


def test_qa_high_002_quantity_stages_null_before_events(admin_client, importation_with_item):
    """DESPACHADA/NAC/RECEB: sem evento → null; com embarque qty 0 → 0."""
    imp_id = importation_with_item["id"]
    central = admin_client.get(f"/api/importations/{imp_id}/order-central").json()
    m = central["models"][0]
    assert m["quantity_shipped"] is None
    assert m["quantity_nationalized"] is None
    assert m["quantity_stocked"] is None

    chain = admin_client.get(f"/api/stock/importations/{imp_id}/quantity-chain").json()
    assert chain[0]["quantity_shipped"] is None


def test_qa_high_002_quantity_shipped_zero_when_shipment_exists(db, admin_client, importation_with_item):
    """Embarque registrado com quantidade 0 → exibe 0 (não null)."""
    imp_id = importation_with_item["id"]
    item = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == imp_id, ImportationItem.is_active.is_(True))
        .first()
    )
    shipment = Shipment(
        importation_id=imp_id,
        shipment_number=f"SH-QA-{_uid()}",
        modal="OCEAN",
        status="PLANNED",
        is_active=True,
    )
    db.add(shipment)
    db.flush()
    db.add(
        ShipmentItem(
            shipment_id=shipment.id,
            importation_item_id=item.id,
            quantity_shipped=0,
            is_active=True,
        )
    )
    db.commit()

    central = admin_client.get(f"/api/importations/{imp_id}/order-central").json()
    assert central["models"][0]["quantity_shipped"] == 0


def test_qa_med_002_003_responsible_persists_get_and_queue(admin_client, importation_with_item):
    """Responsável e previsão persistem em GET e order-queue após PATCH."""
    imp_id = importation_with_item["id"]
    patch = admin_client.patch(
        f"/api/importations/{imp_id}/brazil-fields",
        json={"responsible": "QA Tester", "internal_forecast_date": "2026-08-15"},
    )
    assert patch.status_code == 200

    got = admin_client.get(f"/api/importations/{imp_id}").json()
    assert got["responsible"] == "QA Tester"
    assert got["internal_forecast_date"] == "2026-08-15"

    queue = admin_client.get("/api/importations/order-queue").json()
    row = next(r for r in queue["items"] if r["id"] == imp_id)
    assert row["responsible"] == "QA Tester"
    assert row["internal_forecast_date"] == "2026-08-15"
