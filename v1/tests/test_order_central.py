"""Testes da central da ordem e fila operacional — Fase 6."""

import uuid
from decimal import Decimal

import pytest

from app.models import ImportationOrder, Invoice, Payment, Shipment, Supplier


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
        json={"name": f"OC Supplier {_uid()}", "country": "CN", "currency_default": "EUR"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def product(admin_client):
    r = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-OC-{_uid()}", "description": "Raquete Pro", "ncm": "95069900"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation_with_item(admin_client, supplier, product):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-OC-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "incoterm": "FOB",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity_ordered": 100,
                    "unit_price_foreign": "25",
                }
            ],
        },
    )
    assert r.status_code == 201
    return r.json()


def _create_invoice_with_item(client, importation_id, item_id, product_id, **extra):
    payload = {
        "importation_id": importation_id,
        "invoice_type": "PROFORMA",
        "invoice_number": f"INV-{_uid()}",
        "currency": "EUR",
        "amount": "2500",
        "items": [
            {
                "importation_item_id": item_id,
                "product_id": product_id,
                "quantity": 50,
                "unit_price": "25",
                "amount": "1250",
            }
        ],
        **extra,
    }
    return client.post("/api/invoices", json=payload)


def _pay(client, invoice_id, amount, **extra):
    return client.post(
        "/api/finance/payments",
        json={
            "invoice_id": invoice_id,
            "payment_type": "PARTIAL",
            "amount_foreign": amount,
            "exchange_rate": "5.20",
            "receipt_reference": f"REC-{_uid()}",
            **extra,
        },
    )


def test_order_central_returns_invoices_with_items(admin_client, importation_with_item, product):
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv_resp = _create_invoice_with_item(
        admin_client,
        importation_with_item["id"],
        items[0]["id"],
        product["id"],
    )
    assert inv_resp.status_code == 201

    res = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central")
    assert res.status_code == 200
    data = res.json()
    assert len(data["invoices"]) == 1
    assert len(data["invoices"][0]["items"]) == 1
    item = data["invoices"][0]["items"][0]
    assert item["product_sku"] == product["sku_code"]
    assert item["quantity"] == 50


def test_order_central_quantities_per_model(admin_client, importation_with_item, product):
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    _create_invoice_with_item(
        admin_client,
        importation_with_item["id"],
        items[0]["id"],
        product["id"],
    )

    res = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central")
    assert res.status_code == 200
    models = res.json()["models"]
    assert len(models) == 1
    m = models[0]
    assert m["quantity_ordered"] == 100
    assert m["quantity_shipped"] is None
    assert m["quantity_invoiced"] == 50
    assert m["to_dispatch"] == 100
    assert m["model_label"] == product["sku_code"]


def test_order_central_acconto_and_balance(admin_client, importation_with_item, product):
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv = _create_invoice_with_item(
        admin_client,
        importation_with_item["id"],
        items[0]["id"],
        product["id"],
        amount="2500",
    ).json()

    pay = _pay(admin_client, inv["id"], "1000")
    assert pay.status_code == 201

    res = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central")
    assert res.status_code == 200
    data = res.json()
    assert Decimal(data["kpis"]["total_invoiced"]) == Decimal("2500")
    assert Decimal(data["kpis"]["total_paid"]) == Decimal("1000")
    assert Decimal(data["kpis"]["consolidated_balance"]) == Decimal("1500")
    assert len(data["payments_settled"]) == 1
    assert Decimal(data["invoices"][0]["balance"]) == Decimal("1500")


def test_order_queue_returns_faturado_pago_saldo(admin_client, importation_with_item, product):
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv = _create_invoice_with_item(
        admin_client,
        importation_with_item["id"],
        items[0]["id"],
        product["id"],
        amount="3000",
    ).json()
    _pay(admin_client, inv["id"], "800")

    res = admin_client.get("/api/importations/order-queue")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1
    row = next(i for i in data["items"] if i["id"] == importation_with_item["id"])
    assert Decimal(row["total_invoiced"]) == Decimal("3000")
    assert Decimal(row["total_paid"]) == Decimal("800")
    assert Decimal(row["consolidated_balance"]) == Decimal("2200")


def test_order_central_empty_field_not_zero(admin_client, supplier):
    r = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": admin_client.post(
                "/api/importations",
                json={
                    "po_number": f"PO-EMPTY-{_uid()}",
                    "supplier_id": supplier["id"],
                    "currency": "EUR",
                },
            ).json()["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"EMPTY-{_uid()}",
            "currency": "EUR",
            "amount": "",
        },
    )
    assert r.status_code == 201
    imp_id = r.json()["importation_id"]

    res = admin_client.get(f"/api/importations/{imp_id}/order-central")
    assert res.status_code == 200
    data = res.json()
    assert data["kpis"]["consolidated_balance"] is None
    assert data["invoices"][0]["amount"] is None
    assert data["invoices"][0]["balance"] is None


def test_multi_currency_not_summed_in_single_field(admin_client, db, supplier):
    imp = ImportationOrder(
        po_number=f"PO-MULTI-{_uid()}",
        supplier_id=supplier["id"],
        currency="EUR",
        current_status="PO_CREATED",
        is_active=True,
    )
    db.add(imp)
    db.flush()
    db.add(
        Invoice(
            importation_id=imp.id,
            invoice_type="PROFORMA",
            invoice_number=f"BRL-{_uid()}",
            amount=Decimal("1000"),
            currency="BRL",
            is_active=True,
        )
    )
    db.add(
        Invoice(
            importation_id=imp.id,
            invoice_type="PROFORMA",
            invoice_number=f"EUR-{_uid()}",
            amount=Decimal("500"),
            currency="EUR",
            is_active=True,
        )
    )
    db.commit()

    res = admin_client.get(f"/api/importations/{imp.id}/order-central")
    assert res.status_code == 200
    kpis = res.json()["kpis"]
    assert kpis["total_invoiced"] is None
    assert kpis["total_paid"] is None
    assert kpis["consolidated_balance"] is None
    assert kpis["totals_by_currency"] is not None
    assert Decimal(kpis["totals_by_currency"]["BRL"]["total_invoiced"]) == Decimal("1000")
    assert Decimal(kpis["totals_by_currency"]["EUR"]["total_invoiced"]) == Decimal("500")


def test_order_queue_route_before_id_route(admin_client):
    """Garante que /order-queue não é capturado por /{importation_id}."""
    res = admin_client.get("/api/importations/order-queue")
    assert res.status_code == 200
    assert "items" in res.json()


def test_importation_response_includes_updated_at(admin_client, importation_with_item):
    res = admin_client.get(f"/api/importations/{importation_with_item['id']}")
    assert res.status_code == 200
    assert "updated_at" in res.json()
    assert res.json()["updated_at"] is not None


def test_shipments_list_requires_importation_id(admin_client):
    res = admin_client.get("/api/shipments")
    assert res.status_code == 422


def test_demo_seed_shipments_idempotent(admin_client, db):
    from app.services.demo_seed import run_demo_seed

    run_demo_seed(db, user_id=1)
    count1 = db.query(Shipment).filter(Shipment.shipment_number == "SH-DEMO-02").count()
    run_demo_seed(db, user_id=1)
    count2 = db.query(Shipment).filter(Shipment.shipment_number == "SH-DEMO-02").count()
    assert count1 == count2
    assert count2 >= 1


def test_operational_header_partial_invoices_and_overdue(admin_client, importation_with_item, product):
    items = admin_client.get(f"/api/importations/{importation_with_item['id']}/items").json()
    inv1 = _create_invoice_with_item(
        admin_client,
        importation_with_item["id"],
        items[0]["id"],
        product["id"],
        amount="1000",
        expected_exchange_rate="5.00",
    ).json()
    inv2 = _create_invoice_with_item(
        admin_client,
        importation_with_item["id"],
        items[0]["id"],
        product["id"],
        amount="500",
        expected_exchange_rate="5.00",
        invoice_date="2020-01-15",
    ).json()
    _pay(admin_client, inv1["id"], "1000")

    res = admin_client.get(f"/api/importations/{importation_with_item['id']}/order-central")
    assert res.status_code == 200
    oh = res.json()["operational_header"]
    assert oh["invoices_count"] == 2
    assert oh["invoices_settled_count"] == 1
    assert oh["overdue_count"] == 1
    assert Decimal(oh["overdue_amount_foreign"]) == Decimal("500")
    assert oh["next_due_date"] == "2020-01-15"
    assert oh["next_open_invoice_number"] == inv2["invoice_number"]
    assert Decimal(oh["open_balance_brl_equivalent"]) == Decimal("2500")
    rail = res.json()["status_rail"]
    faturado = next(s for s in rail["stages"] if s["key"] == "faturado")
    assert faturado["subtitle"] == "1/2 faturas"


def test_financial_summary_null_when_no_invoices(admin_client, supplier):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-NOINV-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "incoterm": "FOB",
        },
    )
    assert r.status_code == 201
    imp_id = r.json()["id"]
    summary = admin_client.get(f"/api/finance/importations/{imp_id}/summary").json()
    assert summary["total_invoiced"] is None
    assert summary["total_paid"] is None
    assert summary["consolidated_balance"] is None
    oh = admin_client.get(f"/api/importations/{imp_id}/order-central").json()["operational_header"]
    assert oh["invoices_count"] == 0
    assert oh["total_invoiced"] is None
