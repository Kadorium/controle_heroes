"""RUX-2R / H-EXEC-05 — reextract/replace Ordine IR."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def _ensure_supplier(db) -> int:
    from app.catalog import public as catalog_public

    suppliers = catalog_public.list_suppliers(db, q="Heroe", limit=5)
    if suppliers:
        return suppliers[0].id
    sup = catalog_public.create_supplier(db, name="Heroe's Srl", country_code="IT")
    db.flush()
    return sup.id


def _ensure_products(db) -> tuple[int, int]:
    from app.catalog import public as catalog_public

    supplier_id = _ensure_supplier(db)

    def _product_with_ref(external: str, description: str) -> int:
        refs = catalog_public.find_supplier_product_refs(
            db,
            supplier_id=supplier_id,
            code_kind="SUPPLIER_CLASS",
            external_code=external,
            active_only=True,
            limit=1,
        )
        if refs:
            return refs[0].product_id
        product = catalog_public.create_product(db, sku=None, description=description)
        db.flush()
        catalog_public.upsert_supplier_product_ref(
            db,
            supplier_id=supplier_id,
            product_id=product.id,
            code_kind="SUPPLIER_CLASS",
            match_mode="SUGGEST",
            external_code=external,
            external_description=description,
        )
        db.flush()
        return product.id

    id_iv2 = _product_with_ref("I.V. 2", "racchette 2027 GRAFICATE")
    id_iv1 = _product_with_ref("I.V. 1", "racchette 2027 NON GRAFICATE")
    return id_iv2, id_iv1


def _bind_catalog_on_ir(db, doc_id: int, *, supplier_id: int, product_ids: tuple[int, int]) -> None:
    import json as _json

    from app.ingestion.ir_models import IngestionDocument

    ir_doc = db.get(IngestionDocument, doc_id)
    for f in ir_doc.fields:
        if f.field_key == "supplier_id_catalog" and (f.raw_value is None or f.raw_value == "None"):
            f.raw_value = str(supplier_id)
            f.normalized_value = str(supplier_id)
    id_by_index = {0: product_ids[0], 1: product_ids[1]}
    for row in ir_doc.rows or []:
        pid = id_by_index.get(row.row_index)
        if pid is None:
            continue
        try:
            cells = _json.loads(row.cells_json or "{}")
        except Exception:
            cells = {}
        cells["product_id_catalog"] = {"raw": str(pid), "normalized": str(pid)}
        row.cells_json = _json.dumps(cells, ensure_ascii=False)
    db.commit()


def _seed_ordine_doc(admin_client, db) -> int:
    r = admin_client.post("/api/ingestion/batches", json={})
    assert r.status_code == 200
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert doc_r.status_code == 200, doc_r.text
    return doc_r.json()["id"]


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_reextract_blocked_after_create_order_succeeded(admin_client, db):
    """Reextract bloqueado quando create_order já SUCCEEDED (mesmo attempt PARTIAL)."""
    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    doc_id = _seed_ordine_doc(admin_client, db)
    _bind_catalog_on_ir(db, doc_id, supplier_id=sup_id, product_ids=product_ids)

    commit_r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"reextract-block-{doc_id}"},
    )
    assert commit_r.status_code == 200, commit_r.text
    ops = {op["op_key"]: op for op in commit_r.json()["operations"]}
    assert ops.get("create_order", {}).get("status") == "SUCCEEDED"

    reextract_r = admin_client.post(f"/api/ingestion/documents/{doc_id}/reextract")
    assert reextract_r.status_code == 409, reextract_r.text
    assert reextract_r.json()["error"] == "reextract_blocked"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_reextract_supersedes_old_issues_and_produces_fresh_on_empty_catalog(admin_client, db):
    """Issues OPEN antigas viram RESOLVED; reextract gera novas issues no catálogo vazio."""
    from app.ingestion.ir_models import IngestionDocument, IngestionIssue

    doc_id = _seed_ordine_doc(admin_client, db)

    issue_r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/issues",
        json={
            "severity": "WARNING",
            "code": "MANUAL_TEST_ISSUE",
            "message": "issue manual para supersede",
        },
    )
    assert issue_r.status_code == 200

    doc_before = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    open_before = [i for i in doc_before["issues"] if i["status"] == "OPEN"]
    assert len(open_before) >= 1

    reextract_r = admin_client.post(f"/api/ingestion/documents/{doc_id}/reextract")
    assert reextract_r.status_code == 200, reextract_r.text
    body = reextract_r.json()
    assert body["version"] > doc_before["version"]

    ir_doc = db.get(IngestionDocument, doc_id)
    resolved_manual = [
        i
        for i in ir_doc.issues
        if i.code == "MANUAL_TEST_ISSUE" and i.status == "RESOLVED"
    ]
    assert len(resolved_manual) == 1

    open_after = [i for i in body["issues"] if i["status"] == "OPEN"]
    assert len(open_after) >= 1
    # empty catalog → UNMATCHED_SKU or SUGGESTED_SKU_MATCH on reextract
    open_codes = {i["code"] for i in open_after}
    assert open_codes & {"UNMATCHED_SKU", "SUGGESTED_SKU_MATCH"}

    still_open_manual = db.query(IngestionIssue).filter(
        IngestionIssue.document_id == doc_id,
        IngestionIssue.code == "MANUAL_TEST_ISSUE",
        IngestionIssue.status == "OPEN",
    ).count()
    assert still_open_manual == 0
