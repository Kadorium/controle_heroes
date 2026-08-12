"""RUX-3B-2a — Ordine commit → COMMITMENT + create_supplier (backend only).

Gates:
- Ordine 589, catálogo sem Heroes: create_supplier + Order DRAFT + 2 COMMITMENT
  com unidade (PZ) + Document promovido + link
- Preview: create_supplier → store_document → create_order → add_item×2 → link
- Reimport: matcher encontra fornecedor; sem pending create
- Falha injetada: zero write, zero órfão, motivo no ledger
- create_invoice → 'nenhuma linha faturável'
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.foundation.settings import get_settings

FIXTURE_PDF = (
    Path(__file__).parent
    / "fixtures"
    / "ingestion"
    / "corpus_589"
    / "Ordine_589.pdf"
)

ADAPTER_AVAILABLE = FIXTURE_PDF.is_file()


def _upload_pdf(client, batch_id: int, pdf_path: Path) -> dict:
    with open(pdf_path, "rb") as f:
        r = client.post(
            f"/api/ingestion/batches/{batch_id}/files",
            files=[("files", (pdf_path.name, f, "application/pdf"))],
        )
    assert r.status_code == 200, r.text
    return r.json()


def _archive_heroes_suppliers(db) -> None:
    """Garante catálogo 'vazio' para o Heroes do 589 (epic_v2_test only)."""
    from app.catalog.models import Supplier

    for s in db.query(Supplier).all():
        name = (s.name or "").lower()
        code = (s.code or "").replace(" ", "")
        if "heroe" in name or "02610500395" in code:
            s.name = f"ARCHIVED-{s.id}-{s.name}"
            if s.code:
                s.code = f"ARCH-{s.id}-{s.code}"[:64]
    db.commit()


def _set_pending_create_supplier(db, doc_id: int, *, name: str, code: str | None = None) -> None:
    from app.ingestion.ir_models import IngestionDocument

    ir = db.get(IngestionDocument, doc_id)
    assert ir is not None
    payload = json.dumps(
        {"name": name, "code": code, "country_code": "IT"},
        ensure_ascii=False,
    )
    for f in ir.fields:
        if f.field_key == "supplier_id_catalog":
            f.raw_value = None
            f.normalized_value = None
            f.corrected_value = None
            f.review_status = "PENDING"
        if f.field_key == "pending_create_supplier":
            f.corrected_value = payload
            f.review_status = "CORRECTED"
        if f.field_key == "order_number":
            # código Order único por documento
            f.raw_value = f"589-{doc_id}"
            f.normalized_value = f"589-{doc_id}"
            f.corrected_value = None
            f.review_status = "PENDING"
    # Sem product_id nas linhas → COMMITMENT
    for row in ir.rows or []:
        try:
            cells = json.loads(row.cells_json or "{}")
        except Exception:
            cells = {}
        cells["product_id_catalog"] = {"raw": None, "normalized": None}
        row.cells_json = json.dumps(cells, ensure_ascii=False)
    db.commit()


def _attachment_files() -> set[Path]:
    root = Path(get_settings().attachments_path)
    if not root.exists():
        return set()
    return {p for p in root.rglob("*") if p.is_file()}


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3b2a_empty_catalog_commit_commitment_with_unit(admin_client, db):
    """Gate: catálogo sem Heroes + intent create_supplier → 2 COMMITMENT com PZ."""
    _archive_heroes_suppliers(db)

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert doc_r.status_code == 200, doc_r.text
    doc_id = doc_r.json()["id"]

    _set_pending_create_supplier(
        db, doc_id, name="Heroe's Srl", code="02610500395"
    )

    preview = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit")
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_commit"] is True, body
    op_keys = [o["op_key"] for o in body["operations"]]
    assert op_keys[:1] == ["create_supplier"]
    assert "store_document" in op_keys
    assert "create_order" in op_keys
    add_items = [o for o in body["operations"] if o["op_key"].startswith("add_item_")]
    assert len(add_items) == 2
    for op in add_items:
        assert op["params"]["line_kind"] == "COMMITMENT"
        assert op["params"]["unit"] == "PZ"
        assert op["params"]["product_id"] is None
    # Ordem canônica: create_supplier → store → create_order → add_item* → link
    assert op_keys.index("create_supplier") < op_keys.index("store_document")
    assert op_keys.index("store_document") < op_keys.index("create_order")
    assert op_keys.index("create_order") < op_keys.index(add_items[0]["op_key"])
    assert op_keys.index(add_items[-1]["op_key"]) < op_keys.index("link_document")

    r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"rux3b2a-empty-{doc_id}"},
    )
    assert r.status_code == 200, r.text
    attempt = r.json()
    assert attempt["status"] == "SUCCEEDED", attempt

    ops = {op["op_key"]: op for op in attempt["operations"]}
    assert ops["create_supplier"]["status"] == "SUCCEEDED"
    supplier_id = int(ops["create_supplier"]["entity_id"])
    assert ops["create_order"]["status"] == "SUCCEEDED"
    order_id = int(ops["create_order"]["entity_id"])

    order_r = admin_client.get(f"/api/orders/{order_id}")
    assert order_r.status_code == 200
    order = order_r.json()
    assert order["status"] == "DRAFT"
    assert order["supplier_id"] == supplier_id
    assert len(order["items"]) == 2
    for item in order["items"]:
        assert item["line_kind"] == "COMMITMENT"
        assert item["product_id"] is None
        assert item["unit"] == "PZ"
        assert item["external_code"]
        assert item["description_snapshot"] or item.get("description")

    # Document promovido
    from app.documents.models import Document

    stored = db.get(Document, int(ops["store_document"]["entity_id"]))
    final_path = Path(get_settings().attachments_path) / stored.storage_path
    assert final_path.is_file()
    assert not final_path.with_name(final_path.name + ".pending").exists()

    # confirm + create_invoice → nenhuma linha faturável
    conf = admin_client.post(
        f"/api/orders/{order_id}/confirm",
        json={"expected_version": order["version"]},
    )
    assert conf.status_code == 200, conf.text
    inv = admin_client.post(
        f"/api/orders/{order_id}/invoices",
        json={
            "invoice_number": f"INV-RUX3B2A-{order_id}",
            "invoice_type": "FINAL",
        },
    )
    assert inv.status_code == 400, inv.text
    assert "nenhuma linha faturável" in inv.text

    for item in order["items"]:
        assert item["description_snapshot"]
        assert item["unit"] == "PZ"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3b2a_reimport_matcher_finds_supplier(admin_client, db):
    """Após create, reimport do 589: matcher acha fornecedor; sem create_supplier."""
    from app.catalog import public as catalog_public

    # Garante Heroes presente (pode ter sido criado no teste anterior ou aqui).
    existing = catalog_public.list_suppliers(db, q="Heroe's Srl", limit=10)
    exact = [s for s in existing if (s.name or "").strip() == "Heroe's Srl"]
    if not exact:
        catalog_public.create_supplier(
            db, name="Heroe's Srl", code="02610500395", country_code="IT"
        )
        db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert doc_r.status_code == 200, doc_r.text
    doc_id = doc_r.json()["id"]

    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    supplier_field = next(
        f for f in detail["fields"] if f["field_key"] == "supplier_id_catalog"
    )
    effective = supplier_field.get("corrected_value") or supplier_field.get(
        "normalized_value"
    ) or supplier_field.get("raw_value")
    assert effective and str(effective).isdigit(), (
        f"matcher deveria resolver supplier; got {supplier_field}"
    )

    pending = next(
        f for f in detail["fields"] if f["field_key"] == "pending_create_supplier"
    )
    pending_eff = pending.get("corrected_value") or pending.get("normalized_value")
    assert not pending_eff, "sem intent create_supplier após match"

    preview = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit")
    assert preview.status_code == 200
    op_keys = [o["op_key"] for o in preview.json()["operations"]]
    assert "create_supplier" not in op_keys
    assert preview.json()["can_commit"] is True


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3b2a_supplier_exists_link_required_409(admin_client, db):
    """409 distinto: intent create com fornecedor já existente → vincular."""
    from app.catalog import public as catalog_public

    name = "Heroe's Srl"
    existing = catalog_public.list_suppliers(db, q=name, limit=10)
    if not any((s.name or "").strip() == name for s in existing):
        catalog_public.create_supplier(
            db, name=name, code="02610500395", country_code="IT"
        )
        db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    # Força intent create mesmo com Heroes no catálogo (simula matcher miss + intent).
    _set_pending_create_supplier(db, doc_id, name=name, code="02610500395")

    r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"rux3b2a-link-{doc_id}"},
    )
    assert r.status_code == 409, r.text
    assert "vincular" in r.text.lower() or "commit_supplier_link_required" in r.text


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3b2a_injected_failure_zero_writes(admin_client, db, monkeypatch):
    """Falha no meio: zero domínio, zero órfão, motivo no ledger."""
    from app.ingestion import commit_commands
    from app.orders.models import Order

    _archive_heroes_suppliers(db)

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]
    _set_pending_create_supplier(
        db, doc_id, name="Heroe's Srl", code="02610500395"
    )

    before_orders = {o.id for o in db.query(Order).all()}
    before_files = _attachment_files()

    def _boom(*a, **k):
        raise RuntimeError("falha injetada em add_item RUX-3B-2a")

    monkeypatch.setattr(commit_commands.orders_public, "add_item", _boom)

    r_fail = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"rux3b2a-fail-{doc_id}"},
    )
    assert r_fail.status_code == 200, r_fail.text
    failed = r_fail.json()
    assert failed["status"] == "FAILED", failed
    failed_op = next(op for op in failed["operations"] if op["status"] == "FAILED")
    assert failed_op["op_key"].startswith("add_item_")
    assert "falha injetada" in (failed_op["error_message"] or "")

    db.expire_all()
    after_orders = {o.id for o in db.query(Order).all()}
    assert after_orders == before_orders

    from app.catalog import public as catalog_public

    heroes = [
        s
        for s in catalog_public.list_suppliers(db, q="Heroe's Srl", limit=20)
        if (s.name or "").strip() == "Heroe's Srl"
    ]
    assert heroes == [], "create_supplier não deve persistir após falha"

    after_files = _attachment_files()
    new_files = after_files - before_files
    assert not any(p.suffix == ".pending" or p.name.endswith(".pending") for p in new_files)
    # Sem promoção: nenhum arquivo novo sem .pending
    promoted_new = [
        p for p in new_files if not p.name.endswith(".pending")
    ]
    assert promoted_new == [], f"arquivo órfão promovido: {promoted_new}"
