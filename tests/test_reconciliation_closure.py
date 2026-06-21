"""Fases 10, 11 e 12 — testes críticos."""

import uuid

import pytest

from app.models import ImportationClosure, Reconciliation
from app.services.closure import close_importation, reopen_importation
from app.services.demo_seed import run_demo_seed
from app.services.reconciliation import run_reconciliations


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
        json={"name": f"Sup {_uid()}", "country": "CN", "currency_default": "EUR"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def product(admin_client):
    r = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-{_uid()}", "description": "Produto teste"},
    )
    assert r.status_code == 201
    return r.json()


def _upload_doc(client, importation_id, doc_type="PROFORMA"):
    return client.post(
        "/api/documents/upload",
        data={
            "entity_type": "importation_order",
            "entity_id": str(importation_id),
            "document_type": doc_type,
        },
        files={"file": ("doc.pdf", b"pdf-content", "application/pdf")},
    )


def _full_close_setup(admin_client, supplier, product):
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"CLOSE-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "estimated_total": "1000",
            "items": [{"product_id": product["id"], "quantity_ordered": 100, "unit_price_foreign": "10"}],
        },
    ).json()
    imp_id = imp["id"]
    _upload_doc(admin_client, imp_id, "PROFORMA")
    item = admin_client.get(f"/api/importations/{imp_id}/items").json()[0]
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": imp_id,
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-{_uid()}",
            "amount": "1000",
            "currency": "EUR",
        },
    ).json()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "FINAL",
            "amount_foreign": "1000",
            "currency_foreign": "EUR",
            "exchange_rate": "5.0",
            "receipt_reference": "COMP-001",
        },
    )
    doc = admin_client.post(
        "/api/customs/documents",
        json={
            "importation_id": imp_id,
            "document_type": "DI",
            "document_number": f"DI-{_uid()}",
            "document_data_json": {"raw": True},
        },
    ).json()
    admin_client.post(
        f"/api/customs/documents/{doc['id']}/approve",
        json={"official_data_json": {"number": doc["document_number"]}},
    )
    nat = admin_client.post(
        "/api/stock/nationalizations",
        json={
            "importation_id": imp_id,
            "customs_document_id": doc["id"],
            "items": [{"importation_item_id": item["id"], "quantity_nationalized": 100}],
        },
    ).json()
    admin_client.post(
        "/api/stock/entries",
        json={
            "nationalization_id": nat["id"],
            "importation_item_id": item["id"],
            "quantity_received": 100,
        },
    )
    lc = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": imp_id, "version_type": "INITIAL", "allocation_method": "VALUE"},
    ).json()
    lc_final = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": imp_id, "version_type": "FINAL", "allocation_method": "VALUE"},
    ).json()
    return imp_id, lc_final["id"]


def test_reconciliation_record(admin_client, supplier, product):
    imp_id, _ = _full_close_setup(admin_client, supplier, product)
    r = admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    types = {d["pair_type"] for d in data}
    assert "INVOICE_PAYMENT" in types


def test_invoice_payment_reconciliation(admin_client, supplier, product):
    imp_id, _ = _full_close_setup(admin_client, supplier, product)
    recs = admin_client.post(f"/api/reconciliation/importations/{imp_id}/run").json()
    inv_pay = next(r for r in recs if r["pair_type"] == "INVOICE_PAYMENT")
    assert inv_pay["status"] in ("OK", "WARNING", "APPROVED")


def test_close_blocked_with_divergence(admin_client, supplier, product):
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"BLK-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [{"product_id": product["id"], "quantity_ordered": 100, "unit_price_foreign": "10"}],
        },
    ).json()
    r = admin_client.post(f"/api/closure/importations/{imp['id']}/close", json={})
    assert r.status_code == 400


def test_close_clean(admin_client, supplier, product):
    imp_id, lc_id = _full_close_setup(admin_client, supplier, product)
    admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    r = admin_client.post(
        f"/api/closure/importations/{imp_id}/close",
        json={"landed_cost_version_id": lc_id},
    )
    assert r.status_code == 201
    imp = admin_client.get(f"/api/importations/{imp_id}").json()
    assert imp["current_status"] == "CLOSED"


def test_close_with_approved_variance(admin_client, supplier, product):
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"VAR-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "estimated_total": "1000",
            "items": [{"product_id": product["id"], "quantity_ordered": 100, "unit_price_foreign": "10"}],
        },
    ).json()
    imp_id = imp["id"]
    _upload_doc(admin_client, imp_id)
    inv = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": imp_id,
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-{_uid()}",
            "amount": "1000",
            "currency": "EUR",
        },
    ).json()
    admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "FINAL",
            "amount_foreign": "1000",
            "currency_foreign": "EUR",
            "exchange_rate": "5.0",
            "receipt_reference": "COMP-VAR",
        },
    )
    item = admin_client.get(f"/api/importations/{imp_id}/items").json()[0]
    doc = admin_client.post(
        "/api/customs/documents",
        json={
            "importation_id": imp_id,
            "document_type": "DI",
            "document_number": f"DI-{_uid()}",
            "document_data_json": {},
        },
    ).json()
    admin_client.post(
        f"/api/customs/documents/{doc['id']}/approve",
        json={"official_data_json": {"number": doc["document_number"]}},
    )
    admin_client.post(
        "/api/stock/nationalizations",
        json={
            "importation_id": imp_id,
            "customs_document_id": doc["id"],
            "items": [{"importation_item_id": item["id"], "quantity_nationalized": 90}],
        },
    )
    lc = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": imp_id, "version_type": "FINAL", "allocation_method": "VALUE"},
    ).json()
    recs = admin_client.post(f"/api/reconciliation/importations/{imp_id}/run").json()
    divergent = [r for r in recs if r["status"] == "DIVERGENT" and r["severity"] == "BLOCKING"]
    assert divergent
    r = admin_client.post(
        f"/api/closure/importations/{imp_id}/close",
        json={
            "landed_cost_version_id": lc["id"],
            "approved_reconciliation_ids": [divergent[0]["id"]],
            "reason_code": "DISCREPANCY_QUANTITY",
            "justification": "Divergência aprovada pelo gestor",
        },
    )
    assert r.status_code == 201
    assert r.json()["closure_type"] == "WITH_APPROVED_VARIANCE"


def test_snapshot_preserved(admin_client, supplier, product, db):
    imp_id, lc_id = _full_close_setup(admin_client, supplier, product)
    admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    closure = admin_client.post(
        f"/api/closure/importations/{imp_id}/close",
        json={"landed_cost_version_id": lc_id},
    ).json()
    stored = db.query(ImportationClosure).filter(ImportationClosure.id == closure["id"]).first()
    assert stored.snapshot_json["po_number"]
    assert stored.snapshot_json["landed_cost_version_id"] == lc_id


def test_reopen_blocked_without_reason(admin_client, supplier, product):
    imp_id, lc_id = _full_close_setup(admin_client, supplier, product)
    admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    admin_client.post(f"/api/closure/importations/{imp_id}/close", json={"landed_cost_version_id": lc_id})
    r = admin_client.post(f"/api/closure/importations/{imp_id}/reopen", json={})
    assert r.status_code == 422


def test_reopen_with_reason(admin_client, supplier, product):
    imp_id, lc_id = _full_close_setup(admin_client, supplier, product)
    admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    admin_client.post(f"/api/closure/importations/{imp_id}/close", json={"landed_cost_version_id": lc_id})
    r = admin_client.post(
        f"/api/closure/importations/{imp_id}/reopen",
        json={"reason_code": "REOPEN_QTY_DISCREPANCY", "justification": "Corrigir qty"},
    )
    assert r.status_code == 200
    assert r.json()["current_status"] == "REOPENED"


def test_edit_blocked_when_closed(admin_client, supplier, product):
    imp_id, lc_id = _full_close_setup(admin_client, supplier, product)
    admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    admin_client.post(f"/api/closure/importations/{imp_id}/close", json={"landed_cost_version_id": lc_id})
    r = admin_client.post(
        f"/api/importations/{imp_id}/transition",
        json={"new_status": "ON_HOLD"},
    )
    assert r.status_code == 403


def test_closure_history(admin_client, supplier, product):
    imp_id, lc_id = _full_close_setup(admin_client, supplier, product)
    admin_client.post(f"/api/reconciliation/importations/{imp_id}/run")
    admin_client.post(f"/api/closure/importations/{imp_id}/close", json={"landed_cost_version_id": lc_id})
    hist = admin_client.get(f"/api/closure/importations/{imp_id}/history")
    assert len(hist.json()) == 1


def test_qty_reconciliation(admin_client, supplier, product):
    imp_id, _ = _full_close_setup(admin_client, supplier, product)
    recs = admin_client.post(f"/api/reconciliation/importations/{imp_id}/run").json()
    assert len(recs) >= 1


def test_demo_seed_16_scenarios(admin_client, db):
    r = admin_client.post("/api/demo/seed")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 16
    for key in [
        "ocean_simple",
        "air_simple",
        "modal_change",
        "three_invoices",
        "multi_invoices",
        "partial_payment",
        "fx_diff",
        "discount",
        "credit",
        "brazil_account",
        "qty_divergence",
        "cost_divergence",
        "close_ready",
        "close_with_variance",
        "reopen_candidate",
        "stock_entry",
    ]:
        assert key in data


def test_reconciliation_service(db, admin_client, supplier, product):
    imp_id, _ = _full_close_setup(admin_client, supplier, product)
    recs = run_reconciliations(db, imp_id)
    assert isinstance(recs, list)
    assert db.query(Reconciliation).filter(Reconciliation.importation_id == imp_id).count() >= 1
