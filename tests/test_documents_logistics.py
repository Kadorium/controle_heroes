"""Fases 5 e 6 — testes críticos."""

import io
import uuid
import zipfile

import pytest

from app.config import get_settings
from app.models import DocumentAttachment, ModalChangeLog, RawImportFile, ReviewQueueItem, StagingImportRow
from app.services.attachments import backup_attachments_to_zip


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
        json={"name": f"Heroes {_uid()}", "country": "CN", "currency_default": "EUR"},
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
def importation_item(admin_client, importation):
    items = admin_client.get(f"/api/importations/{importation['id']}/items")
    return items.json()[0]


@pytest.fixture()
def invoice(admin_client, importation):
    r = admin_client.post(
        "/api/invoices",
        json={
            "importation_id": importation["id"],
            "invoice_type": "PROFORMA",
            "invoice_number": f"INV-{_uid()}",
            "amount": "5000",
            "currency": "EUR",
        },
    )
    assert r.status_code == 201
    return r.json()


def _upload_doc(client, entity_type, entity_id, content=b"pdf-content", document_key=None, doc_type="PROFORMA"):
    data = {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "document_type": doc_type,
    }
    if document_key:
        data["document_key"] = document_key
    return client.post(
        "/api/documents/upload",
        data=data,
        files={"file": ("doc.pdf", content, "application/pdf")},
    )


# 1. Upload de documento
def test_upload_document(admin_client, importation):
    r = _upload_doc(admin_client, "importation_order", importation["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["file_hash"]
    assert data["version"] == 1
    assert data["is_current_version"] is True


# 2. Substituição preservando versão anterior
def test_document_replace_preserves_previous_version(admin_client, importation, db):
    v1 = _upload_doc(admin_client, "importation_order", importation["id"], b"v1").json()
    v2 = _upload_doc(
        admin_client,
        "importation_order",
        importation["id"],
        b"v2-content-different",
        document_key=v1["document_key"],
    )
    assert v2.status_code == 201
    v2_data = v2.json()
    assert v2_data["version"] == 2
    versions = admin_client.get(f"/api/documents/key/{v1['document_key']}/versions")
    assert len(versions.json()) == 2
    old = db.query(DocumentAttachment).filter(DocumentAttachment.id == v1["id"]).first()
    assert old.is_current_version is False
    settings = get_settings()
    assert (settings.attachments_path / old.storage_path).exists()
    assert (settings.attachments_path / v2_data["storage_path"]).exists()


# 3. Documento vinculado a invoice
def test_document_linked_to_invoice(admin_client, invoice):
    r = _upload_doc(admin_client, "invoice", invoice["id"], doc_type="PROFORMA")
    assert r.status_code == 201
    listed = admin_client.get(f"/api/documents?entity_type=invoice&entity_id={invoice['id']}")
    assert len(listed.json()) == 1


# 4. Documento vinculado a importação
def test_document_linked_to_importation(admin_client, importation):
    r = _upload_doc(admin_client, "importation_order", importation["id"])
    assert r.status_code == 201
    listed = admin_client.get(
        f"/api/documents?entity_type=importation_order&entity_id={importation['id']}"
    )
    assert len(listed.json()) >= 1


# 5. Backup inclui anexos
def test_backup_includes_attachments(admin_client, importation):
    _upload_doc(admin_client, "importation_order", importation["id"], b"backup-test-content")
    zip_path = backup_attachments_to_zip()
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert any("backup-test-content" in n or n.endswith(".pdf") or "v1_" in n for n in names)


HEROES_CSV_HEADER = "PO,SKU,Description,Qty,UnitPrice,Supplier\n"


def _heroes_csv(*rows: str) -> bytes:
    return (HEROES_CSV_HEADER + "\n".join(rows)).encode("utf-8")


# 6. Importação Heroes com campo vazio não vira zero
def test_heroes_empty_field_not_zero(admin_client, db):
    csv = _heroes_csv("PO-H1,SKU-H1,Item,,10.00,Heroes")
    r = admin_client.post(
        "/api/imports/heroes/upload",
        files={"file": ("heroes.csv", csv, "text/csv")},
    )
    assert r.status_code == 201
    staging = admin_client.get(f"/api/imports/staging?raw_file_id={r.json()['id']}")
    row = staging.json()[0]
    assert row["parsed_data_json"]["quantity"] is None


# 7. Linha ambígua cai em review_queue
def test_ambiguous_line_goes_to_review_queue(admin_client):
    csv = _heroes_csv(
        "PO-DUP,SKU-DUP,Item,10,5.00,Heroes",
        "PO-DUP,SKU-DUP,Item,20,5.00,Heroes",
    )
    r = admin_client.post(
        "/api/imports/heroes/upload",
        files={"file": ("heroes.csv", csv, "text/csv")},
    )
    assert r.status_code == 201
    queue = admin_client.get("/api/imports/review-queue")
    assert queue.status_code == 200
    assert len(queue.json()) >= 1
    assert any("duplicada" in q["reason"].lower() for q in queue.json())


# 8. Importação marítima simples
def test_simple_ocean_shipment(admin_client, importation):
    r = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-OCEAN-{_uid()}",
            "modal": "OCEAN",
            "bl_number": "BL123456",
            "container_number": "CONT001",
        },
    )
    assert r.status_code == 201
    assert r.json()["modal"] == "OCEAN"
    assert r.json()["bl_number"] == "BL123456"


# 9. Importação aérea simples
def test_simple_air_shipment(admin_client, importation):
    r = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-AIR-{_uid()}",
            "modal": "AIR",
            "awb_number": "AWB789",
        },
    )
    assert r.status_code == 201
    assert r.json()["modal"] == "AIR"
    assert r.json()["awb_number"] == "AWB789"


# 10. Dois embarques modais diferentes
def test_two_shipments_different_modals(admin_client, importation):
    s1 = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH1-{_uid()}",
            "modal": "OCEAN",
            "bl_number": "BL1",
        },
    )
    s2 = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH2-{_uid()}",
            "modal": "AIR",
            "awb_number": "AWB1",
        },
    )
    assert s1.status_code == 201 and s2.status_code == 201
    listed = admin_client.get(f"/api/shipments?importation_id={importation['id']}")
    modals = {s["modal"] for s in listed.json()}
    assert modals == {"OCEAN", "AIR"}


# 11. Alteração marítimo → aéreo com motivo
def test_ocean_to_air_modal_change_with_reason(admin_client, importation, db):
    ship = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-MOD-{_uid()}",
            "modal": "OCEAN",
            "bl_number": "BL-OLD",
        },
    ).json()
    r = admin_client.post(
        f"/api/shipments/{ship['id']}/change-modal",
        json={
            "new_modal": "AIR",
            "reason_code": "MODAL_CHANGE_URGENCY",
            "comment": "Urgência de entrega",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["modal"] == "AIR"
    assert data["modal_previous"] == "OCEAN"
    history = admin_client.get(f"/api/shipments/{ship['id']}/modal-history")
    assert len(history.json()) == 1
    assert history.json()[0]["from_modal"] == "OCEAN"


# 12. Alteração de modal sem motivo bloqueada
def test_modal_change_without_reason_blocked(admin_client, importation):
    ship = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-BLOCK-{_uid()}",
            "modal": "OCEAN",
        },
    ).json()
    r = admin_client.post(
        f"/api/shipments/{ship['id']}/change-modal",
        json={"new_modal": "AIR"},
    )
    assert r.status_code == 400


# 13. Modal anterior permanece visível
def test_previous_modal_remains_visible(admin_client, importation):
    ship = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-PREV-{_uid()}",
            "modal": "OCEAN",
        },
    ).json()
    admin_client.post(
        f"/api/shipments/{ship['id']}/change-modal",
        json={"new_modal": "AIR", "comment": "Mudança por custo"},
    )
    detail = admin_client.get(f"/api/shipments/{ship['id']}")
    assert detail.json()["modal"] == "AIR"
    assert detail.json()["modal_previous"] == "OCEAN"
    logs = admin_client.get(f"/api/shipments/{ship['id']}/modal-history")
    assert logs.json()[0]["from_modal"] == "OCEAN"


# Qty shipped cap
def test_quantity_shipped_exceeds_ordered_blocked(admin_client, importation, importation_item):
    ship = admin_client.post(
        "/api/shipments",
        json={
            "importation_id": importation["id"],
            "shipment_number": f"SH-QTY-{_uid()}",
            "modal": "OCEAN",
        },
    ).json()
    r = admin_client.post(
        f"/api/shipments/{ship['id']}/items",
        json={"importation_item_id": importation_item["id"], "quantity_shipped": 150},
    )
    assert r.status_code == 400


# Raw file preserved
def test_raw_import_file_preserved(admin_client, db):
    csv = _heroes_csv("PO-R1,SKU-R1,Item,5,1.00,Heroes")
    r = admin_client.post(
        "/api/imports/heroes/upload",
        files={"file": ("heroes.csv", csv, "text/csv")},
    )
    raw_id = r.json()["id"]
    raw = db.query(RawImportFile).filter(RawImportFile.id == raw_id).first()
    settings = get_settings()
    assert (settings.imports_path / raw.storage_path).exists()


# Approve clean staging row
def test_approve_staging_creates_importation(admin_client):
    csv = _heroes_csv(f"PO-APP-{_uid()},SKU-APP-{_uid()},Item,5,10.00,Heroes")
    raw = admin_client.post(
        "/api/imports/heroes/upload",
        files={"file": ("heroes.csv", csv, "text/csv")},
    ).json()
    staging = admin_client.get(f"/api/imports/staging?raw_file_id={raw['id']}").json()[0]
    assert staging["review_reason"] is None
    approved = admin_client.post(f"/api/imports/staging/{staging['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "MERGED"


# UI smoke endpoints
def test_ui_api_smoke_docs_logistics(admin_client, importation):
    assert admin_client.get("/api/documents").status_code == 200
    assert admin_client.get("/api/imports/review-queue").status_code == 200
    assert admin_client.get(f"/api/shipments?importation_id={importation['id']}").status_code == 200


# F5-010 documento obrigatório bloqueia transição
def test_missing_document_blocks_transition(admin_client, importation):
    r = admin_client.post(
        f"/api/importations/{importation['id']}/transition",
        json={"new_status": "PROFORMA_RECEIVED"},
    )
    assert r.status_code == 400
    _upload_doc(admin_client, "importation_order", importation["id"], doc_type="PROFORMA")
    r2 = admin_client.post(
        f"/api/importations/{importation['id']}/transition",
        json={"new_status": "PROFORMA_RECEIVED"},
    )
    assert r2.status_code == 200
