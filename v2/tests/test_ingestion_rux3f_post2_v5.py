"""RUX-3F-POST-3 — MATH_LINE_EDIT_DIVERGENCE (WARNING, não bloqueia).

Casos:
1. PATCH qty que quebra math → WARNING aparece
2. commit → SUCCEEDED
3. PATCH qty de volta ao original → issue some
4. PATCH qty coerente (qty×price = line_total PDF) → sem issue
"""

from __future__ import annotations

import json
from decimal import Decimal
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
CODE = "MATH_LINE_EDIT_DIVERGENCE"


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


def _open_edit_divergence(detail: dict) -> list[dict]:
    return [
        i
        for i in (detail.get("issues") or [])
        if i.get("status") == "OPEN"
        and i.get("code") == CODE
        and i.get("severity") == "WARNING"
    ]


def _patch_qty(admin_client, row: dict, qty: str, *, keep_line_total: bool = True) -> dict:
    cells = json.loads(row["cells_json"] or "{}")
    line_total_before = cells.get("line_total")
    cells["quantity"] = {
        "raw": cells.get("quantity", {}).get("raw", qty),
        "normalized": qty,
    }
    if keep_line_total and line_total_before is not None:
        cells["line_total"] = line_total_before
    elif not keep_line_total:
        price = Decimal(str(cells.get("unit_price", {}).get("normalized") or "0"))
        total = (Decimal(qty) * price).quantize(Decimal("0.01"))
        cells["line_total"] = {
            "raw": (line_total_before or {}).get("raw") if isinstance(line_total_before, dict) else None,
            "normalized": str(total),
        }
    r = admin_client.patch(
        f"/api/ingestion/rows/{row['id']}",
        json={
            "cells_json": json.dumps(cells, ensure_ascii=False),
            "expected_version": row["version"],
            "reason": "rux3f-post3-v5",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3f_post3_v5_math_line_edit_divergence_warning(admin_client, db):
    doc_id = _seed_ordine(admin_client, db)
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    assert _open_edit_divergence(detail) == []

    code = f"589-RUX3F-POST3-{doc_id}"
    put = admin_client.put(
        f"/api/ingestion/documents/{doc_id}/order-code",
        json={
            "order_code": code,
            "expected_version": detail["version"],
            "reason": "rux3f-post3",
        },
    )
    assert put.status_code == 200, put.text

    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    row = (detail.get("rows") or [])[0]
    cells0 = json.loads(row["cells_json"] or "{}")
    qty_orig = str(cells0["quantity"]["normalized"])
    price = Decimal(str(cells0["unit_price"]["normalized"]))
    pdf_total = Decimal(
        str(cells0["line_total"].get("raw") or cells0["line_total"]["normalized"])
    )

    # 1) PATCH qty quebra math → WARNING
    _patch_qty(admin_client, row, "99999", keep_line_total=True)
    after_break = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    warns = _open_edit_divergence(after_break)
    assert len(warns) == 1, after_break.get("issues")
    assert "99999" in warns[0]["message"]
    assert "difere do total de linha impresso" in warns[0]["message"]
    assert not any(
        i.get("status") == "OPEN" and i.get("code") == CODE and i.get("severity") == "ERROR"
        for i in after_break.get("issues") or []
    )

    # 2) commit NÃO bloqueado
    commit = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"rux3f-post3-commit-{doc_id}"},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["status"] == "SUCCEEDED"

    # Novo doc para casos 3–4 (commit consome o anterior)
    doc_id2 = _seed_ordine(admin_client, db)
    detail2 = admin_client.get(f"/api/ingestion/documents/{doc_id2}").json()
    row2 = (detail2.get("rows") or [])[0]
    cells2 = json.loads(row2["cells_json"] or "{}")
    qty_orig2 = str(cells2["quantity"]["normalized"])
    price2 = Decimal(str(cells2["unit_price"]["normalized"]))
    pdf_total2 = Decimal(
        str(cells2["line_total"].get("raw") or cells2["line_total"]["normalized"])
    )

    # 3) break → revert → issue some
    _patch_qty(admin_client, row2, "99999", keep_line_total=True)
    broken = admin_client.get(f"/api/ingestion/documents/{doc_id2}").json()
    assert len(_open_edit_divergence(broken)) == 1
    row2b = next(r for r in broken["rows"] if r["id"] == row2["id"])
    _patch_qty(admin_client, row2b, qty_orig2, keep_line_total=True)
    reverted = admin_client.get(f"/api/ingestion/documents/{doc_id2}").json()
    assert _open_edit_divergence(reverted) == [], [
        (i.get("code"), i.get("status"), i.get("message")) for i in reverted.get("issues") or []
    ]

    # 4) qty coerente com PDF (único valor que qty×price = pdf_total com price fixo)
    coherent_qty = (pdf_total2 / price2).quantize(Decimal("1"))
    # garantir coerência exacta
    assert abs(coherent_qty * price2 - pdf_total2) < Decimal("0.02")
    row2c = next(r for r in reverted["rows"] if r["id"] == row2["id"])
    # forçar um desvio e depois coerente via keep_line_total
    _patch_qty(admin_client, row2c, "99999", keep_line_total=True)
    mid = admin_client.get(f"/api/ingestion/documents/{doc_id2}").json()
    assert len(_open_edit_divergence(mid)) == 1
    row2d = next(r for r in mid["rows"] if r["id"] == row2["id"])
    _patch_qty(admin_client, row2d, str(int(coherent_qty)), keep_line_total=True)
    coherent = admin_client.get(f"/api/ingestion/documents/{doc_id2}").json()
    assert _open_edit_divergence(coherent) == []
