"""Fase pós-MVP 6 — UX operacional estilo planilha: endpoints e enriquecimento."""

from __future__ import annotations

from decimal import Decimal

from app.models import AuditLog, ImportationItem, ImportationOrder, Invoice
from app.services.demo_seed import run_demo_seed
from app.services.finance import invoice_balance


def _order(db, po: str) -> ImportationOrder:
    return db.query(ImportationOrder).filter(ImportationOrder.po_number == po).first()


def test_order_queue_has_operational_columns(db, admin_client):
    run_demo_seed(db)
    res = admin_client.get("/api/importations/order-queue?limit=200")
    assert res.status_code == 200
    body = res.json()
    assert body["items"]
    row = body["items"][0]
    for key in (
        "qty_ordered",
        "qty_invoiced",
        "qty_shipped",
        "products_count",
        "invoices_count",
        "invoices_settled_count",
        "docs_pending_count",
        "next_due_date",
        "overdue_count",
        "priority",
        "responsible",
        "internal_forecast_date",
        "brazil_operational_notes",
    ):
        assert key in row, f"coluna {key} ausente na fila"


def test_order_queue_invoice_counts_match_db(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-04-3INV")
    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == imp.id, Invoice.is_active.is_(True))
        .all()
    )
    total = len(invoices)
    settled = sum(1 for inv in invoices if invoice_balance(db, inv) == Decimal("0"))
    res = admin_client.get("/api/importations/order-queue?limit=200")
    row = next(r for r in res.json()["items"] if r["id"] == imp.id)
    assert row["invoices_count"] == total
    assert row["invoices_settled_count"] == settled
    assert row["invoices_settled_count"] <= row["invoices_count"]


def test_order_queue_qty_ordered_matches_items(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-04-3INV")
    expected = sum(
        (i.quantity_ordered or 0)
        for i in db.query(ImportationItem).filter(
            ImportationItem.importation_id == imp.id, ImportationItem.is_active.is_(True)
        )
    )
    res = admin_client.get("/api/importations/order-queue?limit=200")
    row = next(r for r in res.json()["items"] if r["id"] == imp.id)
    assert (row["qty_ordered"] or 0) == expected


def test_patch_brazil_fields_priority_responsible_forecast(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-01-OCEAN")
    res = admin_client.patch(
        f"/api/importations/{imp.id}/brazil-fields",
        json={
            "priority": "HIGH",
            "responsible": "Maria",
            "internal_forecast_date": "2026-09-01",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["priority"] == "HIGH"
    assert body["responsible"] == "Maria"
    assert body["internal_forecast_date"] == "2026-09-01"


def test_patch_brazil_fields_partial_does_not_touch_others(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-02-AIR")
    admin_client.patch(
        f"/api/importations/{imp.id}/brazil-fields",
        json={"responsible": "Joao", "priority": "LOW"},
    )
    # update parcial: só observação; mantém responsável/prioridade
    res = admin_client.patch(
        f"/api/importations/{imp.id}/brazil-fields",
        json={"brazil_operational_notes": "Acompanhar"},
    )
    body = res.json()
    assert body["brazil_operational_notes"] == "Acompanhar"
    assert body["responsible"] == "Joao"
    assert body["priority"] == "LOW"


def test_patch_brazil_fields_audits_each_field(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-05-MULTI")
    admin_client.patch(
        f"/api/importations/{imp.id}/brazil-fields",
        json={"priority": "MEDIUM", "responsible": "Ana"},
    )
    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "importation_order",
            AuditLog.entity_id == str(imp.id),
            AuditLog.action == "update_brazil_field",
        )
        .all()
    )
    fields = {log.field_changed for log in logs}
    assert "priority" in fields
    assert "responsible" in fields


def test_patch_item_mapping_updates_and_audits(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-04-3INV")
    item = db.query(ImportationItem).filter(
        ImportationItem.importation_id == imp.id, ImportationItem.is_active.is_(True)
    ).first()
    res = admin_client.patch(
        f"/api/importations/{imp.id}/items/{item.id}",
        json={"supplier_sku": "SKU-BR-99", "description": "Modelo revisado"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["supplier_sku"] == "SKU-BR-99"
    assert body["description"] == "Modelo revisado"
    log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "importation_item",
            AuditLog.action == "update_item_mapping",
            AuditLog.field_changed == "supplier_sku",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.new_value == "SKU-BR-99"


def test_patch_item_mapping_unknown_item_404(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-04-3INV")
    res = admin_client.patch(
        f"/api/importations/{imp.id}/items/999999",
        json={"supplier_sku": "X"},
    )
    assert res.status_code == 404


def test_order_central_model_has_category_and_sku(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-04-3INV")
    res = admin_client.get(f"/api/importations/{imp.id}/order-central")
    assert res.status_code == 200
    models = res.json()["models"]
    assert models
    sample = models[0]
    assert "product_category" in sample
    assert "product_sku" in sample
    assert "description" in sample


def test_create_duplicate_order_friendly_message(db, admin_client):
    run_demo_seed(db)
    imp = _order(db, "DEMO-01-OCEAN")
    res = admin_client.post(
        "/api/importations",
        json={"po_number": imp.po_number, "supplier_id": imp.supplier_id, "currency": "EUR"},
    )
    assert res.status_code == 409
    assert "já existe" in res.json()["detail"].lower()
