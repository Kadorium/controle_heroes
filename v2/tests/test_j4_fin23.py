"""J4-FIN FIN-3 + FIN-2 — Fattura scadenze literais, UNPARSED_LINE, IBAN, order-scoped allocate."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "ingestion"
FATTURA_202 = FIXTURES / "corpus_202" / "Fattura_202.pdf"
FATTURA_328 = FIXTURES / "corpus_328" / "Fattura_328.pdf"
FATTURA_244 = FIXTURES / "corpus_244" / "Fattura_244.pdf"
FATTURA_245 = FIXTURES / "corpus_245" / "Fattura_245.pdf"
FATTURA_332 = FIXTURES / "corpus_332" / "Fattura_332.pdf"
DOGANALE_244 = FIXTURES / "corpus_244" / "FatturaDoganale_244.pdf"

IBAN_244 = "IT82G0707236590000000446136"
IBAN_BPM = "IT95V0503402419000000006147"
LETTERHEAD_INTESA = "IT44Z030693713310000000724"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _upload_pdf(client, batch_id: int, pdf_path: Path) -> dict:
    with open(pdf_path, "rb") as f:
        r = client.post(
            f"/api/ingestion/batches/{batch_id}/files",
            files=[("files", (pdf_path.name, f, "application/pdf"))],
        )
    assert r.status_code == 200, r.text
    return r.json()


def _ensure_heroes(db) -> int:
    from app.catalog import public as catalog_public

    for s in catalog_public.list_suppliers(db, q="Heroe", limit=20):
        if (s.name or "") == "Heroe's Srl":
            return s.id
    sup = catalog_public.create_supplier(db, name="Heroe's Srl", country_code="IT")
    db.flush()
    return sup.id


def _ensure_product(db, sku: str, description: str) -> int:
    from app.catalog import public as catalog_public

    try:
        return catalog_public.get_product_by_sku(db, sku).id
    except Exception:
        p = catalog_public.create_product(db, sku=sku, description=description)
        db.flush()
        return p.id


def _attach_doc(client, invoice_id: int) -> None:
    r = client.post(
        "/api/documents",
        files={"file": ("fattura.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(invoice_id), "role": "official"},
    )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Adapter goldens (pure)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pdf,total,scadenze",
    [
        (FATTURA_202, Decimal("30188.00"), [Decimal("15094.00"), Decimal("15094.00")]),
        (FATTURA_328, Decimal("5333.00"), [Decimal("1250.00"), Decimal("4083.00")]),
        (FATTURA_244, Decimal("19966.00"), [Decimal("5000.00"), Decimal("14966.00")]),
        (FATTURA_245, Decimal("61424.40"), [Decimal("31500.00"), Decimal("29924.40")]),
        (FATTURA_332, Decimal("1445.50"), [Decimal("1445.50")]),
    ],
)
def test_fin3_scadenze_sum_equals_total(pdf, total, scadenze):
    from app.ingestion.adapters.fattura_heroes_v1 import extract

    assert pdf.is_file(), pdf
    raw = extract(pdf.read_bytes())
    assert raw.total_document == total
    amounts = [s.amount for s in raw.scadenze]
    assert amounts == scadenze
    assert abs(sum(amounts) - total) <= Decimal("0.02")


def test_fin3_iban_payment_line_not_letterhead():
    from app.ingestion.adapters.fattura_heroes_v1 import extract

    r244 = extract(FATTURA_244.read_bytes())
    assert r244.destination_iban == IBAN_244
    assert r244.destination_iban != LETTERHEAD_INTESA
    assert r244.destination_bank and "EMIL BANCA" in r244.destination_bank.upper()

    r245 = extract(FATTURA_245.read_bytes())
    assert r245.destination_iban == IBAN_BPM
    assert "BPM" in (r245.destination_bank or "").upper()

    r332 = extract(FATTURA_332.read_bytes())
    assert r332.destination_iban == IBAN_BPM

    r202 = extract(FATTURA_202.read_bytes())
    assert r202.destination_iban is None
    r328 = extract(FATTURA_328.read_bytes())
    assert r328.destination_iban is None


def test_fin3_unparsed_line_332_blocks_and_math_runs():
    from app.ingestion.adapters.fattura_heroes_v1 import extract, _validate_math

    raw = extract(FATTURA_332.read_bytes())
    assert raw.lines == []
    issues = _validate_math(raw)
    codes = {i["code"] for i in issues}
    assert "UNPARSED_LINE" in codes
    unparsed = [i for i in issues if i["code"] == "UNPARSED_LINE"]
    assert unparsed[0]["severity"] == "ERROR"
    assert "10878" in unparsed[0]["message"]
    assert "MATH_LINES_VS_TAX_BASES" in codes
    assert "NO_LINE_ITEMS" in codes


def test_fin3_202_and_244_no_unparsed_line():
    from app.ingestion.adapters.fattura_heroes_v1 import extract, _validate_math

    for pdf, nlines in ((FATTURA_202, 7), (FATTURA_244, 2)):
        raw = extract(pdf.read_bytes())
        assert len(raw.lines) == nlines
        issues = _validate_math(raw)
        assert not any(i["code"] == "UNPARSED_LINE" for i in issues)


def test_fin3_244_two_lines_same_ean_not_grouped():
    from app.ingestion.adapters.fattura_heroes_v1 import extract

    raw = extract(FATTURA_244.read_bytes())
    skus = [l.sku for l in raw.lines]
    qtys = [l.quantity for l in raw.lines]
    assert skus == ["8057628953586", "8057628953586"]
    assert qtys == [Decimal("50"), Decimal("150")]


# ---------------------------------------------------------------------------
# Policy A: order_id obrigatório
# ---------------------------------------------------------------------------


def test_fin3_policy_a_without_order_id_is_422(admin_client, db):
    from app.orders import public as orders_public

    client = admin_client
    sup_id = _ensure_heroes(db)
    _ensure_product(db, "8057628950936", "WASH BAG REBEL - PURPLE")
    order = orders_public.create_order(
        db,
        code=f"ORD-AUTO-{_uid()}",
        supplier_id=sup_id,
        created_by_actor_id="test-actor",
        currency="EUR",
        source_system="MANUAL",
        external_ref="202",
    )
    db.flush()
    prod_id = _ensure_product(db, "8057628950936", "WASH BAG REBEL - PURPLE")
    updated = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        product_id=prod_id,
        quantity="150",
        unit_price="6.50",
        unit="PZ",
    )
    orders_public.confirm_order(db, order.id, expected_version=updated.version)
    db.commit()

    r = client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    occ_id = _upload_pdf(client, batch_id, FATTURA_202)["results"][0]["id"]
    r = client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura")
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]

    preview = client.get(
        f"/api/ingestion/documents/{doc_id}/preview-commit-fattura",
        params={"policy": "A"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_commit"] is False
    assert "order_id" in (body["policy_match"].get("warning") or "").lower()

    r = client.post(
        f"/api/ingestion/documents/{doc_id}/commit-fattura",
        json={"operation_key": f"no-oid-{doc_id}", "policy": "A"},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("error") == "order_id_required"


# ---------------------------------------------------------------------------
# Fattura 244 → Invoice AMOUNT + IBAN + issue payables literais
# ---------------------------------------------------------------------------


def _confirmed_order_244(db, supplier_id: int):
    from app.orders import public as orders_public

    sku = "8057628953586"
    prod_id = _ensure_product(db, sku, "RACCHETTA BT 2026 SHOW")
    order = orders_public.create_order(
        db,
        code=f"ORD-244-{_uid()}",
        supplier_id=supplier_id,
        created_by_actor_id="test-actor",
        currency="EUR",
        source_system="MANUAL",
        external_ref="244-sample",
    )
    db.flush()
    o = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        product_id=prod_id,
        quantity="50",
        unit_price="99.83",
        unit="PZ",
    )
    o = orders_public.add_item(
        db,
        o.id,
        expected_version=o.version,
        product_id=prod_id,
        quantity="150",
        unit_price="99.83",
        unit="PZ",
    )
    orders_public.confirm_order(db, o.id, expected_version=o.version)
    db.flush()
    return orders_public.get_order(db, o.id)


def test_fin3_fattura_244_amount_iban_issue_payables(admin_client, db):
    client = admin_client
    sup_id = _ensure_heroes(db)
    order = _confirmed_order_244(db, sup_id)
    db.commit()

    r = client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    occ_id = _upload_pdf(client, batch_id, FATTURA_244)["results"][0]["id"]
    r = client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura")
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]

    r = client.post(
        f"/api/ingestion/documents/{doc_id}/commit-fattura",
        json={
            "operation_key": f"fin3-244-{doc_id}",
            "policy": "A",
            "order_id": order.id,
            "line_choices": [
                {"row_index": 0, "order_item_id": order.items[0].id},
                {"row_index": 1, "order_item_id": order.items[1].id},
            ],
        },
    )
    assert r.status_code == 200, r.text
    attempt = r.json()
    assert attempt["status"] == "SUCCEEDED", attempt
    create_op = next(
        (op for op in (attempt.get("operations") or []) if op.get("op_key") == "create_invoice"),
        None,
    )
    assert create_op is not None, attempt
    invoice_id = int(create_op["entity_id"])

    inv = client.get(f"/api/invoices/{invoice_id}").json()
    assert inv["terms_mode"] == "AMOUNT"
    assert inv["terms_from_document"] is True
    assert inv["destination_iban"] == IBAN_244
    assert inv["items"]
    assert all(it["discount_type"] == "NONE" for it in inv["items"])
    amounts = sorted(Decimal(t["amount"]) for t in inv["terms"])
    assert amounts == [Decimal("5000.00"), Decimal("14966.00")]

    bad = client.put(
        f"/api/invoices/{invoice_id}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "PERCENT",
            "terms": [
                {"due_date": date.today().isoformat(), "percent": "50"},
                {"due_date": (date.today() + timedelta(days=60)).isoformat(), "percent": "50"},
            ],
        },
    )
    assert bad.status_code == 400, bad.text
    assert "percentual" in bad.json().get("message", "").lower() or "literais" in bad.json().get(
        "message", ""
    ).lower()

    inv = client.get(f"/api/invoices/{invoice_id}").json()
    if not inv.get("documents"):
        _attach_doc(client, invoice_id)
        inv = client.get(f"/api/invoices/{invoice_id}").json()
    r = client.post(
        f"/api/invoices/{invoice_id}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    pays = sorted(inv["payables"], key=lambda p: p["sequence"])
    assert len(pays) == 2
    assert Decimal(pays[0]["amount"]) == Decimal("5000.00")
    assert Decimal(pays[1]["amount"]) == Decimal("14966.00")
    assert pays[0]["destination_iban"] == IBAN_244
    assert pays[1]["destination_iban"] == IBAN_244
    assert pays[0]["order_id"] == order.id

    r = client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    dog_occ = _upload_pdf(client, batch_id, DOGANALE_244)["results"][0]["id"]
    r = client.post(
        f"/api/ingestion/occurrences/{dog_occ}/run-adapter",
        json={"adapter_id": "fattura_doganale_v1"},
    )
    assert r.status_code == 200, r.text
    dog_doc = r.json()["id"]
    r = client.post(
        f"/api/ingestion/documents/{dog_doc}/commit-doganale",
        json={"operation_key": f"twin-d-{dog_doc}"},
    )
    assert r.status_code == 200, r.text
    dog_attempt = r.json()
    assert dog_attempt["status"] == "SUCCEEDED", dog_attempt

    pays = client.get("/api/payables", params={"order_id": order.id}).json()
    commercial = [p for p in pays if p.get("source_type") in (None, "INVOICE")]
    customs = [p for p in pays if p.get("source_type") == "CUSTOMS_FUNDING"]
    assert len(commercial) == 2, pays
    assert customs == []


# ---------------------------------------------------------------------------
# FIN-2: allocate order-scoped
# ---------------------------------------------------------------------------


def _issued_invoice(client, *, supplier_id: int, product_id: int, code: str, amount: str):
    o = client.post(
        "/api/orders",
        json={"code": code, "supplier_id": supplier_id, "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": product_id,
            "quantity": "1",
            "unit_price": amount,
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = client.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{code}"},
    ).json()
    item = inv["items"][0]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": item["quantity"],
                    "unit_price_gross": item["unit_price_gross"],
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    due = date.today() + timedelta(days=30)
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": due.isoformat(), "amount": amount}],
        },
    ).json()
    _attach_doc(client, inv["id"])
    inv = client.get(f"/api/invoices/{inv['id']}").json()
    inv = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    ).json()
    return o, inv


def test_fin2_allocate_advance_same_order_only(admin_client):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": f"Fin2-{_uid()}", "country_code": "IT"}).json()
    p = c.post("/api/products", json={"sku": f"FIN2-{_uid()}", "description": "Item"}).json()
    order_a, inv_a = _issued_invoice(
        c, supplier_id=s["id"], product_id=p["id"], code=f"A-{_uid()}", amount="1000.00"
    )
    order_b, inv_b = _issued_invoice(
        c, supplier_id=s["id"], product_id=p["id"], code=f"B-{_uid()}", amount="1000.00"
    )
    pa = inv_a["payables"][0]
    pb = inv_b["payables"][0]

    adv = c.post(
        f"/api/orders/{order_a['id']}/advances",
        json={
            "amount": "400.00",
            "payment_date": date.today().isoformat(),
            "execution_date": date.today().isoformat(),
            "rate": "6.20",
            "register_without_fx_document": True,
            "reason_code": "TEST_FIN2",
        },
    )
    assert adv.status_code == 200, adv.text
    payment_id = adv.json()["payment_id"]
    pay = c.get(f"/api/payments/{payment_id}").json()
    listing = c.get(f"/api/orders/{order_a['id']}/advances").json()
    assert listing["advances"][0]["amount_unallocated"] == "400.00"

    elig = c.get(f"/api/payments/{payment_id}/eligible-payables").json()
    elig_ids = {e["id"] for e in elig}
    assert pa["id"] in elig_ids
    assert pb["id"] not in elig_ids

    bad = c.post(
        f"/api/payments/{payment_id}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"cross-{_uid()}",
            "allocations": [
                {"payable_id": pb["id"], "amount": "400.00", "expected_version": pb["version"]}
            ],
        },
    )
    assert bad.status_code == 400, bad.text

    ok = c.post(
        f"/api/payments/{payment_id}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"same-{_uid()}",
            "allocations": [
                {"payable_id": pa["id"], "amount": "400.00", "expected_version": pa["version"]}
            ],
        },
    )
    assert ok.status_code == 200, ok.text
    pa2 = c.get(f"/api/payables/{pa['id']}").json()
    assert pa2["status"] == "PARTIALLY_PAID"
    assert Decimal(pa2["balance"]) == Decimal("600.00")
