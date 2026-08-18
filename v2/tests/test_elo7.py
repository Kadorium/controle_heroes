"""Elo 7 — Doganale fill, Print attach, Numerário tax register, nationalization residual."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingestion"
PDF_DOG_328 = FIXTURES / "corpus_328" / "FatturaDoganale_328.pdf"
PDF_PRINT_328 = FIXTURES / "corpus_328" / "PrintDeclaration_328.pdf"
PDF_DOG_202 = FIXTURES / "corpus_202" / "FatturaDoganale_202.pdf"
PDF_NUM_202 = FIXTURES / "corpus_202" / "Solicitacao_Numerario.pdf"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _upload_pdf(client, batch_id: int, pdf_path: Path) -> dict:
    with pdf_path.open("rb") as f:
        ur = client.post(
            f"/api/ingestion/batches/{batch_id}/files",
            files={"files": (pdf_path.name, f, "application/pdf")},
        )
    assert ur.status_code == 200, ur.text
    return ur.json()["results"][0]


def _run_adapter(client, occ_id: int, adapter_id: str) -> dict:
    rr = client.post(
        f"/api/ingestion/occurrences/{occ_id}/run-adapter",
        json={"adapter_id": adapter_id},
    )
    assert rr.status_code == 200, rr.text
    return rr.json()


def _confirmed_order(client, *, tag: str, qty="50", price="106.66"):
    s = client.post("/api/suppliers", json={"name": f"Sup-{tag}", "country_code": "IT"}).json()
    p = client.post(
        "/api/products",
        json={"sku": f"SKU-{tag}", "description": f"P {tag}"},
    ).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{tag}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": qty,
            "unit_price": price,
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    return s, p, o


def _issued_invoice(client, order, *, number: str, qty: str | None = None):
    inv = client.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": number, "invoice_type": "FINAL"},
    ).json()
    oi = order["items"][0]["id"]
    use_qty = qty or order["items"][0]["quantity"]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": oi,
                    "quantity": use_qty,
                    "unit_price_gross": order["items"][0]["unit_price"],
                    "discount_type": "PERCENT",
                    "discount_percent": "0",
                }
            ],
        },
    ).json()
    today = date.today()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "PERCENT",
            "terms": [{"due_date": (today + timedelta(days=30)).isoformat(), "percent": "100"}],
        },
    ).json()
    r = client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF-1.4 x"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    assert r.status_code == 200, r.text
    inv = client.get(f"/api/invoices/{inv['id']}").json()
    r = client.post(f"/api/invoices/{inv['id']}/issue", json={"expected_version": inv["version"]})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Extracts (E7-0)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PDF_DOG_328.is_file(), reason="FatturaDoganale_328.pdf absent")
def test_extract_328_doganale_one_line_qty_50():
    from app.ingestion.adapters.fattura_doganale_v1 import extract

    raw = extract(PDF_DOG_328.read_bytes())
    assert raw.document_number == "328"
    assert raw.total_document == Decimal("5333.00")
    assert len(raw.lines) == 1
    assert raw.lines[0].quantity == Decimal("50")
    assert (raw.lines[0].ncm or "").replace(" ", "") == "95069900"


@pytest.mark.skipif(not PDF_DOG_202.is_file(), reason="FatturaDoganale_202.pdf absent")
def test_extract_202_doganale_seven_lines():
    from app.ingestion.adapters.fattura_doganale_v1 import extract

    raw = extract(PDF_DOG_202.read_bytes())
    assert raw.document_number == "202"
    assert raw.total_document == Decimal("30188.00")
    assert len(raw.lines) == 7
    assert sum(ln.quantity for ln in raw.lines) == Decimal("1600")


@pytest.mark.skipif(not PDF_NUM_202.is_file(), reason="Solicitacao_Numerario.pdf absent")
def test_extract_202_numerario_brazilian_taxes():
    from app.ingestion.adapters.solicitacao_numerario_v1 import extract

    raw = extract(PDF_NUM_202.read_bytes())
    assert raw.payee_name and "BECH" in raw.payee_name.upper()
    codes = {ln.code for ln in raw.lines if ln.category == "tax"}
    for expected in ("AFRMM", "ICMS", "II", "IPI", "PIS", "COFINS", "SISCOMEX"):
        assert expected in codes, codes
    by_code = {ln.code: ln.amount_brl for ln in raw.lines if ln.category == "tax"}
    assert by_code["II"] == Decimal("343800.00")
    assert by_code["IPI"] == Decimal("253500.00")
    assert by_code["PIS"] == Decimal("37700.00")
    assert by_code["COFINS"] == Decimal("167900.00")
    assert by_code["AFRMM"] == Decimal("2000.00")
    assert by_code["ICMS"] == Decimal("556000.00")
    assert "202" in (raw.invoice_refs or [])


# ---------------------------------------------------------------------------
# HTTP Doganale fill + idempotency (E7-2)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PDF_DOG_328.is_file(), reason="FatturaDoganale_328.pdf absent")
def test_http_commit_328_fills_doganale_and_retry_same_process(admin_client):
    br = admin_client.post("/api/ingestion/batches", json={"notes": "e7-dog-328"})
    occ = _upload_pdf(admin_client, br.json()["id"], PDF_DOG_328)
    doc = _run_adapter(admin_client, occ["id"], "fattura_doganale_v1")
    doc_id = doc["id"]
    assert doc["doc_type"] == "FATTURA_DOGANALE"

    prev = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit-doganale")
    assert prev.status_code == 200, prev.text
    body = prev.json()
    assert body["will_create_process"] is True
    assert body["can_commit"] is True, body.get("blockers")
    assert len(body["lines"]) >= 1
    assert body["already_committed"] is False

    cr = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-doganale",
        json={"operation_key": f"dog-{_uid()}"},
    )
    assert cr.status_code == 200, cr.text
    attempt = cr.json()
    failed_ops = [
        {
            "op_key": o.get("op_key"),
            "status": o.get("status"),
            "error": o.get("error_message"),
            "details": o.get("details_json"),
        }
        for o in (attempt.get("operations") or [])
        if o.get("status") != "SUCCEEDED"
    ]
    assert attempt["status"] == "SUCCEEDED", failed_ops or attempt
    proc_ops = [
        o
        for o in attempt["operations"]
        if o.get("entity_type") in ("import_process", "process") and o.get("entity_id")
    ]
    assert proc_ops
    process_id = int(proc_ops[0]["entity_id"])

    dog = admin_client.get(f"/api/import-processes/{process_id}/doganale")
    assert dog.status_code == 200, dog.text
    summary = dog.json()
    assert summary is not None
    current = next(v for v in summary["versions"] if v["is_current"])
    assert current["status"] == "ACTIVE"
    assert len(current["lines"]) >= 1
    qty = sum(Decimal(str(ln["quantity"] or 0)) for ln in current["lines"])
    assert qty == Decimal("50")
    assert any((ln.get("ncm") or "").replace(" ", "") == "95069900" for ln in current["lines"])

    cr2 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-doganale",
        json={"operation_key": f"dog-again-{_uid()}"},
    )
    assert cr2.status_code == 200, cr2.text
    assert cr2.json()["id"] == attempt["id"]

    prev2 = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit-doganale")
    assert prev2.json()["already_committed"] is True
    assert prev2.json()["can_commit"] is False
    assert prev2.json()["last_succeeded_process_id"] == process_id

    dog2 = admin_client.get(f"/api/import-processes/{process_id}/doganale").json()
    active = [v for v in dog2["versions"] if v["status"] == "ACTIVE"]
    assert len(active) == 1


@pytest.mark.skipif(not PDF_DOG_328.is_file(), reason="FatturaDoganale_328.pdf absent")
def test_http_doganale_one_invoice_not_silent_link(admin_client):
    tag = _uid()
    _, _, order = _confirmed_order(admin_client, tag=tag, qty="50")
    inv = _issued_invoice(admin_client, order, number="328", qty="50")

    br = admin_client.post("/api/ingestion/batches", json={"notes": "e7-dog-inv"})
    occ = _upload_pdf(admin_client, br.json()["id"], PDF_DOG_328)
    doc = _run_adapter(admin_client, occ["id"], "fattura_doganale_v1")
    doc_id = doc["id"]

    prev = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-commit-doganale")
    body = prev.json()
    assert any(c["invoice_id"] == inv["id"] for c in body["invoice_candidates"])
    assert body["resolved_invoice_id"] is None

    cr = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-doganale",
        json={"operation_key": f"dog-nolink-{_uid()}"},
    )
    assert cr.status_code == 200, cr.text
    proc_ops = [
        o
        for o in cr.json()["operations"]
        if o.get("entity_type") in ("import_process", "process") and o.get("entity_id")
    ]
    process_id = int(proc_ops[0]["entity_id"])
    p = admin_client.get(f"/api/import-processes/{process_id}").json()
    inv_ids = [x["invoice_id"] for x in (p.get("invoices") or [])]
    assert inv["id"] not in inv_ids

    br2 = admin_client.post("/api/ingestion/batches", json={"notes": "e7-dog-link"})
    occ2 = _upload_pdf(admin_client, br2.json()["id"], PDF_DOG_328)
    doc2 = _run_adapter(admin_client, occ2["id"], "fattura_doganale_v1")
    cr3 = admin_client.post(
        f"/api/ingestion/documents/{doc2['id']}/commit-doganale",
        json={"operation_key": f"dog-link-{_uid()}", "invoice_id": inv["id"]},
    )
    assert cr3.status_code == 200, cr3.text
    proc_ops3 = [
        o
        for o in cr3.json()["operations"]
        if o.get("entity_type") in ("import_process", "process") and o.get("entity_id")
    ]
    pid3 = int(proc_ops3[0]["entity_id"])
    p3 = admin_client.get(f"/api/import-processes/{pid3}").json()
    inv_ids = [x["invoice_id"] for x in (p3.get("invoices") or [])]
    assert inv["id"] in inv_ids


# ---------------------------------------------------------------------------
# Print (E7-3)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PDF_PRINT_328.is_file(), reason="PrintDeclaration_328.pdf absent")
def test_http_print_attaches_without_second_process(admin_client):
    proc_r = admin_client.post("/api/import-processes", json={"notes": "e7-print-target"})
    assert proc_r.status_code == 201, proc_r.text
    process_id = proc_r.json()["id"]

    br = admin_client.post("/api/ingestion/batches", json={"notes": "e7-print"})
    occ_p = _upload_pdf(admin_client, br.json()["id"], PDF_PRINT_328)
    print_doc = _run_adapter(admin_client, occ_p["id"], "print_declaration_v1")
    prev = admin_client.get(
        f"/api/ingestion/documents/{print_doc['id']}/preview-commit-print",
        params={"process_id": process_id},
    )
    assert prev.status_code == 200, prev.text
    assert prev.json()["can_commit"] is True, prev.json().get("blockers")

    pr = admin_client.post(
        f"/api/ingestion/documents/{print_doc['id']}/commit-print",
        json={"operation_key": f"print-{_uid()}", "process_id": process_id},
    )
    assert pr.status_code == 200, pr.text
    assert pr.json()["status"] == "SUCCEEDED"

    pr2 = admin_client.post(
        f"/api/ingestion/documents/{print_doc['id']}/commit-print",
        json={"operation_key": f"print-again-{_uid()}", "process_id": process_id},
    )
    assert pr2.json()["id"] == pr.json()["id"]

    docs = admin_client.get(
        "/api/documents",
        params={"entity_type": "import_process", "entity_id": str(process_id)},
    )
    assert docs.status_code == 200, docs.text
    assert len(docs.json()) >= 1


# ---------------------------------------------------------------------------
# Numerário (E7-TAX)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PDF_NUM_202.is_file(), reason="Solicitacao_Numerario.pdf absent")
def test_http_numerario_create_process_registers_tax_lines(admin_client):
    br = admin_client.post("/api/ingestion/batches", json={"notes": "e7-num"})
    occ = _upload_pdf(admin_client, br.json()["id"], PDF_NUM_202)
    doc = _run_adapter(admin_client, occ["id"], "solicitacao_numerario_v1")
    doc_id = doc["id"]

    prev = admin_client.get(f"/api/ingestion/documents/{doc_id}/preview-numerario")
    assert prev.status_code == 200, prev.text
    body = prev.json()
    assert body["can_create_process"] is True
    assert "202" in (body.get("invoice_refs") or [])

    cr = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-numerario",
        json={"operation_key": f"num-{_uid()}", "process_ids": [], "create_process": True},
    )
    assert cr.status_code in (200, 201), cr.text
    result = cr.json()
    failed_ops = [
        {
            "op_key": o.get("op_key"),
            "status": o.get("status"),
            "error": o.get("error_message"),
            "details": o.get("details_json"),
        }
        for o in (result.get("operations") or [])
        if o.get("status") != "SUCCEEDED"
    ]
    assert result["status"] == "SUCCEEDED", failed_ops or result
    ops = result.get("operations") or []
    proc_op = next(
        (o for o in ops if o.get("entity_type") in ("import_process", "process") and o.get("entity_id")),
        None,
    )
    fr_op = next(
        (o for o in ops if o.get("entity_type") == "customs_funding_request" and o.get("entity_id")),
        None,
    )
    assert proc_op and fr_op
    process_id = int(proc_op["entity_id"])

    frs = admin_client.get(f"/api/import-processes/{process_id}/funding-requests")
    assert frs.status_code == 200, frs.text
    rows = frs.json()
    assert rows
    fr = rows[0]
    assert fr["status"] == "DRAFT"
    tax_codes = {t["code"] for t in fr.get("tax_lines") or []}
    for expected in ("AFRMM", "ICMS", "II", "IPI", "PIS", "COFINS"):
        assert expected in tax_codes, tax_codes

    cr2 = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/commit-numerario",
        json={"operation_key": f"num-again-{_uid()}", "process_ids": [process_id]},
    )
    assert cr2.status_code in (200, 201)
    assert cr2.json()["attempt_id"] == result["attempt_id"]

    confirmed = admin_client.post(
        f"/api/import-processes/{process_id}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    links = confirmed.json().get("payable_links") or []
    assert links
    payable_id = links[0]["payable_id"]
    pay = admin_client.get(f"/api/payables/{payable_id}")
    assert pay.status_code == 200, pay.text
    body_pay = pay.json()
    assert body_pay.get("source_type") == "CUSTOMS_FUNDING" or body_pay.get("status") in (
        "OPEN",
        "ISSUED",
        "UNPAID",
    )
    assert body_pay.get("status") != "PAID"


# ---------------------------------------------------------------------------
# Nationalization residual / over (E7-4)
# ---------------------------------------------------------------------------


def _submitted_two_items(client, *, tag: str):
    s = client.post("/api/suppliers", json={"name": f"Sup-{tag}", "country_code": "IT"}).json()
    p1 = client.post("/api/products", json={"sku": f"SKU-{tag}-A", "description": "A"}).json()
    p2 = client.post("/api/products", json={"sku": f"SKU-{tag}-B", "description": "B"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{tag}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p1["id"],
            "quantity": "10",
            "unit_price": "10",
        },
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p2["id"],
            "quantity": "20",
            "unit_price": "10",
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = _issued_invoice(client, o, number=f"INV-{tag}", qty="10")
    provider = client.post(
        "/api/logistics-providers",
        json={"legal_name": f"Carrier {tag}", "provider_type": "TRANSPORTADOR", "active": True},
    ).json()
    sh = client.post(
        "/api/shipments",
        json={"modal": "SEA", "logistics_provider_id": provider["id"]},
    ).json()
    for item in o["items"]:
        sh = client.post(
            f"/api/shipments/{sh['id']}/items",
            json={
                "expected_version": sh["version"],
                "order_item_id": item["id"],
                "quantity": item["quantity"],
            },
        ).json()
    p = client.post("/api/import-processes", json={"external_reference": f"DUIMP-TEST-{tag}"}).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": inv["id"]},
    ).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/shipments",
        json={"expected_version": p["version"], "shipment_id": sh["id"]},
    ).json()
    for si in sh["items"]:
        p = client.post(
            f"/api/import-processes/{p['id']}/shipment-items/allocate",
            json={
                "expected_version": p["version"],
                "shipment_item_id": si["id"],
                "allocated_qty": si["quantity"],
            },
        ).json()
    p = client.post(
        f"/api/import-processes/{p['id']}/submit",
        json={"expected_version": p["version"]},
    ).json()
    assert p["status"] == "SUBMITTED"
    return {"process": p, "shipment": sh, "products": [p1, p2], "order": o}


def test_nationalization_partial_residual_over_blocked(admin_client):
    ctx = _submitted_two_items(admin_client, tag=_uid()[:6])
    pid = ctx["process"]["id"]
    residuals = admin_client.get(f"/api/import-processes/{pid}/clearance-residuals")
    assert residuals.status_code == 200, residuals.text
    rows = residuals.json()
    assert len(rows) == 2
    assert all(r.get("product_sku") for r in rows)
    assert all(Decimal(r["residual_qty"]) > 0 for r in rows)

    first = rows[0]
    r = admin_client.post(f"/api/import-processes/{pid}/nationalizations", json={})
    assert r.status_code == 201, r.text
    nat = r.json()
    half = str(Decimal(first["residual_qty"]) / 2)
    r = admin_client.post(
        f"/api/import-processes/{pid}/nationalizations/{nat['id']}/items",
        json={
            "expected_version": nat["version"],
            "items": [
                {
                    "quantity": half,
                    "product_id": first["product_id"],
                    "shipment_item_id": first["shipment_item_id"],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    nat = r.json()
    r = admin_client.post(
        f"/api/import-processes/{pid}/nationalizations/{nat['id']}/confirm",
        json={"expected_version": nat["version"]},
    )
    assert r.status_code == 200, r.text
    proc = admin_client.get(f"/api/import-processes/{pid}").json()
    assert proc["status"] == "PARTIALLY_CLEARED"

    over = admin_client.post(f"/api/import-processes/{pid}/nationalizations", json={})
    nat2 = over.json()
    too_much = admin_client.post(
        f"/api/import-processes/{pid}/nationalizations/{nat2['id']}/items",
        json={
            "expected_version": nat2["version"],
            "items": [
                {
                    "quantity": "9999",
                    "product_id": first["product_id"],
                    "shipment_item_id": first["shipment_item_id"],
                }
            ],
        },
    )
    assert too_much.status_code == 409, too_much.text
    assert too_much.json().get("error") == "over_nationalization"

    left = admin_client.get(f"/api/import-processes/{pid}/clearance-residuals").json()
    remaining = [x for x in left if Decimal(x["residual_qty"]) > 0]
    assert remaining
    nat3 = admin_client.post(f"/api/import-processes/{pid}/nationalizations", json={}).json()
    items = [
        {
            "quantity": x["residual_qty"],
            "product_id": x["product_id"],
            "shipment_item_id": x["shipment_item_id"],
        }
        for x in remaining
    ]
    nat3 = admin_client.post(
        f"/api/import-processes/{pid}/nationalizations/{nat3['id']}/items",
        json={"expected_version": nat3["version"], "items": items},
    ).json()
    conf = admin_client.post(
        f"/api/import-processes/{pid}/nationalizations/{nat3['id']}/confirm",
        json={"expected_version": nat3["version"]},
    )
    assert conf.status_code == 200, conf.text
    proc = admin_client.get(f"/api/import-processes/{pid}").json()
    assert proc["status"] == "CLEARED"


def test_arch_elo7_internal_suffixes():
    from app.foundation.module_graph import INTERNAL_SUFFIXES

    assert ".doganale_commit_commands" in INTERNAL_SUFFIXES
    assert ".print_commit_commands" in INTERNAL_SUFFIXES
