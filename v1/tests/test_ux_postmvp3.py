"""Testes Fase pós-MVP 3 — UX operacional."""

import uuid
from decimal import Decimal

from app.models import ImportationOrder, Invoice, Supplier


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _setup(admin_client, db):
    tag = _uid()
    supplier = Supplier(name=f"UX Sup {tag}", country="CN", currency_default="EUR", is_active=True)
    db.add(supplier)
    db.flush()
    imp = ImportationOrder(
        po_number=f"UX-{tag}",
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
        invoice_number=f"INV-{tag}",
        amount=Decimal("5000"),
        currency="EUR",
        is_active=True,
    )
    db.add(inv)
    db.commit()
    return imp, inv


def test_list_discounts_by_importation(admin_client, db):
    imp, inv = _setup(admin_client, db)
    res = admin_client.post(
        "/api/finance/discounts",
        json={
            "invoice_id": inv.id,
            "discount_type": "GLOBAL",
            "amount": "100",
            "currency": "EUR",
            "reason": "UX test",
        },
    )
    assert res.status_code == 201
    listed = admin_client.get(f"/api/finance/discounts?importation_id={imp.id}").json()
    assert len(listed) >= 1
    assert listed[0]["reason"] == "UX test"


def test_brazil_account_list_and_create(admin_client, db):
    imp, _ = _setup(admin_client, db)
    supplier_id = imp.supplier_id
    created = admin_client.post(
        "/api/finance/brazil-accounts",
        json={
            "supplier_id": supplier_id,
            "description": "Compensação UX",
            "amount": "500",
            "currency": "BRL",
            "financial_impact_estimated": "500",
            "origin_importation_id": imp.id,
        },
    )
    assert created.status_code == 201
    listed = admin_client.get("/api/finance/brazil-accounts").json()
    assert any(a["description"] == "Compensação UX" for a in listed)


def test_expense_with_landed_cost_flag(admin_client, db):
    imp, _ = _setup(admin_client, db)
    res = admin_client.post(
        "/api/finance/expenses",
        json={
            "importation_id": imp.id,
            "expense_type": "FREIGHT",
            "amount": "200",
            "currency": "BRL",
            "is_included_in_landed_cost": True,
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["is_included_in_landed_cost"] is True
    listed = admin_client.get(f"/api/finance/expenses?importation_id={imp.id}").json()
    assert len(listed) >= 1


def test_timeline_human_summary(admin_client, db):
    from app.services.auth import write_audit_log
    from app.services.closure import get_timeline

    imp, _ = _setup(admin_client, db)
    write_audit_log(
        db,
        user_id=1,
        entity_type="importation_order",
        entity_id=str(imp.id),
        action="update",
        field_changed="observacao",
        new_value="Teste UX",
    )
    db.commit()
    events = get_timeline(db, imp.id)
    assert len(events) >= 1
    assert any(e.get("summary") for e in events)


def test_dashboard_summary_no_fake_data(admin_client):
    summary = admin_client.get("/api/dashboard/summary").json()
    assert "open_importations_count" in summary
    assert "payments_due_count" in summary
    assert summary["data_availability"]["payments_due"] in (True, False)


def test_empty_invoice_stays_null(admin_client, db):
    _, inv = _setup(admin_client, db)
    inv_empty = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": inv.importation_id,
            "invoice_type": "PROFORMA",
            "invoice_number": f"EMPTY-{_uid()}",
            "currency": "EUR",
            "amount": None,
        },
    ).json()
    assert inv_empty["amount"] is None
