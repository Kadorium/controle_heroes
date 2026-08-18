"""A0 — candidatos de Order e ambiguidade de linha na Fattura."""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace

from app.ingestion.fattura_line_match import plan_fattura_lines
from app.ingestion.fattura_order_candidates import suggest_fattura_orders


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


def _issue(code: str, status: str = "OPEN"):
    return SimpleNamespace(code=code, status=status, severity="WARNING")


def _row(index: int, sku: str, qty: str, price: str = "10.00", product_id: int | None = None):
    cells = {
        "sku": {"raw": sku, "normalized": sku},
        "quantity": {"raw": qty, "normalized": qty},
        "unit_price": {"raw": price, "normalized": price},
        "unit": {"raw": "PZ", "normalized": "PZ"},
    }
    if product_id is not None:
        cells["product_id_catalog"] = {
            "raw": str(product_id),
            "normalized": str(product_id),
        }
    return SimpleNamespace(row_index=index, cells_json=json.dumps(cells))


def _doc(*, supplier_id: int | None, sku: str, qty: str = "10", issues=None, extra_rows=None):
    fields = [
        _field("currency", "EUR"),
        _field("invoice_number", f"A0-{_uid()}"),
        _field("supplier_id_catalog", str(supplier_id) if supplier_id else None),
    ]
    rows = [_row(0, sku, qty)]
    if extra_rows:
        rows.extend(extra_rows)
    return SimpleNamespace(fields=fields, rows=rows, issues=issues or [])


def _supplier_product(db, sku: str):
    from app.catalog import public as catalog_public

    s = catalog_public.create_supplier(db, name=f"A0 Sup {_uid()}", country_code="IT")
    p = catalog_public.create_product(db, sku=sku, description="A0 item")
    db.flush()
    return s, p


def _confirmed_order(db, supplier_id: int, product_id: int, sku: str, *, qty: str, price: str):
    from app.orders import public as orders_public

    order = orders_public.create_order(
        db,
        code=f"A0-{_uid()}",
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


def test_a0_zero_candidates(db):
    sku = f"A0Z-{_uid()}"
    s, p = _supplier_product(db, sku)
    db.flush()
    doc = _doc(supplier_id=s.id, sku=sku, qty="5")
    sug = suggest_fattura_orders(db, doc)
    assert sug.candidates == []
    assert sug.reason
    assert "não inventamos" in sug.reason.lower() or "nenhum pedido" in sug.reason.lower()


def test_a0_one_candidate(db):
    sku = f"A0O-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="100", price="10.00")
    sug = suggest_fattura_orders(db, _doc(supplier_id=s.id, sku=sku, qty="10"))
    assert [c.order_id for c in sug.candidates] == [order.id]
    assert sug.reason is None
    assert any("Fornecedor" in e for e in sug.candidates[0].evidence)


def test_a0_n_candidates(db):
    sku = f"A0N-{_uid()}"
    s, p = _supplier_product(db, sku)
    a = _confirmed_order(db, s.id, p.id, sku, qty="100", price="10.00")
    b = _confirmed_order(db, s.id, p.id, sku, qty="80", price="10.00")
    sug = suggest_fattura_orders(db, _doc(supplier_id=s.id, sku=sku, qty="10"))
    ids = {c.order_id for c in sug.candidates}
    assert ids == {a.id, b.id}


def test_a0_supplier_missing_sku_discriminates(db):
    sku_hit = f"A0H-{_uid()}"
    sku_miss = f"A0M-{_uid()}"
    s1, p1 = _supplier_product(db, sku_hit)
    s2, p2 = _supplier_product(db, sku_miss)
    hit = _confirmed_order(db, s1.id, p1.id, sku_hit, qty="50", price="9")
    _confirmed_order(db, s2.id, p2.id, sku_miss, qty="50", price="9")
    doc = _doc(supplier_id=None, sku=sku_hit, qty="10", issues=[_issue("SUPPLIER_NOT_FOUND")])
    sug = suggest_fattura_orders(db, doc)
    assert [c.order_id for c in sug.candidates] == [hit.id]
    assert sug.supplier_unreliable is True
    assert sug.supplier_used is False


def test_a0_supplier_ambiguous_does_not_use_supplier_filter(db):
    sku = f"A0B-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="40", price="8")
    other_s, _ = _supplier_product(db, f"A0BX-{_uid()}")
    doc = _doc(
        supplier_id=other_s.id,
        sku=sku,
        qty="10",
        issues=[_issue("AMBIGUOUS_SUPPLIER")],
    )
    sug = suggest_fattura_orders(db, doc)
    assert [c.order_id for c in sug.candidates] == [order.id]


def test_a0_exhausted_issued_excluded(admin_client, db):
    from datetime import date, timedelta

    sku = f"A0E-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="10", price="20.00")
    db.commit()
    client = admin_client
    inv = client.post(
        f"/api/orders/{order.id}/invoices",
        json={"invoice_number": f"A0E-{_uid()}", "invoice_type": "FINAL"},
    )
    assert inv.status_code == 200, inv.text
    body = inv.json()
    item = body["items"][0]
    body = client.put(
        f"/api/invoices/{body['id']}/items",
        json={
            "expected_version": body["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "10",
                    "unit_price_gross": "20.00",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    due = (date.today() + timedelta(days=30)).isoformat()
    body = client.put(
        f"/api/invoices/{body['id']}/terms",
        json={
            "expected_version": body["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": due, "amount": "200.00"}],
        },
    ).json()
    att = client.post(
        "/api/documents",
        files={"file": ("fattura.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(body["id"]), "role": "official"},
    )
    assert att.status_code == 200, att.text
    issued = client.post(
        f"/api/invoices/{body['id']}/issue",
        json={"expected_version": body["version"]},
    )
    assert issued.status_code == 200, issued.text
    pays = client.get("/api/payables", params={"invoice_id": body["id"]}).json()
    assert len(pays) >= 1

    sug = suggest_fattura_orders(db, _doc(supplier_id=s.id, sku=sku, qty="10"))
    assert order.id not in {c.order_id for c in sug.candidates}


def test_a0_unique_line_auto_matches(db):
    sku = f"A0U-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="100", price="50.00")
    plan = plan_fattura_lines(db, _doc(supplier_id=s.id, sku=sku, qty="10"), order)
    assert plan.ok
    assert plan.matches[0].candidate_count == 1
    assert plan.matches[0].order_item_id == order.items[0].id
    assert plan.items_payload[0]["quantity"] == "10"
    assert plan.items_payload[0]["unit_price_gross"] == "10.00"


def test_a0_multiple_line_candidates_block_without_choice(db):
    sku = f"A0A-{_uid()}"
    s, p = _supplier_product(db, sku)
    from app.orders import public as orders_public

    order = orders_public.create_order(
        db,
        code=f"A0A-{_uid()}",
        supplier_id=s.id,
        created_by_actor_id="test-actor",
        currency="EUR",
    )
    db.flush()
    o = orders_public.add_item(
        db, order.id, expected_version=order.version, product_id=p.id, quantity="100", unit_price="50"
    )
    o = orders_public.add_item(
        db, o.id, expected_version=o.version, product_id=p.id, quantity="100", unit_price="55"
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    order = orders_public.get_order(db, o.id)
    plan = plan_fattura_lines(db, _doc(supplier_id=s.id, sku=sku, qty="10"), order)
    assert not plan.ok
    assert any(b.code == "fattura_line_ambiguous" for b in plan.blockers)
    assert plan.matches[0].status == "ambiguous"
    assert plan.matches[0].order_item_id is None
    assert plan.items_payload == []


def test_a0_explicit_line_choice_resolves(db):
    sku = f"A0C-{_uid()}"
    s, p = _supplier_product(db, sku)
    from app.orders import public as orders_public

    order = orders_public.create_order(
        db,
        code=f"A0C-{_uid()}",
        supplier_id=s.id,
        created_by_actor_id="test-actor",
        currency="EUR",
    )
    db.flush()
    o = orders_public.add_item(
        db, order.id, expected_version=order.version, product_id=p.id, quantity="100", unit_price="50"
    )
    o = orders_public.add_item(
        db, o.id, expected_version=o.version, product_id=p.id, quantity="100", unit_price="55"
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    order = orders_public.get_order(db, o.id)
    chosen = order.items[1].id
    plan = plan_fattura_lines(
        db,
        _doc(supplier_id=s.id, sku=sku, qty="10"),
        order,
        line_choices={0: chosen},
    )
    assert plan.ok
    assert plan.matches[0].order_item_id == chosen
    assert plan.items_payload[0]["unit_price_gross"] == "10.00"


def test_a0_no_line_candidate(db):
    sku = f"A0X-{_uid()}"
    other = f"A0Y-{_uid()}"
    s, p = _supplier_product(db, sku)
    order = _confirmed_order(db, s.id, p.id, sku, qty="10", price="10")
    plan = plan_fattura_lines(db, _doc(supplier_id=s.id, sku=other, qty="5"), order)
    assert not plan.ok
    assert any(b.code == "fattura_sku_not_on_order" for b in plan.blockers)


def test_a0_commitment_still_blocked(db):
    from app.orders import public as orders_public

    s, _p = _supplier_product(db, f"A0K-{_uid()}")
    order = orders_public.create_order(
        db,
        code=f"A0K-{_uid()}",
        supplier_id=s.id,
        created_by_actor_id="test-actor",
        currency="EUR",
    )
    db.flush()
    o = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        line_kind="COMMITMENT",
        external_code="IV-A0",
        description="compromisso",
        quantity="10",
        unit_price="10.00",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    order = orders_public.get_order(db, o.id)
    plan = plan_fattura_lines(db, _doc(supplier_id=s.id, sku="IV-A0", qty="5"), order)
    assert plan.commitment_only
    assert not plan.ok


def test_a0_same_price_two_buckets_still_ambiguous(db):
    sku = f"A0P-{_uid()}"
    s, p = _supplier_product(db, sku)
    from app.orders import public as orders_public

    order = orders_public.create_order(
        db,
        code=f"A0P-{_uid()}",
        supplier_id=s.id,
        created_by_actor_id="test-actor",
        currency="EUR",
    )
    db.flush()
    o = orders_public.add_item(
        db, order.id, expected_version=order.version, product_id=p.id, quantity="100", unit_price="50"
    )
    o = orders_public.add_item(
        db, o.id, expected_version=o.version, product_id=p.id, quantity="100", unit_price="50"
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    order = orders_public.get_order(db, o.id)
    plan = plan_fattura_lines(db, _doc(supplier_id=s.id, sku=sku, qty="10"), order)
    assert any(b.code == "fattura_line_ambiguous" for b in plan.blockers)


def test_a0_arch_public_contracts():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "ingestion"
    cand = (root / "fattura_order_candidates.py").read_text(encoding="utf-8")
    match = (root / "fattura_line_match.py").read_text(encoding="utf-8")
    assert "from app.orders import public" in cand
    assert "app.orders.repository" not in cand
    assert "app.orders.queries" not in cand
    assert "from app.billing import public" in match
    assert "import v1" not in cand and "from v1" not in cand


def test_a0_preview_candidates_and_commit_requires_order_id(admin_client, db):
    from test_j4_fin3b import SKU_244, _ingest_fattura_244

    client = admin_client
    sku = SKU_244
    s, p = _supplier_product(db, f"A0W-{_uid()}")
    # pedido coberto pelo SKU 244 no mesmo fornecedor do doc, se o adapter casar;
    # senão o preview ainda exige order_id.
    _confirmed_order(db, s.id, p.id, sku, qty="1000", price="99.83")
    db.commit()
    doc_id = _ingest_fattura_244(client)
    preview = client.get(
        f"/api/ingestion/documents/{doc_id}/preview-commit-fattura",
        params={"policy": "A"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_commit"] is False
    assert "order_candidates" in body
    assert "order_id" in (body["policy_match"].get("warning") or "").lower()
    r = client.post(
        f"/api/ingestion/documents/{doc_id}/commit-fattura",
        json={"operation_key": f"a0-no-oid-{doc_id}", "policy": "A"},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("error") == "order_id_required"


def test_a0_commit_same_draft_with_pdf_qty_and_issue_payables(admin_client, db):
    from test_j4_fin3b import (
        SKU_244,
        _commit_a,
        _ensure_product,
        _ingest_fattura_244,
        _preview_a,
        _unique_supplier,
    )

    client = admin_client
    s_id = _unique_supplier(db)
    p_id = _ensure_product(db, SKU_244, "RACCHETTA BT 2026 SHOW")
    order = _confirmed_order(db, s_id, p_id, SKU_244, qty="1000", price="50.00")
    db.commit()
    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, order.id).json()
    assert preview["can_commit"] is True
    assert any(op["op_key"] == "create_invoice" for op in preview["operations"])
    r = _commit_a(client, doc_id, order.id, f"a0-draft-{doc_id}")
    assert r.status_code == 200, r.text
    attempt = r.json()
    inv_op = next(op for op in attempt["operations"] if op.get("entity_type") == "invoice")
    invoice_id = int(inv_op["entity_id"])
    inv = client.get(f"/api/invoices/{invoice_id}").json()
    assert inv["status"] == "DRAFT"
    qtys = sorted(float(it["quantity"]) for it in inv["items"])
    assert qtys == [50.0, 150.0]
    prices = {it["unit_price_gross"] for it in inv["items"]}
    assert any(str(p).startswith("99.83") for p in prices)

    prev2 = _preview_a(client, doc_id, order.id).json()
    assert prev2["already_committed"] is True
    assert prev2["can_commit"] is False
    assert prev2["last_succeeded_invoice_id"] == invoice_id
    again = _commit_a(client, doc_id, order.id, f"a0-again-{doc_id}")
    assert again.status_code == 200, again.text
    assert again.json()["id"] == attempt["id"]

    due = (date.today() + timedelta(days=20)).isoformat()
    inv = client.put(
        f"/api/invoices/{invoice_id}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": due, "amount": inv["net_amount"]}],
        },
    ).json()
    att = client.post(
        "/api/documents",
        files={"file": ("fattura.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(invoice_id), "role": "official"},
    )
    assert att.status_code == 200, att.text
    inv = client.get(f"/api/invoices/{invoice_id}").json()
    issued = client.post(
        f"/api/invoices/{invoice_id}/issue",
        json={"expected_version": inv["version"]},
    )
    assert issued.status_code == 200, issued.text
    issued_body = issued.json()
    assert issued_body["status"] == "ISSUED"
    assert issued_body["payables"]
    assert all(p["source_type"] == "INVOICE" for p in issued_body["payables"])
    pays = client.get("/api/payables", params={"invoice_id": invoice_id}).json()
    assert len(pays) >= 1
