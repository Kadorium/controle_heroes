"""Testes de vencimento (due_date) em pagamentos."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models import ImportationOrder, Invoice, Supplier


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _setup_invoice(db):
    tag = _uid()
    supplier = Supplier(name=f"Due Supplier {tag}", country="CN", currency_default="EUR", is_active=True)
    db.add(supplier)
    db.flush()
    imp = ImportationOrder(
        po_number=f"DUE-PO-{tag}",
        supplier_id=supplier.id,
        currency="EUR",
        estimated_total=Decimal("5000"),
        current_status="PO_CREATED",
    )
    db.add(imp)
    db.flush()
    inv = Invoice(
        importation_id=imp.id,
        invoice_type="PROFORMA",
        invoice_number=f"INV-DUE-{tag}",
        amount=Decimal("5000"),
        currency="EUR",
        is_active=True,
    )
    db.add(inv)
    db.commit()
    return inv, imp.po_number


def test_create_payment_with_due_date(admin_client, db):
    inv, _ = _setup_invoice(db)
    due = (date.today() + timedelta(days=3)).isoformat()
    res = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "1000",
            "due_date": due,
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["due_date"] == due
    assert body["payment_date"] is None


def test_create_payment_without_due_date_requires_receipt(admin_client, db):
    inv, _ = _setup_invoice(db)
    res = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "1000",
            "payment_date": date.today().isoformat(),
            "receipt_reference": "REC-001",
        },
    )
    assert res.status_code == 201
    assert res.json()["due_date"] is None


def test_list_payment_shows_due_date(admin_client, db):
    inv, _ = _setup_invoice(db)
    due = (date.today() + timedelta(days=5)).isoformat()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "500",
            "due_date": due,
        },
    )
    listed = admin_client.get(f"/api/finance/payments?invoice_id={inv.id}").json()
    assert len(listed) == 1
    assert listed[0]["due_date"] == due


def test_planned_payment_does_not_reduce_invoice_balance(admin_client, db):
    inv, _ = _setup_invoice(db)
    due = (date.today() + timedelta(days=2)).isoformat()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "2000",
            "due_date": due,
        },
    )
    summary = admin_client.get(f"/api/finance/importations/{inv.importation_id}/summary").json()
    assert Decimal(summary["consolidated_balance"]) == Decimal("5000")


def test_dashboard_payments_due_kpi(admin_client, db):
    inv, _ = _setup_invoice(db)
    due = (date.today() + timedelta(days=4)).isoformat()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "1500",
            "due_date": due,
        },
    )
    summary = admin_client.get("/api/dashboard/summary").json()
    assert summary["data_availability"]["payments_due"] is True
    assert summary["payments_due_count"] >= 1


def test_overdue_payment_in_dashboard(admin_client, db):
    inv, po = _setup_invoice(db)
    overdue = (date.today() - timedelta(days=2)).isoformat()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "800",
            "due_date": overdue,
        },
    )
    summary = admin_client.get("/api/dashboard/summary").json()
    assert summary["payments_overdue_count"] >= 1
    rows = admin_client.get("/api/dashboard/importations").json()["items"]
    row = next(r for r in rows if r["po_number"] == po)
    assert any(p.get("is_overdue") for p in row["pending_payments"])


def test_liquidate_planned_payment_reduces_balance(admin_client, db):
    inv, _ = _setup_invoice(db)
    due = (date.today() + timedelta(days=5)).isoformat()
    created = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "2000",
            "due_date": due,
        },
    ).json()
    before = admin_client.get(f"/api/finance/importations/{inv.importation_id}/summary").json()
    assert Decimal(before["consolidated_balance"]) == Decimal("5000")

    settled = admin_client.patch(
        f"/api/finance/payments/{created['id']}",
        json={
            "payment_date": date.today().isoformat(),
            "receipt_reference": "REC-LIQ",
        },
    )
    assert settled.status_code == 200
    after = admin_client.get(f"/api/finance/importations/{inv.importation_id}/summary").json()
    assert Decimal(after["consolidated_balance"]) == Decimal("3000")


def test_update_payment_due_date(admin_client, db):
    inv, _ = _setup_invoice(db)
    created = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv.id,
            "payment_type": "PARTIAL",
            "amount_foreign": "300",
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    ).json()
    new_due = (date.today() + timedelta(days=6)).isoformat()
    updated = admin_client.patch(
        f"/api/finance/payments/{created['id']}",
        json={"due_date": new_due},
    )
    assert updated.status_code == 200
    assert updated.json()["due_date"] == new_due
