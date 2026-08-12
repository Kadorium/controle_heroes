"""J4-FIN FIN-3B — Fattura commit fatura a qty (e o preço) do PDF."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from test_j4_fin23 import (
    FATTURA_244,
    _attach_doc,
    _ensure_product,
    _uid,
    _upload_pdf,
)

SKU_244 = "8057628953586"


def _unique_supplier(db) -> int:
    from app.catalog import public as catalog_public

    s = catalog_public.create_supplier(db, name=f"FIN3B {_uid()}", country_code="IT")
    db.flush()
    return s.id


def _ingest_fattura_244(client) -> int:
    r = client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    occ_id = _upload_pdf(client, batch_id, FATTURA_244)["results"][0]["id"]
    r = client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura")
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _commit_a(client, doc_id: int, order_id: int, key: str):
    return client.post(
        f"/api/ingestion/documents/{doc_id}/commit-fattura",
        json={"operation_key": key, "policy": "A", "order_id": order_id},
    )


def _preview_a(client, doc_id: int, order_id: int):
    return client.get(
        f"/api/ingestion/documents/{doc_id}/preview-commit-fattura",
        params={"policy": "A", "order_id": order_id},
    )


def _confirmed_product_order(db, supplier_id: int, *, qty: str, price: str, sku: str = SKU_244):
    from app.orders import public as orders_public

    prod_id = _ensure_product(db, sku, "RACCHETTA BT 2026 SHOW")
    order = orders_public.create_order(
        db,
        code=f"ORD-3B-{_uid()}",
        supplier_id=supplier_id,
        created_by_actor_id="test-actor",
        currency="EUR",
        source_system="MANUAL",
        external_ref="fin3b",
    )
    db.flush()
    o = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        product_id=prod_id,
        quantity=qty,
        unit_price=price,
        unit="PZ",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    return orders_public.get_order(db, o.id)


def test_fin3b_pdf_qty_against_large_order_line(admin_client, db):
    client = admin_client
    sup_id = _unique_supplier(db)
    order = _confirmed_product_order(db, sup_id, qty="14600", price="99.83")
    db.commit()

    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, order.id)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_commit"] is True
    map_op = next(op for op in body["operations"] if op["op_key"] == "map_invoice_items")
    lines = map_op["params"]["lines"]
    assert len(lines) == 2
    assert [ln["pdf_qty"] for ln in lines] == ["50", "150"]
    assert lines[0]["order_item_id"] == lines[1]["order_item_id"] == order.items[0].id

    r = _commit_a(client, doc_id, order.id, f"fin3b-14600-{doc_id}")
    assert r.status_code == 200, r.text
    attempt = r.json()
    assert attempt["status"] == "SUCCEEDED", attempt
    invoice_id = int(
        next(op["entity_id"] for op in attempt["operations"] if op["op_key"] == "create_invoice")
    )
    inv = client.get(f"/api/invoices/{invoice_id}").json()
    qtys = sorted(Decimal(it["quantity"]) for it in inv["items"])
    assert qtys == [Decimal("50"), Decimal("150")]
    assert {it["order_item_id"] for it in inv["items"]} == {order.items[0].id}
    assert Decimal(inv["net_amount"]) == Decimal("19966.00")
    amounts = sorted(Decimal(t["amount"]) for t in inv["terms"])
    assert amounts == [Decimal("5000.00"), Decimal("14966.00")]

    if not inv.get("documents"):
        _attach_doc(client, invoice_id)
        inv = client.get(f"/api/invoices/{invoice_id}").json()
    issued = client.post(
        f"/api/invoices/{invoice_id}/issue",
        json={"expected_version": inv["version"]},
    )
    assert issued.status_code == 200, issued.text

    qty = client.get(f"/api/orders/{order.id}/invoiced-quantities").json()
    row = next(q for q in qty if q["order_item_id"] == order.items[0].id)
    assert Decimal(row["issued_qty"]) == Decimal("200")
    assert Decimal(row["available_qty"]) == Decimal("14400")

    # Segunda fatura (80) via billing — 245 não é "só +80" deste EAN.
    inv2 = client.post(
        f"/api/orders/{order.id}/invoices",
        json={"invoice_number": f"F-3B-80-{_uid()}"},
    ).json()
    oid = order.items[0].id
    inv2 = client.put(
        f"/api/invoices/{inv2['id']}/items",
        json={
            "expected_version": inv2["version"],
            "items": [
                {
                    "order_item_id": oid,
                    "quantity": "80",
                    "unit_price_gross": "99.83",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    due = date.today() + timedelta(days=30)
    inv2 = client.put(
        f"/api/invoices/{inv2['id']}/terms",
        json={
            "expected_version": inv2["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": due.isoformat(), "amount": "7986.40"}],
        },
    ).json()
    _attach_doc(client, inv2["id"])
    inv2 = client.get(f"/api/invoices/{inv2['id']}").json()
    inv2 = client.post(
        f"/api/invoices/{inv2['id']}/issue",
        json={"expected_version": inv2["version"]},
    ).json()
    assert inv2["status"] == "ISSUED"
    qty = client.get(f"/api/orders/{order.id}/invoiced-quantities").json()
    row = next(q for q in qty if q["order_item_id"] == oid)
    assert Decimal(row["issued_qty"]) == Decimal("280")
    assert Decimal(row["available_qty"]) == Decimal("14320")


def test_fin3b_sku_not_on_order_is_422(admin_client, db):
    client = admin_client
    sup_id = _unique_supplier(db)
    order = _confirmed_product_order(
        db, sup_id, qty="100", price="10", sku="8057628950936"
    )
    db.commit()
    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, order.id).json()
    assert preview["can_commit"] is False
    assert any("fattura_sku_not_on_order" in (op["op_key"] + op["description"]) for op in preview["operations"])
    r = _commit_a(client, doc_id, order.id, f"fin3b-unmatched-{doc_id}")
    assert r.status_code == 422, r.text
    assert r.json().get("error") == "fattura_sku_not_on_order"


def test_fin3b_qty_exceeds_remaining_is_422(admin_client, db):
    client = admin_client
    sup_id = _unique_supplier(db)
    order = _confirmed_product_order(db, sup_id, qty="100", price="99.83")
    db.commit()
    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, order.id).json()
    assert preview["can_commit"] is False
    assert any("fattura_qty_exceeds_remaining" in (op["op_key"] + op["description"]) for op in preview["operations"])
    r = _commit_a(client, doc_id, order.id, f"fin3b-exceed-{doc_id}")
    assert r.status_code == 422, r.text
    assert r.json().get("error") == "fattura_qty_exceeds_remaining"
    assert "restante" in r.json().get("message", "").lower() or "excede" in r.json().get("message", "").lower()


def test_fin3b_commitment_order_keeps_honest_message(admin_client, db):
    from app.orders import public as orders_public

    client = admin_client
    sup_id = _unique_supplier(db)
    order = orders_public.create_order(
        db,
        code=f"ORD-3B-C-{_uid()}",
        supplier_id=sup_id,
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
        external_code="I.V. 1",
        description="racchette compromisso",
        quantity="14600",
        unit_price="50.00",
        unit="PZ",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.commit()

    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, o.id).json()
    assert preview["can_commit"] is False
    assert any(op["op_key"] == "blocked_no_billable_lines" for op in preview["operations"])
    r = _commit_a(client, doc_id, o.id, f"fin3b-cmt-{doc_id}")
    assert r.status_code == 422, r.text
    assert r.json().get("error") == "fattura_no_billable_lines"
    assert "nenhuma linha faturável" in r.json().get("message", "")


def test_fin3b_price_divergence_leaves_trail(admin_client, db):
    client = admin_client
    sup_id = _unique_supplier(db)
    order = _confirmed_product_order(db, sup_id, qty="14600", price="50.00")
    db.commit()
    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, order.id).json()
    assert preview["can_commit"] is True
    assert any(op["op_key"] == "warn_price_divergence" for op in preview["operations"])

    r = _commit_a(client, doc_id, order.id, f"fin3b-px-{doc_id}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SUCCEEDED", r.json()
    invoice_id = int(
        next(op["entity_id"] for op in r.json()["operations"] if op["op_key"] == "create_invoice")
    )
    inv = client.get(f"/api/invoices/{invoice_id}").json()
    notes = inv.get("notes") or ""
    assert "Divergência de preço" in notes
    assert "50" in notes and "99.83" in notes

    audit = client.get(
        "/api/audit",
        params={"entity_type": "invoice", "entity_id": str(invoice_id)},
    )
    assert audit.status_code == 200, audit.text
    actions = [a["action"] for a in audit.json()]
    assert "invoice_price_divergence" in actions
    order_audit = client.get(
        "/api/audit",
        params={"entity_type": "order", "entity_id": str(order.id)},
    )
    assert order_audit.status_code == 200, order_audit.text
    assert "invoice_price_divergence" in [a["action"] for a in order_audit.json()]


def test_fin3b_ambiguous_match_visible_in_preview(admin_client, db):
    from app.orders import public as orders_public

    client = admin_client
    sup_id = _unique_supplier(db)
    prod_id = _ensure_product(db, SKU_244, "RACCHETTA BT 2026 SHOW")
    order = orders_public.create_order(
        db,
        code=f"ORD-3B-AMB-{_uid()}",
        supplier_id=sup_id,
        created_by_actor_id="test-actor",
        currency="EUR",
        source_system="MANUAL",
    )
    db.flush()
    o = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        product_id=prod_id,
        quantity="1000",
        unit_price="50.00",
        unit="PZ",
    )
    o = orders_public.add_item(
        db,
        o.id,
        expected_version=o.version,
        product_id=prod_id,
        quantity="1000",
        unit_price="55.00",
        unit="PZ",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.commit()
    order = orders_public.get_order(db, o.id)

    doc_id = _ingest_fattura_244(client)
    preview = _preview_a(client, doc_id, order.id).json()
    assert preview["can_commit"] is True
    assert any(op["op_key"] == "match_choice" for op in preview["operations"])
    assert any(op["op_key"] == "warn_ambiguous_match" for op in preview["operations"])
    choice = next(op for op in preview["operations"] if op["op_key"] == "match_choice")
    assert choice["params"]["candidate_count"] == 2
    assert choice["params"]["order_item_id"] == order.items[0].id
    assert any(c["unit_price"] in ("50.00", "50.0000", "50") for c in choice["params"]["candidates"])
