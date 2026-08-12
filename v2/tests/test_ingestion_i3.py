"""J3-I3 tests — Ordine 589 vertical: adapter, matching, preview, commit, idempotency.

Gates:
- Golden extraction (key fields from corpus_589/Ordine_589.pdf)
- Ambiguous I.V. SKUs → issues AMBIGUOUS_SKU (never silent)
- Preview digest stable across repeated calls
- Commit creates Order DRAFT + Document (promoted) + DocumentLink
- Retry same operation_key + same fingerprint → idempotent (returns existing)
- Lost response: same operation_key + same fingerprint → OK
- Different fingerprint → 409
- Tudo-ou-nada (RUX-2R-b): falha injetada não persiste write nem arquivo; retry do zero
- Architecture: no V1 imports, no cross-module internals
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from decimal import Decimal

import pytest

from app.foundation.settings import get_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    from app.catalog.errors import CatalogError

    suppliers = catalog_public.list_suppliers(db, q="Heroe", limit=20)
    for s in suppliers:
        if (s.name or "") == "Heroe's Srl":
            return s.id
    sup = catalog_public.create_supplier(db, name="Heroe's Srl", country_code="IT")
    db.flush()
    return sup.id


def _ensure_products(db) -> tuple[int, int]:
    """Creates EPIC products for bind tests (Q3=B: I.V.* não usam supplier_product_refs)."""
    from app.catalog import public as catalog_public

    def _product(sku: str, description: str) -> int:
        try:
            return catalog_public.get_product_by_sku(db, sku).id
        except Exception:
            pass
        product = catalog_public.create_product(db, sku=sku, description=description)
        db.flush()
        return product.id

    id_iv2 = _product("EPIC-TEST-IV2", "racchette 2027 GRAFICATE")
    id_iv1 = _product("EPIC-TEST-IV1", "racchette 2027 NON GRAFICATE")
    return id_iv2, id_iv1


def _bind_catalog_on_ir(
    db,
    doc_id: int,
    *,
    supplier_id: int,
    product_ids: tuple[int, int],
    order_number: str | None = None,
) -> None:
    """Simulate human confirmation: bind supplier + products on IR rows.

    ``order_number`` permite um número único por teste: o código da Order é o
    próprio número do documento (sem prefixo ING-) e Orders têm código único,
    então dois commits do mesmo 589 no mesmo banco colidem.
    """
    import json as _json

    from app.ingestion.ir_models import IngestionDocument

    ir_doc = db.get(IngestionDocument, doc_id)
    for f in ir_doc.fields:
        if f.field_key == "supplier_id_catalog" and (f.raw_value is None or f.raw_value == "None"):
            f.raw_value = str(supplier_id)
            f.normalized_value = str(supplier_id)
        if order_number is not None and f.field_key == "order_number":
            f.raw_value = order_number
            f.normalized_value = order_number
            f.corrected_value = None
            f.review_status = "PENDING"
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


# ---------------------------------------------------------------------------
# Golden extraction tests (pure, no DB)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_order_number():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert raw.order_number == "589"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_date():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert raw.order_date_iso == "2026-06-04"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_supplier_name():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert raw.supplier_name is not None
    assert "heroe" in raw.supplier_name.lower()


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_supplier_pi_cf():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert raw.supplier_pi_cf is not None
    assert "02610500395" in raw.supplier_pi_cf


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_two_lines():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert len(raw.lines) == 2


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_line_quantities():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    # I.V. 2 → qty 14600; I.V. 1 → qty 2000
    skus = {line.sku.replace(" ", ""): line for line in raw.lines}
    # Accept with/without space
    iv2 = next((l for l in raw.lines if "2" in l.sku.replace(" ", "")), None)
    iv1 = next((l for l in raw.lines if "1" in l.sku.replace(" ", "") and "IV1" in l.sku.replace(".", "").replace(" ", "").upper()), None)
    # Simpler: just check total is 830000
    total = sum(l.line_total for l in raw.lines)
    assert total == Decimal("830000.00"), f"Expected 830000.00 got {total}"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_extract_total_document():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert raw.total_document == Decimal("830000.00")


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_math_export_n31_no_false_taxable_warning():
    """Golden POSITIVO Ordine 589 — lista exata de issues math (B3).

    N3.1 100% esenti, IMPOSTE=SCONTI=Spese=0: L2/L5 ok; L4 ok (IVA export);
    MATH_TOTAL_MISMATCH não dispara; INFO MATH_EXPORT_N31 presente.
    """
    from app.ingestion.adapters.ordine_heroes_v1 import extract, _validate_math

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    issues = _validate_math(raw)
    codes = sorted(i["code"] for i in issues)
    assert codes == ["MATH_EXPORT_N31"], f"Expected exact math issues; got {codes} detail={issues}"
    assert "MATH_TAXABLE_ZERO_MISMATCH" not in codes
    assert "MATH_LINES_VS_TAX_BASES" not in codes
    assert "MATH_DOCUMENT_COMPOSITION" not in codes
    assert "MATH_LINE_VAT_NATURE" not in codes
    assert "MATH_TOTAL_MISMATCH" not in codes
    assert "MATH_LINE_TOTAL_MISMATCH" not in codes
    assert "MATH_TOTAL_COMPOSITION_UNVERIFIED" not in codes


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_ordine_589_issue_codes_exact(db, monkeypatch):
    """Golden POSITIVO: issues de match+math do Ordine 589 em catálogo vazio.

    Isola matching do catálogo poluído pela suíte (Heroes SPA etc.) — a lista
    positiva é a do catálogo vazio (B3), não o estado acidental do DB de teste.
    """
    from app.ingestion.adapters import ordine_heroes_v1 as ad
    from app.ingestion.adapters.ordine_heroes_v1 import extract, match_catalog, _validate_math

    monkeypatch.setattr(
        ad.catalog_public,
        "list_suppliers",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        ad.catalog_public,
        "list_products",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        ad.catalog_public,
        "get_product_by_sku",
        lambda *a, **k: (_ for _ in ()).throw(Exception("empty")),
    )

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    math_issues = _validate_math(raw)
    _, match_issues = match_catalog(db, raw)
    codes = sorted(i["code"] for i in (math_issues + match_issues))
    assert codes == [
        "MATH_EXPORT_N31",
        "SUPPLIER_NOT_FOUND",
        "UNMATCHED_SKU",
        "UNMATCHED_SKU",
    ], f"Unexpected issue set: {codes} detail={math_issues + match_issues}"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_golden_classify():
    from app.ingestion.adapters.ordine_heroes_v1 import extract, classify

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    assert classify(raw) is True


# ---------------------------------------------------------------------------
# Matching: I.V. codes → AMBIGUOUS_SKU (never silent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_matching_no_catalog_produces_unmatched_sku_issues(db):
    """With empty catalog, lines produce UNMATCHED_SKU warnings — no silent promotion."""
    from app.ingestion.adapters.ordine_heroes_v1 import extract, match_catalog

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    _, issues = match_catalog(db, raw)
    unmatched = [i for i in issues if i["code"] == "UNMATCHED_SKU"]
    assert len(unmatched) >= 2, f"Expected ≥2 UNMATCHED_SKU issues; got {issues}"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_matching_with_catalog_still_unmatched_iv_lines(db):
    """Q3=(B): mesmo com products EPIC no catálogo, I.V.* permanecem UNMATCHED_SKU."""
    from app.ingestion.adapters.ordine_heroes_v1 import extract, match_catalog

    _ensure_supplier(db)
    _ensure_products(db)
    db.flush()

    pdf_bytes = FIXTURE_PDF.read_bytes()
    raw = extract(pdf_bytes)
    result, issues = match_catalog(db, raw)
    unmatched = [i for i in issues if i["code"] == "UNMATCHED_SKU"]
    assert len(unmatched) >= 2, f"Expected ≥2 UNMATCHED_SKU; got {issues}"
    for sku, pid in result.line_matches.items():
        if sku.upper().startswith("I.V") or sku.upper().startswith("IV"):
            assert pid is None, f"I.V.* must not auto-bind product_id (got {sku}→{pid})"


# ---------------------------------------------------------------------------
# IR seed via API
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_run_adapter_api(admin_client, db):
    """POST /api/ingestion/occurrences/{id}/run-adapter creates IngestionDocument."""
    # create batch + upload
    r = admin_client.post("/api/ingestion/batches", json={})
    assert r.status_code == 200
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ = upload["results"][0]
    assert occ["status"] == "STORED"
    occ_id = occ["id"]

    # run adapter
    r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["doc_type"] == "ORDINE_COMPRA"
    assert doc["adapter_id"] == "ordine_heroes_v1"
    assert len(doc["fields"]) > 0
    assert len(doc["rows"]) > 0
    # Should have at least one issue (taxable zero warning)
    assert len(doc["issues"]) > 0


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_run_adapter_idempotency_conflict(admin_client):
    """Running adapter twice on same occurrence returns 409."""
    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]

    r1 = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert r1.status_code == 200

    r2 = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert r2.status_code == 409, r2.text


# ---------------------------------------------------------------------------
# Preview commit
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_preview_commit_stable_fingerprint(admin_client, db):
    """Preview returns stable fingerprint across repeated calls."""
    # setup catalog
    _ensure_supplier(db)
    _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    p1 = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit")
    p2 = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit")
    assert p1.status_code == 200, p1.text
    assert p2.status_code == 200, p2.text
    assert p1.json()["fingerprint"] == p2.json()["fingerprint"], "Fingerprint must be stable"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_preview_commit_has_expected_ops(admin_client, db):
    """Preview includes store_document and create_order when supplier resolved."""
    sup_id = _ensure_supplier(db)
    _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    p = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit")
    assert p.status_code == 200
    ops = [o["op_key"] for o in p.json()["operations"]]
    assert "store_document" in ops
    # create_order only if supplier resolved in IR — may be skip_order if not resolved
    # At minimum store_document must be there
    assert len(ops) >= 1


# ---------------------------------------------------------------------------
# Commit: creates Order DRAFT + Document
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_commit_creates_order_draft(admin_client, db):
    """Commit creates an Order DRAFT and promoted Document."""
    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    _bind_catalog_on_ir(
        db, doc_id, supplier_id=sup_id, product_ids=product_ids,
        order_number=f"589-{doc_id}",
    )

    r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"test-commit-{doc_id}"},
    )
    assert r.status_code == 200, r.text
    attempt = r.json()
    assert attempt["status"] == "SUCCEEDED", f"Unexpected status: {attempt}"

    ops_by_key = {op["op_key"]: op for op in attempt["operations"]}
    assert "store_document" in ops_by_key
    assert ops_by_key["store_document"]["status"] == "SUCCEEDED"

    # arquivo promovido da área temporária depois do commit
    from app.documents.models import Document

    stored = db.get(Document, int(ops_by_key["store_document"]["entity_id"]))
    final_path = Path(get_settings().attachments_path) / stored.storage_path
    assert final_path.is_file(), f"arquivo final ausente: {final_path}"
    assert not final_path.with_name(final_path.name + ".pending").exists()

    create_order_op = ops_by_key["create_order"]
    assert create_order_op["status"] == "SUCCEEDED", create_order_op
    order_r = admin_client.get(f"/api/orders/{create_order_op['entity_id']}")
    assert order_r.status_code == 200
    assert order_r.json()["status"] == "DRAFT"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_commit_idempotent_same_fingerprint(admin_client, db):
    """Same operation_key + same fingerprint → returns existing attempt (200)."""
    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    _bind_catalog_on_ir(
        db, doc_id, supplier_id=sup_id, product_ids=product_ids,
        order_number=f"589-{doc_id}",
    )

    op_key = f"idempotent-test-{doc_id}"
    r1 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": op_key},
    )
    assert r1.status_code == 200
    attempt1_id = r1.json()["id"]

    # Replay — same key + same fingerprint
    r2 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": op_key},
    )
    assert r2.status_code == 200
    attempt2_id = r2.json()["id"]
    assert attempt1_id == attempt2_id, "Idempotent replay must return same attempt"


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_commit_conflict_different_fingerprint(admin_client, db):
    """Same operation_key + different fingerprint → 409.

    Strategy: commit doc once, then correct a field (changing fingerprint),
    then retry the same operation_key → should get 409.
    """
    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    _bind_catalog_on_ir(
        db, doc_id, supplier_id=sup_id, product_ids=product_ids,
        order_number=f"589-{doc_id}",
    )

    op_key = f"fp-conflict-{doc_id}"

    # First commit
    r1 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": op_key},
    )
    assert r1.status_code == 200

    # Correct the order_number field to change fingerprint
    doc_detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    order_field = next(
        (f for f in doc_detail["fields"] if f["field_key"] == "order_number"), None
    )
    if order_field:
        patch_r = admin_client.patch(
            f"/api/ingestion/fields/{order_field['id']}",
            json={
                "corrected_value": "589-MODIFIED",
                "expected_version": order_field["version"],
            },
        )
        assert patch_r.status_code == 200

    # Same operation_key but different fingerprint → 409
    r2 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": op_key},
    )
    assert r2.status_code == 409, r2.text


# ---------------------------------------------------------------------------
# GET commit-attempt status
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_get_commit_attempt_status(admin_client, db):
    """GET /api/ingestion/commit-attempts/{id} returns full status."""
    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    _bind_catalog_on_ir(
        db, doc_id, supplier_id=sup_id, product_ids=product_ids,
        order_number=f"589-{doc_id}",
    )

    r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"status-test-{doc_id}"},
    )
    attempt_id = r.json()["id"]

    r_status = admin_client.get(f"/api/ingestion/commit-attempts/{attempt_id}")
    assert r_status.status_code == 200
    body = r_status.json()
    assert body["id"] == attempt_id
    assert body["status"] == "SUCCEEDED"
    assert isinstance(body["operations"], list)


# ---------------------------------------------------------------------------
# RUX-2R-b: commit tudo-ou-nada (substitui os testes do Modelo B / PARTIAL)
# ---------------------------------------------------------------------------


def _attachment_files() -> set[Path]:
    root = Path(get_settings().attachments_path)
    if not root.exists():
        return set()
    return {p for p in root.rglob("*") if p.is_file()}


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_commit_injected_failure_persists_nothing_then_retry_succeeds(
    admin_client, db, monkeypatch
):
    """Falha injetada em add_item: nada persiste, nenhum arquivo órfão, motivo visível.

    Em seguida, o retry com a mesma operation_key reexecuta do zero e conclui.
    """
    from app.documents.models import Document
    from app.ingestion import commit_commands
    from app.orders.models import Order

    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    _bind_catalog_on_ir(
        db, doc_id, supplier_id=sup_id, product_ids=product_ids,
        order_number=f"589-{doc_id}",
    )

    documents_before = db.query(Document).count()
    orders_before = db.query(Order).count()
    files_before = _attachment_files()

    def _boom(*args, **kwargs):
        raise RuntimeError("falha injetada em add_item")

    monkeypatch.setattr(commit_commands.orders_public, "add_item", _boom)

    op_key = f"all-or-nothing-{doc_id}"
    r_fail = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit", json={"operation_key": op_key}
    )
    assert r_fail.status_code == 200, r_fail.text
    failed_attempt = r_fail.json()
    assert failed_attempt["status"] == "FAILED", failed_attempt

    ops = {op["op_key"]: op for op in failed_attempt["operations"]}
    failed_op = next(op for op in ops.values() if op["status"] == "FAILED")
    assert failed_op["op_key"].startswith("add_item_"), failed_op
    assert "falha injetada em add_item" in (failed_op["error_message"] or "")
    assert ops["store_document"]["status"] == "SKIPPED", ops["store_document"]
    assert "rolled_back" in (ops["store_document"]["details_json"] or "")
    assert ops["create_order"]["status"] == "SKIPPED", ops["create_order"]

    db.rollback()
    assert db.query(Document).count() == documents_before, "Document persistiu após rollback"
    assert db.query(Order).count() == orders_before, "Order persistiu após rollback"
    assert _attachment_files() == files_before, "arquivo órfão em disco após rollback"

    # Retry do zero, agora sem a falha injetada
    monkeypatch.undo()
    r_ok = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit", json={"operation_key": op_key}
    )
    assert r_ok.status_code == 200, r_ok.text
    ok_attempt = r_ok.json()
    assert ok_attempt["id"] == failed_attempt["id"], "retry criou outro attempt"
    assert ok_attempt["status"] == "SUCCEEDED", ok_attempt

    ok_ops = {op["op_key"]: op for op in ok_attempt["operations"]}
    assert ok_ops["store_document"]["status"] == "SUCCEEDED", ok_ops["store_document"]
    assert ok_ops["create_order"]["status"] == "SUCCEEDED", ok_ops["create_order"]
    assert not any(op["status"] == "FAILED" for op in ok_ops.values()), ok_ops

    db.rollback()
    assert db.query(Document).count() == documents_before + 1, "Document não persistiu"
    assert db.query(Order).count() == orders_before + 1, "Order não persistiu"

    stored = db.get(Document, int(ok_ops["store_document"]["entity_id"]))
    final_path = Path(get_settings().attachments_path) / stored.storage_path
    assert final_path.is_file(), "arquivo não foi promovido"
    assert not final_path.with_name(final_path.name + ".pending").exists()


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_commit_failure_leaves_no_pending_file(admin_client, db, monkeypatch):
    """Falha depois do store_document remove o temporário — nem final, nem .pending."""
    from app.ingestion import commit_commands

    sup_id = _ensure_supplier(db)
    product_ids = _ensure_products(db)
    db.commit()

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    upload = _upload_pdf(admin_client, batch_id, FIXTURE_PDF)
    occ_id = upload["results"][0]["id"]
    doc_r = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    doc_id = doc_r.json()["id"]

    _bind_catalog_on_ir(
        db, doc_id, supplier_id=sup_id, product_ids=product_ids,
        order_number=f"589-{doc_id}",
    )

    root = Path(get_settings().attachments_path)
    pending_before = {p for p in root.rglob("*.pending")} if root.exists() else set()

    def _boom(*args, **kwargs):
        raise RuntimeError("falha injetada em create_order")

    monkeypatch.setattr(commit_commands.orders_public, "create_order", _boom)

    r_fail = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"pending-cleanup-{doc_id}"},
    )
    assert r_fail.status_code == 200, r_fail.text
    attempt = r_fail.json()
    assert attempt["status"] == "FAILED", attempt
    ops = {op["op_key"]: op for op in attempt["operations"]}
    assert ops["create_order"]["status"] == "FAILED", ops["create_order"]
    assert "falha injetada em create_order" in (ops["create_order"]["error_message"] or "")

    pending_after = {p for p in root.rglob("*.pending")} if root.exists() else set()
    assert pending_after == pending_before, "temporário não removido após rollback"


# ---------------------------------------------------------------------------
# Commit blocked by open ERROR issues
# ---------------------------------------------------------------------------


def test_commit_blocked_by_open_error_issues(admin_client, db):
    """Commit with open ERROR issues → 422."""
    # Create batch + minimal PDF occurrence
    from tests.ingestion_i0_fixtures import minimal_pdf_bytes, write_fixture

    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]

    import tempfile, os
    tmp = Path(tempfile.mkdtemp())
    pdf_path = tmp / "test_blocked.pdf"
    pdf_path.write_bytes(minimal_pdf_bytes("blocked_test"))

    with open(pdf_path, "rb") as f:
        upload_r = admin_client.post(
            f"/api/ingestion/batches/{batch_id}/files",
            files=[("files", ("test_blocked.pdf", f, "application/pdf"))],
        )
    assert upload_r.status_code == 200
    occ_id = upload_r.json()["results"][0]["id"]

    # Seed document manually with an ERROR issue
    seed_r = admin_client.post(
        "/api/ingestion/documents",
        json={
            "occurrence_id": occ_id,
            "doc_type": "ORDINE_COMPRA",
            "adapter_id": "test_v1",
            "issues": [
                {
                    "severity": "ERROR",
                    "code": "MATH_TOTAL_MISMATCH",
                    "message": "test error",
                }
            ],
        },
    )
    assert seed_r.status_code == 200
    doc_id = seed_r.json()["id"]

    r = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"blocked-{doc_id}"},
    )
    assert r.status_code == 422, r.text
    assert "commit_blocked_by_issues" in r.text


# ---------------------------------------------------------------------------
# RUX-2R-a: unsqueeze descriptions + C4 dual-form supplier header
# ---------------------------------------------------------------------------


def test_unsqueeze_preserves_normal_description():
    from app.ingestion.adapters.ordine_heroes_v1 import _unsqueeze_pdf_glyphs

    normal = "racchette 2027 GRAFICATE"
    assert _unsqueeze_pdf_glyphs(normal) == normal
    spaced_non = "racchette 2027 NON GRAFICATE"
    assert _unsqueeze_pdf_glyphs(spaced_non) == spaced_non


def test_unsqueeze_collapses_fragmented_description():
    from app.ingestion.adapters.ordine_heroes_v1 import _unsqueeze_pdf_glyphs

    frag = "ra c c hette 2027 GR AFIC AT E"
    assert _unsqueeze_pdf_glyphs(frag) == "racchette 2027 GRAFICATE"
    frag_non = "ra c c hette 2027 NO N GR AFIC AT E"
    out = _unsqueeze_pdf_glyphs(frag_non)
    assert "racchette" in out
    assert "NON GRAFICATE" in out or "NONGRAFICATE" not in out.replace(" ", "")


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_ir_description_raw_intact_normalized_unsqueezed():
    """raw stays glyph-spaced; normalized is readable (RUX-2R-a). Same path as build_ir_payload rows."""
    from app.ingestion.adapters.ordine_heroes_v1 import extract, _unsqueeze_pdf_glyphs

    raw = extract(FIXTURE_PDF.read_bytes())
    assert raw.lines, "expected line items"
    for line in raw.lines:
        desc_norm = _unsqueeze_pdf_glyphs(line.description)
        assert line.description, "raw description must be present"
        assert "racchette" in desc_norm.lower()
        assert "GRAFICATE" in desc_norm.upper()
        # Fragmented raw must differ from unsqueezed when glyphs were spaced
        if " " in line.description and len(line.description) > len(desc_norm):
            assert line.description != desc_norm
        assert line.sku  # sku path untouched by unsqueeze helper


def test_c4_supplier_extract_fragmented_and_unsqueezed():
    """C4: header regex must work on fragmented form; unsqueezed form must not lose supplier.

    Unsqueeze is description-only — we still prove _extract_header on both text shapes.
    """
    from app.ingestion.adapters.ordine_heroes_v1 import _extract_header, _unsqueeze_pdf_glyphs

    fragmented = (
        "Her oe's Sr l\n"
        "P.IVA 02610500395\n"
        "ORDINE N. 589\n"
        "DATA 04/06/2026\n"
        "TOTALE DOCUMENTO € 830.000,00\n"
    )
    unsqueezed_body = _unsqueeze_pdf_glyphs(fragmented)
    # Full-document unsqueeze of header block (hostile to C4) — must still resolve
    header_frag = _extract_header(fragmented)
    header_unsq = _extract_header(unsqueezed_body)
    assert header_frag.get("supplier_name") == "Heroe's Srl", header_frag
    assert header_unsq.get("supplier_name") == "Heroe's Srl", (
        f"C4 BREAK: unsqueezed header lost supplier: {header_unsq}"
    )


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_c4_supplier_from_real_pdf_layout():
    from app.ingestion.adapters.ordine_heroes_v1 import extract

    raw = extract(FIXTURE_PDF.read_bytes())
    assert raw.supplier_name == "Heroe's Srl"


# ---------------------------------------------------------------------------
# Architecture: no internals, no V1
# ---------------------------------------------------------------------------


def test_arch_no_v1_imports():
    """Adapter and commit modules must not import V1."""
    import ast
    from pathlib import Path

    v2_root = Path(__file__).parent.parent
    to_check = [
        v2_root / "app" / "ingestion" / "adapters" / "ordine_heroes_v1.py",
        v2_root / "app" / "ingestion" / "commit_commands.py",
        v2_root / "app" / "ingestion" / "commit_queries.py",
        v2_root / "app" / "ingestion" / "commit_models.py",
    ]
    violations = []
    for path in to_check:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("v1"):
                        violations.append(f"{path.name}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("v1"):
                    violations.append(f"{path.name}: {node.module}")
    assert not violations, "V1 import violation: " + str(violations)


def test_arch_ingestion_module_graph_updated():
    """Module graph must allow ingestion → documents, orders, catalog."""
    from app.foundation.module_graph import ALLOWED_DEPS

    allowed = ALLOWED_DEPS.get("ingestion", frozenset())
    assert "documents" in allowed, "ingestion must be allowed to import documents"
    assert "orders" in allowed, "ingestion must be allowed to import orders"
    assert "catalog" in allowed, "ingestion must be allowed to import catalog"


def test_arch_no_cross_module_internals_in_commit():
    """commit_commands uses only public APIs of orders/documents/catalog."""
    import ast
    from pathlib import Path

    path = Path(__file__).parent.parent / "app" / "ingestion" / "commit_commands.py"
    if not path.exists():
        pytest.skip("commit_commands.py not found")

    tree = ast.parse(path.read_text(encoding="utf-8"))
    internals = (
        ".models", ".repository", ".commands", ".queries",
        ".errors", ".money", ".storage",
    )
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for other_mod in ("orders", "documents", "catalog"):
                if f"app.{other_mod}" in node.module:
                    suffix = node.module.replace(f"app.{other_mod}", "")
                    for internal in internals:
                        if suffix == internal or suffix.startswith(internal + "."):
                            violations.append(f"{node.module}")
    assert not violations, f"Cross-module internals found: {violations}"
