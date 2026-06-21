"""Fases 7, 8 e 9 — testes críticos."""

import uuid
from decimal import Decimal

import pytest

from app.models import LandedCostVersion
from app.services.customs import CustomsValidationError, create_tax
from app.services.landed_cost import LandedCostError, create_landed_cost_version


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


@pytest.fixture()
def product_b(admin_client):
    r = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-B-{_uid()}", "description": "Produto B"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation(admin_client, supplier, product):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [{"product_id": product["id"], "quantity_ordered": 100, "unit_price_foreign": "10"}],
        },
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation_two_skus(admin_client, supplier, product, product_b):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-2SK-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [
                {"product_id": product["id"], "quantity_ordered": 100, "unit_price_foreign": "10"},
                {"product_id": product_b["id"], "quantity_ordered": 50, "unit_price_foreign": "20"},
            ],
        },
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation_item(admin_client, importation):
    items = admin_client.get(f"/api/importations/{importation['id']}/items")
    return items.json()[0]


def _upload_doc(client, entity_type, entity_id, content=b"pdf-content", doc_type="DI"):
    return client.post(
        "/api/documents/upload",
        data={
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "document_type": doc_type,
        },
        files={"file": ("doc.pdf", content, "application/pdf")},
    )


def _create_official_di(admin_client, importation_id, number=None):
    number = number or f"DI-{_uid()}"
    staging = admin_client.post(
        "/api/customs/documents",
        json={
            "importation_id": importation_id,
            "document_type": "DI",
            "document_number": number,
            "document_data_json": {"raw": "staging data", "items": []},
        },
    )
    assert staging.status_code == 201
    doc = staging.json()
    assert doc["status"] == "STAGING"
    assert doc["document_data_json"]["raw"] == "staging data"
    approved = admin_client.post(
        f"/api/customs/documents/{doc['id']}/approve",
        json={"official_data_json": {"number": number, "status": "cleared"}},
    )
    assert approved.status_code == 200
    official = approved.json()
    assert official["status"] == "OFFICIAL"
    assert official["is_valid"] is True
    assert official["official_data_json"]["number"] == number
    return official


def _tax_attachment(admin_client, importation_id):
    att = _upload_doc(admin_client, "importation_order", importation_id, doc_type="TAX_RECEIPT")
    assert att.status_code == 201
    return att.json()["id"]


# 1. DI/DUIMP registrada
def test_di_duimp_registered(admin_client, importation):
    doc = _create_official_di(admin_client, importation["id"])
    listed = admin_client.get(f"/api/customs/documents?importation_id={importation['id']}")
    assert any(d["id"] == doc["id"] for d in listed.json())


# 2. Imposto sem documento bloqueado
def test_tax_without_document_blocked(admin_client, importation, importation_item, db):
    doc = _create_official_di(admin_client, importation["id"])
    r = admin_client.post(
        "/api/customs/taxes",
        json={
            "importation_id": importation["id"],
            "customs_document_id": doc["id"],
            "tax_type": "II",
            "amount": "1000",
            "source_document_attachment_id": 999999,
        },
    )
    assert r.status_code == 400
    assert "comprobatório" in r.json()["detail"].lower() or "documento" in r.json()["detail"].lower()

    with pytest.raises(CustomsValidationError):
        create_tax(
            db,
            importation_id=importation["id"],
            customs_document_id=doc["id"],
            tax_type="II",
            amount=Decimal("100"),
            source_document_attachment_id=0,
            user_id=1,
        )


# 3. Despesa despachante sem evidência bloqueada
def test_customs_agent_expense_without_evidence_blocked(admin_client, importation):
    r = admin_client.post(
        "/api/finance/expenses",
        json={
            "importation_id": importation["id"],
            "expense_type": "CUSTOMS_AGENT",
            "amount": "500",
            "currency": "BRL",
        },
    )
    assert r.status_code == 400
    assert "evidência" in r.json()["detail"].lower() or "despachante" in r.json()["detail"].lower()


# 4. Nacionalização com DI/DUIMP
def test_nationalization_with_di(admin_client, importation, importation_item):
    doc = _create_official_di(admin_client, importation["id"])
    r = admin_client.post(
        "/api/stock/nationalizations",
        json={
            "importation_id": importation["id"],
            "customs_document_id": doc["id"],
            "items": [{"importation_item_id": importation_item["id"], "quantity_nationalized": 80}],
        },
    )
    assert r.status_code == 201
    assert r.json()["customs_document_id"] == doc["id"]


# 5. Entrada em estoque após nacionalização
def test_stock_entry_after_nationalization(admin_client, importation, importation_item):
    doc = _create_official_di(admin_client, importation["id"])
    nat = admin_client.post(
        "/api/stock/nationalizations",
        json={
            "importation_id": importation["id"],
            "customs_document_id": doc["id"],
            "items": [{"importation_item_id": importation_item["id"], "quantity_nationalized": 50}],
        },
    ).json()
    r = admin_client.post(
        "/api/stock/entries",
        json={
            "nationalization_id": nat["id"],
            "importation_item_id": importation_item["id"],
            "quantity_received": 40,
            "unit_cost_approved": "125.50",
        },
    )
    assert r.status_code == 201
    assert r.json()["quantity_received"] == 40


# 6. Estoque acima do nacionalizado bloqueado
def test_stock_exceeds_nationalized_blocked(admin_client, importation, importation_item):
    doc = _create_official_di(admin_client, importation["id"])
    nat = admin_client.post(
        "/api/stock/nationalizations",
        json={
            "importation_id": importation["id"],
            "customs_document_id": doc["id"],
            "items": [{"importation_item_id": importation_item["id"], "quantity_nationalized": 30}],
        },
    ).json()
    r = admin_client.post(
        "/api/stock/entries",
        json={
            "nationalization_id": nat["id"],
            "importation_item_id": importation_item["id"],
            "quantity_received": 50,
        },
    )
    assert r.status_code == 400
    assert "excede" in r.json()["detail"].lower() or "justificativa" in r.json()["detail"].lower()


# 7. Divergência de quantidade registrada
def test_quantity_discrepancy_recorded(admin_client, importation, importation_item):
    r = admin_client.post(
        "/api/stock/discrepancies",
        json={
            "importation_id": importation["id"],
            "importation_item_id": importation_item["id"],
            "stage_from": "ORDERED",
            "stage_to": "STOCKED",
            "expected_quantity": 100,
            "actual_quantity": 95,
            "reason": "Avaria no recebimento",
        },
    )
    assert r.status_code == 201
    assert r.json()["difference"] == -5


# 8. Landed cost inicial
def test_landed_cost_initial(admin_client, importation):
    r = admin_client.post(
        "/api/landed-cost/versions",
        json={
            "importation_id": importation["id"],
            "version_type": "INITIAL",
            "allocation_method": "VALUE",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["version_type"] == "INITIAL"
    assert data["version_number"] == 1
    assert data["is_current_version"] is True
    assert Decimal(data["total_cost"]) > 0


# 9. Landed cost revisado após mudança de modal
def test_landed_cost_revised_after_modal_change(admin_client, importation, db):
    admin_client.post(
        "/api/landed-cost/versions",
        json={
            "importation_id": importation["id"],
            "version_type": "INITIAL",
            "allocation_method": "VALUE",
        },
    )
    ship = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-LC-{_uid()}",
            "modal": "OCEAN",
            "bl_number": "BL-LC",
        },
    ).json()
    admin_client.post(
        f"/api/shipments/{ship['id']}/change-modal",
        json={"new_modal": "AIR", "reason_code": "MODAL_CHANGE_URGENCY", "comment": "Urgência"},
    )
    versions = admin_client.get(f"/api/landed-cost/importations/{importation['id']}/versions").json()
    types = [v["version_type"] for v in versions]
    assert "INITIAL" in types
    assert "REVISED" in types
    revised = next(v for v in versions if v["version_type"] == "REVISED")
    assert revised["trigger_event"] == "MODAL_CHANGE"


# 10. Landed cost final
def test_landed_cost_final(admin_client, importation):
    admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": importation["id"], "version_type": "INITIAL", "allocation_method": "VALUE"},
    )
    r = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": importation["id"], "version_type": "FINAL", "allocation_method": "VALUE"},
    )
    assert r.status_code == 201
    assert r.json()["version_type"] == "FINAL"


# 11. Versão anterior preservada
def test_landed_cost_previous_version_preserved(admin_client, importation, db):
    v1 = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": importation["id"], "version_type": "INITIAL", "allocation_method": "VALUE"},
    ).json()
    v2 = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": importation["id"], "version_type": "FINAL", "allocation_method": "VALUE"},
    ).json()
    assert v2["previous_version_id"] == v1["id"]
    old = db.query(LandedCostVersion).filter(LandedCostVersion.id == v1["id"]).first()
    assert old is not None
    assert old.is_current_version is False
    versions = admin_client.get(f"/api/landed-cost/importations/{importation['id']}/versions").json()
    assert len(versions) == 2


# 12. Rateio por SKU por valor
def test_allocation_by_value(admin_client, importation_two_skus):
    imp_id = importation_two_skus["id"]
    items = admin_client.get(f"/api/importations/{imp_id}/items").json()
    r = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": imp_id, "version_type": "INITIAL", "allocation_method": "VALUE"},
    )
    assert r.status_code == 201
    allocs = {a["importation_item_id"]: a for a in r.json()["allocations"]}
    assert len(allocs) == 2
    # item A: 100*10=1000, item B: 50*20=1000 → split 50/50
    a_id, b_id = items[0]["id"], items[1]["id"]
    assert Decimal(allocs[a_id]["allocated_amount"]) == Decimal(allocs[b_id]["allocated_amount"])


# 13. Rateio por SKU por quantidade
def test_allocation_by_quantity(admin_client, importation_two_skus):
    imp_id = importation_two_skus["id"]
    items = admin_client.get(f"/api/importations/{imp_id}/items").json()
    r = admin_client.post(
        "/api/landed-cost/versions",
        json={"importation_id": imp_id, "version_type": "INITIAL", "allocation_method": "QUANTITY"},
    )
    allocs = {a["importation_item_id"]: a for a in r.json()["allocations"]}
    a_id, b_id = items[0]["id"], items[1]["id"]
    ratio_a = Decimal(allocs[a_id]["allocated_amount"])
    ratio_b = Decimal(allocs[b_id]["allocated_amount"])
    # 100 vs 50 qty → 2:1
    assert abs(ratio_a / ratio_b - Decimal("2")) < Decimal("0.01")


# 14. Rateio manual sem motivo bloqueado
def test_manual_allocation_without_reason_blocked(admin_client, importation, importation_item):
    r = admin_client.post(
        "/api/landed-cost/versions",
        json={
            "importation_id": importation["id"],
            "version_type": "INITIAL",
            "allocation_method": "MANUAL",
            "manual_allocations": {str(importation_item["id"]): "1000"},
        },
    )
    assert r.status_code == 400
    assert "motivo" in r.json()["detail"].lower()


def test_manual_allocation_without_reason_blocked_service(db, importation_item, importation):
    with pytest.raises(LandedCostError, match="motivo"):
        create_landed_cost_version(
            db,
            importation_id=importation["id"],
            version_type="INITIAL",
            allocation_method="MANUAL",
            user_id=1,
            manual_allocations={importation_item["id"]: Decimal("1000")},
        )
