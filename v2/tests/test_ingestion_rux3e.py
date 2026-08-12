"""RUX-3E — DELETE IR, colisão de código, code≠external_ref, edição, reject bloqueado.

Gates:
- DELETE 204 quando não houve create_order SUCCEEDED
- DELETE 409 quando houve create_order SUCCEEDED
- Audit (audit_log) sobrevive ao DELETE
- commit_order_code_exists 409 + details
- order_code editável; external_ref permanece número do documento
- PATCH review REJECTED bloqueado se já criou pedido
- correção de campo / linha (contrato de edição)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.audit.models import AuditLog
from app.orders.models import Order

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
    for row in ir.rows or []:
        try:
            cells = json.loads(row.cells_json or "{}")
        except Exception:
            cells = {}
        cells["product_id_catalog"] = {"raw": None, "normalized": None}
        row.cells_json = json.dumps(cells, ensure_ascii=False)
    db.commit()


def _seed_ordine(admin_client, db) -> int:
    _archive_heroes_suppliers(db)
    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert doc_r.status_code == 200, doc_r.text
    doc_id = doc_r.json()["id"]
    _set_pending_create_supplier(db, doc_id, name="Heroe's Srl", code="02610500395")
    return doc_id


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3e_delete_without_create_order_and_audit_survives(admin_client, db):
    doc_id = _seed_ordine(admin_client, db)

    # gera ao menos um evento de audit (seed / adapter)
    before = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ingestion_document",
            AuditLog.entity_id == str(doc_id),
        )
        .count()
    )
    assert before >= 1

    # edição de campo (contrato D8) — sem create_order
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    currency = next(f for f in detail["fields"] if f["field_key"] == "currency")
    patch = admin_client.patch(
        f"/api/ingestion/fields/{currency['id']}",
        json={
            "corrected_value": "EUR",
            "expected_version": currency["version"],
            "reason": "rux3e_edit",
        },
    )
    assert patch.status_code == 200, patch.text

    # edição de linha
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    row0 = detail["rows"][0]
    cells = json.loads(row0["cells_json"])
    cells["quantity"] = {"raw": cells.get("quantity", {}).get("raw"), "normalized": "14601"}
    row_patch = admin_client.patch(
        f"/api/ingestion/rows/{row0['id']}",
        json={
            "cells_json": json.dumps(cells),
            "expected_version": row0["version"],
            "reason": "rux3e_row_edit",
        },
    )
    assert row_patch.status_code == 200, row_patch.text

    deleted = admin_client.delete(f"/api/ingestion/documents/{doc_id}")
    assert deleted.status_code == 204, deleted.text

    gone = admin_client.get(f"/api/ingestion/documents/{doc_id}")
    assert gone.status_code == 404

    # Audit separado do ledger IR — eventos sobrevivem (incl. hard_delete)
    db.expire_all()
    surviving = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ingestion_document",
            AuditLog.entity_id == str(doc_id),
        )
        .all()
    )
    actions = {a.action for a in surviving}
    assert "document_hard_deleted" in actions
    assert len(surviving) >= before


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3e_delete_blocked_after_create_order(admin_client, db):
    doc_id = _seed_ordine(admin_client, db)
    # código único para não colidir com outros testes paralelos
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    put = admin_client.put(
        f"/api/ingestion/documents/{doc_id}/order-code",
        json={
            "order_code": f"589-RUX3E-DEL-{doc_id}",
            "expected_version": detail["version"],
            "reason": "rux3e",
        },
    )
    assert put.status_code == 200, put.text

    key = f"rux3e-del-block-{doc_id}"
    commit = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": key},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["status"] == "SUCCEEDED"

    blocked = admin_client.delete(f"/api/ingestion/documents/{doc_id}")
    assert blocked.status_code == 409, blocked.text
    body = blocked.json()
    assert body.get("error") == "document_delete_blocked"

    # reject também bloqueado
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    assert detail.get("created_order_id") is not None
    assert detail["review_status"] != "REJECTED"
    reject = admin_client.patch(
        f"/api/ingestion/documents/{doc_id}/review-status",
        json={"review_status": "REJECTED", "expected_version": detail["version"]},
    )
    assert reject.status_code == 409, reject.text
    assert reject.json().get("error") == "document_reject_blocked"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3e_order_code_collision_and_external_ref_stable(admin_client, db):
    doc_a = _seed_ordine(admin_client, db)
    detail_a = admin_client.get(f"/api/ingestion/documents/{doc_a}").json()
    code_a = f"589-RUX3E-A-{doc_a}"
    put_a = admin_client.put(
        f"/api/ingestion/documents/{doc_a}/order-code",
        json={"order_code": code_a, "expected_version": detail_a["version"], "reason": "rux3e"},
    )
    assert put_a.status_code == 200, put_a.text

    commit_a = admin_client.post(
        f"/api/ingestion/documents/{doc_a}/commit",
        json={"operation_key": f"rux3e-a-{doc_a}"},
    )
    assert commit_a.status_code == 200, commit_a.text
    order_id = None
    for op in commit_a.json().get("operations") or []:
        if op.get("op_key") == "create_order" and op.get("entity_id"):
            order_id = int(op["entity_id"])
    assert order_id is not None
    order = db.get(Order, order_id)
    assert order is not None
    assert order.code == code_a
    assert order.external_ref == "589"

    # segundo doc: colisão no mesmo code
    doc_b = _seed_ordine(admin_client, db)
    detail_b = admin_client.get(f"/api/ingestion/documents/{doc_b}").json()
    put_b = admin_client.put(
        f"/api/ingestion/documents/{doc_b}/order-code",
        json={"order_code": code_a, "expected_version": detail_b["version"], "reason": "rux3e"},
    )
    assert put_b.status_code == 200, put_b.text

    collide = admin_client.post(
        f"/api/ingestion/documents/{doc_b}/commit",
        json={"operation_key": f"rux3e-b-collide-{doc_b}"},
    )
    assert collide.status_code == 409, collide.text
    err = collide.json()
    assert err.get("error") == "commit_order_code_exists"
    assert err.get("details", {}).get("order_id") == order_id
    assert err.get("details", {}).get("order_code") == code_a

    # escape: outro code, external_ref permanece 589
    detail_b = admin_client.get(f"/api/ingestion/documents/{doc_b}").json()
    code_b = f"589-RUX3E-B-{doc_b}"
    put_b2 = admin_client.put(
        f"/api/ingestion/documents/{doc_b}/order-code",
        json={"order_code": code_b, "expected_version": detail_b["version"], "reason": "rux3e"},
    )
    assert put_b2.status_code == 200, put_b2.text

    # order_number do PDF permanece 589 (não editado)
    on = next(f for f in detail_b["fields"] if f["field_key"] == "order_number")
    assert (on.get("normalized_value") or on.get("raw_value")) == "589"

    commit_b = admin_client.post(
        f"/api/ingestion/documents/{doc_b}/commit",
        json={"operation_key": f"rux3e-b-ok-{doc_b}"},
    )
    assert commit_b.status_code == 200, commit_b.text
    order_b_id = None
    for op in commit_b.json().get("operations") or []:
        if op.get("op_key") == "create_order" and op.get("entity_id"):
            order_b_id = int(op["entity_id"])
    assert order_b_id is not None
    db.expire_all()
    order_b = db.get(Order, order_b_id)
    assert order_b is not None
    assert order_b.code == code_b
    assert order_b.external_ref == "589"
