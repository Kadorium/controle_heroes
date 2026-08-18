"""C6 — Packing List Detail: extract layout, Order 0/1/N, fill Shipment PLANNED."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ingestion.adapters.packing_list_detail_v1 import extract
from app.ingestion.packing_line_match import is_packaging_ncm, plan_packing_lines
from app.ingestion.packing_order_candidates import suggest_packing_orders

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingestion"
PDF_328 = FIXTURES / "corpus_328" / "PackingList_328.pdf"
PDF_202 = FIXTURES / "corpus_202" / "PackingList_202.pdf"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _field(key: str, value: str | None, review_status: str = "APPROVED"):
    return SimpleNamespace(
        field_key=key,
        review_status=review_status,
        corrected_value=None,
        normalized_value=value,
        raw_value=value,
    )


def _carton_row(index: int, *, ncm: str, desc: str, qty: str = "10", carton_no: str | None = None):
    cells = {
        "pallet_no": {"raw": "1", "normalized": "1"},
        "carton_no": {"raw": carton_no or str(index + 1), "normalized": carton_no or str(index + 1)},
        "items_per_ctn": {"raw": qty, "normalized": qty},
        "ncm": {"raw": ncm, "normalized": ncm},
        "description": {"raw": desc, "normalized": desc},
        "dimensions": {"raw": "61,00x65,00x36,00", "normalized": "61,00x65,00x36,00"},
        "unit_net_weight_kg": {"raw": "0.32", "normalized": "0.32"},
        "unit_gross_weight_kg": {"raw": "2.40", "normalized": "2.40"},
        "total_net_weight_kg": {"raw": "3.20", "normalized": "3.20"},
        "total_gross_weight_kg": {"raw": "24.00", "normalized": "24.00"},
    }
    return SimpleNamespace(
        row_index=index,
        section_key="cartons",
        cells_json=json.dumps(cells),
    )


def _doc(*, supplier_id: int | None, ncm: str = "95069900", desc: str = "RACCHETTA BT", qty: str = "50"):
    fields = [
        _field("currency", "EUR"),
        _field("document_number", "328"),
        _field("supplier_name", "Heroe's Srl"),
        _field("supplier_id_catalog", str(supplier_id) if supplier_id else None),
    ]
    n = int(Decimal(qty))
    per = 10
    rows = []
    remaining = n
    i = 0
    while remaining > 0:
        take = min(per, remaining)
        rows.append(_carton_row(i, ncm=ncm, desc=desc, qty=str(take)))
        remaining -= take
        i += 1
    return SimpleNamespace(id=1, fields=fields, rows=rows, issues=[], doc_type="PACKING_LIST_DETAIL")


def _supplier_product(db, sku: str, *, name: str | None = None):
    from app.catalog import public as catalog_public

    s = catalog_public.create_supplier(db, name=name or f"C6 Sup {_uid()}", country_code="IT")
    p = catalog_public.create_product(db, sku=sku, description="RACCHETTA BT 2026 STARLIGHT")
    db.flush()
    return s, p


def _confirmed_order(db, supplier_id: int, product_id: int, sku: str, *, qty: str, price: str = "106.66"):
    from app.orders import public as orders_public

    order = orders_public.create_order(
        db,
        code=f"C6-{_uid()}",
        supplier_id=supplier_id,
        created_by_actor_id="test-actor",
        currency="EUR",
        source_system="MANUAL",
    )
    db.flush()
    o = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        product_id=product_id,
        quantity=qty,
        unit_price=price,
        unit="PZ",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    return orders_public.get_order(db, o.id)


@pytest.mark.skipif(not PDF_328.is_file(), reason="PackingList_328.pdf absent")
def test_extract_328_layout_cartons():
    raw = extract(PDF_328.read_bytes())
    assert raw.document_number == "328"
    assert len(raw.carton_rows) == 5
    assert sum(c.items_per_ctn for c in raw.carton_rows) == 50
    assert {c.ncm for c in raw.carton_rows} == {"95069900"}
    assert not is_packaging_ncm("95069900")


@pytest.mark.skipif(not PDF_202.is_file(), reason="PackingList_202.pdf absent")
def test_extract_202_layout_cartons():
    raw = extract(PDF_202.read_bytes())
    assert raw.document_number == "202"
    assert len(raw.carton_rows) == 100
    descs = {c.description for c in raw.carton_rows}
    assert len(descs) == 7


def test_4819_is_packaging():
    assert is_packaging_ncm("48191000")
    assert is_packaging_ncm("4819 10")
    assert not is_packaging_ncm("95069900")


def test_packing_zero_candidates(db):
    sku = f"C6Z-{_uid()}"
    s, _p = _supplier_product(db, sku)
    sug = suggest_packing_orders(db, _doc(supplier_id=s.id, qty="50"))
    assert sug.candidates == []
    assert sug.reason
    assert "não inventamos" in sug.reason.lower() or "nenhum pedido" in sug.reason.lower()


def test_packing_one_candidate(db):
    sku = f"C6O-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="50")
    sug = suggest_packing_orders(db, _doc(supplier_id=s.id, qty="50"))
    assert [c.order_id for c in sug.candidates] == [order.id]


def test_packing_n_candidates(db):
    sku = f"C6N-{_uid()}"
    s, p = _supplier_product(db, sku)
    a = _confirmed_order(db, s.id, p.id, sku, qty="50")
    b = _confirmed_order(db, s.id, p.id, sku, qty="80")
    sug = suggest_packing_orders(db, _doc(supplier_id=s.id, qty="50"))
    assert {c.order_id for c in sug.candidates} == {a.id, b.id}


def test_packing_line_auto_match_single_product(db):
    sku = f"C6M-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="50")
    plan = plan_packing_lines(db, _doc(supplier_id=s.id, qty="50"), order)
    commercial = plan.commercial_groups
    assert len(commercial) == 1
    assert commercial[0].status == "matched"
    assert commercial[0].order_item_id == order.items[0].id


def test_packing_4819_skips_order_item(db):
    sku = f"C6P-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="50")
    doc = _doc(supplier_id=s.id, ncm="48191000", desc="CARTON BOX", qty="10")
    plan = plan_packing_lines(db, doc, order)
    assert plan.packaging_groups
    assert all(g.order_item_id is None for g in plan.packaging_groups)
    assert not plan.commercial_groups


def test_packing_commitment_blocks_ship_qty(db):
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public

    s = catalog_public.create_supplier(db, name=f"C6C {_uid()}", country_code="IT")
    order = orders_public.create_order(
        db,
        code=f"C6C-{_uid()}",
        supplier_id=s.id,
        created_by_actor_id="test-actor",
        currency="EUR",
        source_system="MANUAL",
    )
    db.flush()
    o = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        line_kind="COMMITMENT",
        sku=f"EXT-{_uid()}",
        description="RACCHETTA BT",
        quantity="50",
        unit_price="106.66",
        unit="PZ",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    order = orders_public.get_order(db, o.id)
    plan = plan_packing_lines(db, _doc(supplier_id=s.id, qty="50"), order)
    assert any("COMMITMENT" in b for b in plan.blockers)


def _upload_pdf(client, batch_id: int, pdf_path: Path) -> dict:
    with pdf_path.open("rb") as f:
        ur = client.post(
            f"/api/ingestion/batches/{batch_id}/files",
            files={"files": (pdf_path.name, f, "application/pdf")},
        )
    assert ur.status_code == 200, ur.text
    return ur.json()["results"][0]


@pytest.mark.skipif(not PDF_328.is_file(), reason="PackingList_328.pdf absent")
def test_http_commit_328_fills_planned_shipment(admin_client, db):
    from app.catalog import public as catalog_public

    s = catalog_public.create_supplier(db, name="Heroe's Srl", country_code="IT")
    p = catalog_public.create_product(
        db, sku=f"8057628953593-{_uid()}", description="RACCHETTA BT 2026 STARLIGHT"
    )
    db.flush()
    order = _confirmed_order(db, s.id, p.id, p.sku, qty="50")
    db.commit()

    br = admin_client.post("/api/ingestion/batches", json={"notes": "c6-328"})
    assert br.status_code == 200
    occ = _upload_pdf(admin_client, br.json()["id"], PDF_328)
    rr = admin_client.post(
        f"/api/ingestion/occurrences/{occ['id']}/run-adapter",
        json={"adapter_id": "packing_list_detail_v1"},
    )
    assert rr.status_code == 200, rr.text
    doc_id = rr.json()["id"]
    assert rr.json()["doc_type"] == "PACKING_LIST_DETAIL"
    assert len(rr.json().get("rows") or []) == 5

    blocked = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-pl-detail",
        json={"operation_key": f"pl-no-order-{_uid()}"},
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json().get("error") in {
        "packing_order_id_required",
        "packing_commit_blocked",
    } or "order_id" in (blocked.json().get("message") or "").lower()

    prev = admin_client.get(
        f"/api/ingestion/documents/{doc_id}/preview-commit-pl-detail",
        params={"order_id": order.id},
    )
    assert prev.status_code == 200, prev.text
    body = prev.json()
    assert body["will_create_shipment"] is True
    assert body["can_commit"] is True, body.get("blockers")
    assert len(body["cartons"]) == 5

    cr = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-pl-detail",
        json={
            "operation_key": f"pl-{_uid()}",
            "order_id": order.id,
            "line_choices": [],
        },
    )
    assert cr.status_code == 200, cr.text
    attempt = cr.json()
    assert attempt["status"] == "SUCCEEDED"
    ship_ops = [
        o
        for o in attempt["operations"]
        if o.get("entity_type") == "shipment" and o.get("entity_id")
    ]
    assert ship_ops
    shipment_id = int(ship_ops[0]["entity_id"])

    sr = admin_client.get(f"/api/shipments/{shipment_id}")
    assert sr.status_code == 200, sr.text
    shipment = sr.json()
    assert shipment["status"] == "PLANNED"
    assert shipment["modal"] is None
    assert len(shipment["items"]) == 1
    assert Decimal(shipment["items"][0]["quantity"]) == Decimal("50")
    assert len(shipment["packages"]) == 5
    assert all(pkg["package_type"] == "CARTON" for pkg in shipment["packages"])
    assert any(
        r["reference_type"] == "PACKING_LIST" and r["reference_value"] == "328"
        for r in shipment["references"]
    )
    assert all(pkg.get("contents") for pkg in shipment["packages"])

    cr2 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-pl-detail",
        json={"operation_key": f"pl-again-{_uid()}", "order_id": order.id},
    )
    assert cr2.status_code == 200, cr2.text
    assert cr2.json()["id"] == attempt["id"]

    prev2 = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit-pl-detail")
    assert prev2.status_code == 200, prev2.text
    body2 = prev2.json()
    assert body2["already_committed"] is True
    assert body2["can_commit"] is False
    assert body2["last_succeeded_shipment_id"] == shipment_id
    assert body2["last_succeeded_attempt_id"] == attempt["id"]

    sr2 = admin_client.get(f"/api/shipments/{shipment_id}")
    assert sr2.status_code == 200
    assert len(sr2.json()["packages"]) == 5

    audit = admin_client.get(
        "/api/audit",
        params={"entity_type": "shipment", "entity_id": str(shipment_id)},
    )
    assert audit.status_code == 200, audit.text
    actions = {row["action"] for row in audit.json()}
    assert "shipment.create" in actions
    assert "shipment.packages.add" in actions
    assert "shipment.item.add" in actions
