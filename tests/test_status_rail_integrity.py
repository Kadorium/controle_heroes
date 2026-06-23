"""Integridade da régua de status e interatividade da Visão Geral."""

from __future__ import annotations

from app.models import AuditLog, ImportationOrder, Invoice, Payment
from app.services.demo_seed import run_demo_seed
from app.services.order_status_rail import build_status_rail


def test_no_faturado_check_without_invoices():
    rail = build_status_rail(
        "IN_TRANSIT",
        has_invoices=False,
        has_payments=False,
        has_shipments=True,
        shipment_in_transit=True,
    )
    faturado = next(s for s in rail["stages"] if s["key"] == "faturado")
    assert faturado["state"] != "done"
    assert faturado["state"] == "declared_without_data"


def test_no_acconto_check_without_payments():
    rail = build_status_rail(
        "IN_TRANSIT",
        has_invoices=True,
        has_payments=False,
        has_shipments=True,
        shipment_in_transit=True,
    )
    acconto = next(s for s in rail["stages"] if s["key"] == "acconto")
    assert acconto["state"] != "done"
    assert acconto["state"] == "declared_without_data"


def test_no_transito_check_without_shipment():
    rail = build_status_rail(
        "IN_TRANSIT",
        has_invoices=True,
        has_payments=True,
        has_shipments=False,
        shipment_in_transit=False,
    )
    transito = next(s for s in rail["stages"] if s["key"] == "transito")
    assert transito["state"] != "done"
    assert transito["state"] == "declared_without_data"


def test_declared_without_data_generates_alert():
    rail = build_status_rail(
        "IN_TRANSIT",
        has_invoices=False,
        has_payments=False,
        has_shipments=False,
        shipment_in_transit=False,
    )
    assert len(rail["alerts"]) >= 1
    assert any("sem dado" in a for a in rail["alerts"])


def test_demo_01_ocean_coherent_after_seed(db):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-01-OCEAN").first()
    assert imp is not None
    assert db.query(Invoice).filter(Invoice.importation_id == imp.id).count() >= 1
    assert (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.importation_id == imp.id)
        .count()
        >= 1
    )
    central = __import__("app.services.order_central", fromlist=["build_order_central"]).build_order_central(db, imp.id)
    rail = central["status_rail"]
    for key in ("faturado", "acconto", "transito"):
        stage = next(s for s in rail["stages"] if s["key"] == key)
        assert stage["state"] == "done", f"{key} deve ter dado de suporte"


def test_demo_02_air_coherent_after_seed(db):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-02-AIR").first()
    assert imp is not None
    central = __import__("app.services.order_central", fromlist=["build_order_central"]).build_order_central(db, imp.id)
    rail = central["status_rail"]
    faturado = next(s for s in rail["stages"] if s["key"] == "faturado")
    assert faturado["state"] == "done"


def test_brazil_notes_update_audit_log(db, admin_client):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-04-3INV").first()
    res = admin_client.patch(
        f"/api/importations/{imp.id}/brazil-fields",
        json={"brazil_operational_notes": "Nota teste Brasil"},
    )
    assert res.status_code == 200
    assert res.json()["brazil_operational_notes"] == "Nota teste Brasil"
    log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "importation_order",
            AuditLog.action == "update_brazil_field",
            AuditLog.field_changed == "brazil_operational_notes",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.new_value == "Nota teste Brasil"


def test_allowed_transitions_lists_blocked(db, admin_client):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-01-OCEAN").first()
    res = admin_client.get(f"/api/importations/{imp.id}/allowed-transitions")
    assert res.status_code == 200
    body = res.json()
    assert body["current_status"] == imp.current_status
    assert isinstance(body["transitions"], list)


def test_transition_blocked_shows_reason(db, admin_client):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-04-3INV").first()
    res = admin_client.post(
        f"/api/importations/{imp.id}/transition",
        json={"new_status": "IN_TRANSIT"},
    )
    assert res.status_code == 400
    assert "Transição inválida" in res.json()["detail"]


def test_italy_override_requires_attachment(db, admin_client):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-06-PARTIAL").first()
    inv = db.query(Invoice).filter(Invoice.importation_id == imp.id).first()
    res = admin_client.post(
        f"/api/importations/{imp.id}/italy-overrides",
        json={
            "entity_type": "invoice",
            "entity_id": inv.id,
            "field_name": "invoice_number",
            "new_value": "PRO-06-FIX",
            "reason": "Correção conferida",
            "attachment_id": 999999,
        },
    )
    assert res.status_code == 400


def test_italy_override_with_attachment_and_audit(db, admin_client):
    run_demo_seed(db)
    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == "DEMO-06-PARTIAL").first()
    inv = db.query(Invoice).filter(Invoice.importation_id == imp.id).first()
    up = admin_client.post(
        "/api/documents/upload",
        files={"file": ("proof.txt", b"comprovante", "text/plain")},
        data={
            "entity_type": "importation_order",
            "entity_id": str(imp.id),
            "document_type": "ITALY_OVERRIDE",
        },
    )
    assert up.status_code == 201, up.text
    att_id = up.json()["id"]
    res = admin_client.post(
        f"/api/importations/{imp.id}/italy-overrides",
        json={
            "entity_type": "invoice",
            "entity_id": inv.id,
            "field_name": "invoice_number",
            "new_value": "PRO-06-OVERRIDE",
            "reason": "Correção com comprovante anexo",
            "attachment_id": att_id,
        },
    )
    assert res.status_code == 200, res.text
    db.refresh(inv)
    assert inv.invoice_number == "PRO-06-OVERRIDE"
    log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "italy_field_override", AuditLog.entity_id == str(inv.id))
        .first()
    )
    assert log is not None
