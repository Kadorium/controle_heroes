"""Testes da API agregada do dashboard."""

from decimal import Decimal

from app.models import ImportationOrder, Invoice, Supplier


def _login(client):
    client.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})


def test_dashboard_summary_structure(client, db):
    _login(client)
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "open_importations_count" in data
    assert "payments_due_count" in data
    assert "data_availability" in data
    assert len(data["stage_counts"]) == 7


def test_dashboard_importations_includes_created_po(client, db):
    supplier = Supplier(name="Dash Supplier Unique", country="CN", currency_default="EUR", is_active=True)
    db.add(supplier)
    db.flush()
    imp = ImportationOrder(
        po_number="DASH-PO-UNIQUE-001",
        supplier_id=supplier.id,
        currency="EUR",
        estimated_total=Decimal("1000"),
        current_status="PO_CREATED",
    )
    db.add(imp)
    db.flush()
    db.add(
        Invoice(
            importation_id=imp.id,
            invoice_type="PROFORMA",
            invoice_number="INV-DASH-UNIQUE",
            amount=Decimal("1000"),
            currency="EUR",
            is_active=True,
        )
    )
    db.commit()

    _login(client)
    summary = client.get("/api/dashboard/summary").json()
    assert summary["open_importations_count"] >= 1
    assert summary["open_value_by_currency"].get("EUR") is not None

    rows = client.get("/api/dashboard/importations").json()
    po_numbers = [r["po_number"] for r in rows["items"]]
    assert "DASH-PO-UNIQUE-001" in po_numbers
    row = next(r for r in rows["items"] if r["po_number"] == "DASH-PO-UNIQUE-001")
    assert Decimal(row["open_value"]) == Decimal("1000")


def test_dashboard_null_invoice_amount_not_invented(client, db):
    supplier = Supplier(name="Dash Supplier Null", country="CN", currency_default="EUR", is_active=True)
    db.add(supplier)
    db.flush()
    imp = ImportationOrder(
        po_number="DASH-PO-NULL-UNIQUE",
        supplier_id=supplier.id,
        currency="EUR",
        current_status="PO_CREATED",
    )
    db.add(imp)
    db.flush()
    db.add(
        Invoice(
            importation_id=imp.id,
            invoice_type="PROFORMA",
            invoice_number="INV-NULL-UNIQUE",
            amount=None,
            currency="EUR",
            is_active=True,
        )
    )
    db.commit()

    _login(client)
    item = next(
        r
        for r in client.get("/api/dashboard/importations").json()["items"]
        if r["po_number"] == "DASH-PO-NULL-UNIQUE"
    )
    assert item["open_value"] is None
