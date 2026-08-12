"""RUX-3F I3 — qty/linha corrigida grava na Order; header total_document não corrompe.

Prova:
1. PATCH cells_json quantity → commit → OrderItem.quantity == valor corrigido
2. PATCH total_document absurdo → commit → total comercial = Σ qty×price (ignora header)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.orders.models import Order, OrderItem
from app.orders.queries import compute_totals

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


def _first_line_row(detail: dict) -> dict:
    rows = detail.get("rows") or []
    assert rows, "IR sem linhas"
    return rows[0]


@pytest.mark.skipif(not ADAPTER_AVAILABLE, reason="corpus_589/Ordine_589.pdf not present")
def test_rux3f_i3_patched_qty_and_absurd_header_total_commit(admin_client, db):
    doc_id = _seed_ordine(admin_client, db)
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()

    code = f"589-RUX3F-I3-{doc_id}"
    put = admin_client.put(
        f"/api/ingestion/documents/{doc_id}/order-code",
        json={
            "order_code": code,
            "expected_version": detail["version"],
            "reason": "rux3f-i3",
        },
    )
    assert put.status_code == 200, put.text

    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    row = _first_line_row(detail)
    cells = json.loads(row["cells_json"] or "{}")
    assert "quantity" in cells

    # 1) corrige qty da 1ª linha (14600 → 14601) e recalcula line_total
    price = Decimal(str(cells.get("unit_price", {}).get("normalized") or "50"))
    new_qty = Decimal("14601")
    cells["quantity"] = {
        "raw": cells["quantity"].get("raw", "14600"),
        "normalized": "14601",
    }
    cells["line_total"] = {
        "raw": cells.get("line_total", {}).get("raw"),
        "normalized": str((new_qty * price).quantize(Decimal("0.01"))),
    }
    patch_row = admin_client.patch(
        f"/api/ingestion/rows/{row['id']}",
        json={
            "cells_json": json.dumps(cells, ensure_ascii=False),
            "expected_version": row["version"],
            "reason": "rux3f-i3-qty",
        },
    )
    assert patch_row.status_code == 200, patch_row.text

    # 2) total_document absurdo — não deve contaminar Order
    detail = admin_client.get(f"/api/ingestion/documents/{doc_id}").json()
    total_f = next(f for f in detail["fields"] if f["field_key"] == "total_document")
    patch_hdr = admin_client.patch(
        f"/api/ingestion/fields/{total_f['id']}",
        json={
            "corrected_value": "999999999.99",
            "expected_version": total_f["version"],
            "reason": "rux3f-i3-absurd-header",
        },
    )
    assert patch_hdr.status_code == 200, patch_hdr.text

    commit = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit",
        json={"operation_key": f"rux3f-i3-{doc_id}"},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["status"] == "SUCCEEDED"

    order = db.query(Order).filter(Order.code == code).one()
    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id)
        .order_by(OrderItem.id)
        .all()
    )
    assert len(items) == 2

    qty_values = sorted(i.quantity for i in items)
    assert Decimal("2000") in qty_values
    assert Decimal("14601") in qty_values, (
        f"qty corrigida não gravou na OrderItem: {[str(i.quantity) for i in items]}"
    )

    # Total comercial = Σ qty×price — NÃO 999999999.99 do header
    totals = compute_totals(items)
    commercial = totals.commercial_total
    assert commercial is not None
    expected = (Decimal("14601") * price) + (Decimal("2000") * price)
    assert abs(commercial - expected) < Decimal("0.02")
    assert commercial != Decimal("999999999.99")
    assert commercial < Decimal("1000000")  # ~830k+50, longe do absurdo
