"""Elo 9 — cobertura 6 faturas, papéis de frete, sku ≠ ean."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from app.costing.freight import (
    ROLE_CUSTOMS_BASIS,
    ROLE_DOMESTIC_DELIVERY,
    ROLE_DOMESTIC_REMOVAL,
    ROLE_INTERNATIONAL,
    classify_freight_role,
)
from test_costing_j6 import (
    REPO,
    _link_and_allocate,
    _open_case,
    _uid,
)

E9_FOB = "288195.20"
E9_DECLARED = "1425554.64"
E9_TAXES = "1361123.64"
E9_FX = "5.9205"
E9_NOTES = "INV. 181/202/203/244/245/246"
E9_INVOICES = (
    ("181", "173217.30"),
    ("202", "30188.00"),
    ("203", "1824.50"),
    ("244", "19966.00"),
    ("245", "61424.40"),
    ("246", "1575.00"),
)
MANIFEST = REPO / "docs" / "v2" / "etapa-elo-9" / "E9_FIXTURE_MANIFEST.json"


def test_freight_roles_are_semantic_not_regex():
    assert classify_freight_role("FRETE", "FRETE", source="value_basis") == ROLE_CUSTOMS_BASIS
    assert (
        classify_freight_role("FRETE_INTERNACIONAL", "FRETE INTERNACIONAL", source="expense")
        == ROLE_INTERNATIONAL
    )
    assert classify_freight_role("FRETE__REMOCAO_", "FRETE (REMOÇÃO)", source="expense") == ROLE_DOMESTIC_REMOVAL
    assert classify_freight_role("FRETE__ENTREGA_", "FRETE (ENTREGA)", source="expense") == ROLE_DOMESTIC_DELIVERY
    assert classify_freight_role("FRETE", "FRETE", source="expense") is None


def test_e9_fixture_pdfs_sha():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["files"]
    for row in data["files"]:
        path = REPO / row["file"].replace("\\", "/")
        assert path.is_file(), path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == row["sha256"], row["file"]


def _e9_product(client, *, sku: str, description: str, ean: str):
    assert sku != ean
    assert not sku.isdigit()
    listed = client.get("/api/catalog/product-list", params={"ean": ean, "limit": 5})
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items") or []
    if len(items) == 1:
        row = items[0]
        assert row["sku"] != ean
        return row
    r = client.post("/api/products", json={"sku": sku, "description": description})
    assert r.status_code == 201, r.text
    row = r.json()
    r = client.patch(f"/api/products/{row['id']}", json={"ean": ean})
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["sku"] != row["ean"]
    assert row["ean"] == ean
    return row


def _priced_invoice(client, order, *, number: str, unit_price: str, rate: str = E9_FX):
    inv = client.post(
        f"/api/orders/{order['id']}/invoices",
        json={"invoice_number": number, "invoice_type": "FINAL"},
    ).json()
    payload_items = []
    for oi in order["items"]:
        payload_items.append(
            {
                "order_item_id": oi["id"],
                "quantity": oi["quantity"],
                "unit_price_gross": unit_price,
                "discount_type": "PERCENT",
                "discount_percent": "0",
            }
        )
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={"expected_version": inv["version"], "items": payload_items},
    ).json()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "PERCENT",
            "terms": [{"due_date": (date.today() + timedelta(days=30)).isoformat(), "percent": "100"}],
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
    inv = r.json()
    for p in inv.get("payables") or []:
        fx = client.post(
            f"/api/payables/{p['id']}/fx-plan",
            json={"kind": "INITIAL", "rate": rate, "effective_from": date.today().isoformat()},
        )
        assert fx.status_code == 200, fx.text
    return client.get(f"/api/invoices/{inv['id']}").json()


def _e9_family(client, supplier_id, *, tag: str, number: str, net: str):
    sku = f"ENSAIO-E9-F{number}-{tag}"
    ean = f"8000000000{number.zfill(3)}"[:13]
    product = _e9_product(client, sku=sku, description=f"Ensaio Fattura {number}", ean=ean)
    o = client.post(
        "/api/orders",
        json={
            "code": f"ENSAIO-E9-F{number}-{tag}",
            "supplier_id": supplier_id,
            "currency": "EUR",
            "notes": "Pedido de ensaio Elo 9 — não é Ordine do fornecedor",
        },
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": product["id"],
            "quantity": "1",
            "unit_price": net,
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = _priced_invoice(client, o, number=f"{number}-{tag}", unit_price=net)
    provider = client.post(
        "/api/logistics-providers",
        json={"legal_name": f"Fwd {number}-{tag}", "provider_type": "TRANSPORTADOR", "active": True},
    ).json()
    sh = client.post("/api/shipments", json={"modal": "SEA", "logistics_provider_id": provider["id"]}).json()
    sh = client.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": o["items"][0]["id"], "quantity": "1"},
    ).json()
    return product, o, inv, sh


def _e9_funding(client, process):
    from test_costing_j6 import _funding

    return _funding(
        client,
        process,
        declared=E9_DECLARED,
        fob=E9_FOB,
        extra_bases=[
            {
                "position": 2,
                "label": "FRETE",
                "code": "FRETE",
                "amount": "20000.04",
                "currency": "BRL",
            }
        ],
        taxes=[{"position": 1, "label": "II", "code": "II", "amount": E9_TAXES}],
        expenses=[
            {"position": 1, "label": "FRETE INTERNACIONAL", "code": "FRETE_INTERNACIONAL", "amount": "28600.00"},
            {"position": 2, "label": "FRETE (REMOÇÃO)", "code": "FRETE__REMOCAO_", "amount": "7300.00"},
            {"position": 3, "label": "FRETE (ENTREGA)", "code": "FRETE__ENTREGA_", "amount": "5600.00"},
            {"position": 4, "label": "HONORÁRIOS", "code": "HONORARIOS", "amount": "22931.00"},
        ],
        notes=E9_NOTES,
    )


def test_sku_not_ean_bind_by_ean_field(admin_client):
    c = admin_client
    tag = _uid()
    ean = f"80576289{int(tag, 16) % 100000:05d}"
    sku = f"ENSAIO-E9-SHOW-{tag}"
    p = _e9_product(c, sku=sku, description="SHOW ensaio", ean=ean)
    assert p["sku"] == sku
    assert p["ean"] == ean
    assert p["sku"] != p["ean"]
    listed = c.get("/api/catalog/product-list", params={"ean": ean}).json()["items"]
    assert listed[0]["id"] == p["id"]
    again = _e9_product(c, sku=f"ENSAIO-E9-OTHER-{tag}", description="não duplicar", ean=ean)
    assert again["id"] == p["id"]


def test_trial_order_code_is_not_ordine(admin_client):
    c = admin_client
    tag = _uid()
    s = c.post("/api/suppliers", json={"name": f"Heroes-e9-{tag}", "country_code": "IT"}).json()
    _, order, _, _ = _e9_family(c, s["id"], tag=tag, number="181", net="173217.30")
    assert order["code"].startswith("ENSAIO-E9-F181")
    assert "não é Ordine" in (order.get("notes") or "")
    assert order["status"] == "CONFIRMED"


def test_six_invoices_fob_complete_and_freight_roles(admin_client):
    c = admin_client
    tag = _uid()
    s = c.post("/api/suppliers", json={"name": f"Heroes-e9-{tag}", "country_code": "IT"}).json()
    families = []
    for number, net in E9_INVOICES:
        families.append(_e9_family(c, s["id"], tag=tag, number=number, net=net))
    proc = c.post("/api/import-processes", json={"external_reference": f"E9-{tag}"}).json()
    for _p, _o, inv, sh in families:
        proc = _link_and_allocate(c, proc, inv, sh)
        assert _p["sku"] != _p["ean"]
    _e9_funding(c, proc)
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "REVISED"})
    assert r.status_code == 200, r.text
    ver = r.json()
    cov = ver["snapshot"]["coverage"]
    assert cov["coverage"] == "COMPLETE"
    assert ver["partial_coverage"] is False
    family_nums = {str(n).split("-", 1)[0] for n in cov["process_invoice_numbers"]}
    assert family_nums == {n for n, _ in E9_INVOICES}
    assert cov["extra_refs"] == []
    assert Decimal(cov["merchandise_foreign"]) == Decimal(E9_FOB)
    assert cov["freight_conflict"] is False
    assert not any(p["pair_type"] == "FREIGHT_CONFLICT" for p in ver["pairs"])
    by_type = {x["component_type"]: x for x in ver["components"]}
    assert by_type["FRETE_INTERNACIONAL"]["included"] is True
    assert Decimal(by_type["FRETE_INTERNACIONAL"]["amount_brl"]) == Decimal("28600.00")
    assert by_type["FRETE_REMOCAO"]["included"] is True
    assert by_type["FRETE_ENTREGA"]["included"] is True
    assert not any(x["source_kind"] == "VALUE_BASIS" for x in ver["components"])
    fx = ver["snapshot"].get("fx") or {}
    assert fx.get("kind") in ("documental", "parcial")
    assert fx.get("documentary_rate")
    products = ver["products"]
    assert products
    for row in products:
        assert row["sku_snapshot"].startswith("ENSAIO-E9-")
        assert row.get("merchandise_brl")
        assert Decimal(row["total_brl"]) == (
            Decimal(row["merchandise_brl"])
            + Decimal(row["freight_brl"])
            + Decimal(row["tax_brl"])
            + Decimal(row["expense_brl"])
        )
    r = c.post(
        f"/api/costing/versions/{ver['id']}/publish",
        json={"reason": "Elo 9 custo revisado documental — não é realizado"},
    )
    assert r.status_code == 200, r.text
    pub = r.json()
    assert pub["status"] == "PUBLISHED"
    assert pub["kind"] == "REVISED"
    still = c.get(f"/api/costing/versions/{pub['id']}").json()
    assert still["status"] == "PUBLISHED"


def test_five_of_six_invoices_incomplete(admin_client):
    c = admin_client
    tag = _uid()
    s = c.post("/api/suppliers", json={"name": f"Heroes-e9-{tag}", "country_code": "IT"}).json()
    families = []
    for number, net in E9_INVOICES[:5]:
        families.append(_e9_family(c, s["id"], tag=tag, number=number, net=net))
    proc = c.post("/api/import-processes", json={"external_reference": f"E9-5-{tag}"}).json()
    for _p, _o, inv, sh in families:
        proc = _link_and_allocate(c, proc, inv, sh)
    _e9_funding(c, proc)
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "REVISED"})
    ver = r.json()
    assert ver["partial_coverage"] is True
    assert "246" in ver["snapshot"]["coverage"]["extra_refs"]
    r = c.post(f"/api/costing/versions/{ver['id']}/publish", json={"reason": "não fecha"})
    assert r.status_code == 409


def test_a0_policy_a_needs_explicit_trial_order(admin_client):
    from test_j4_fin3b import _commit_a, _ingest_fattura_244, _preview_a

    c = admin_client
    tag = _uid()
    ean = "8057628953586"
    product = _e9_product(c, sku=f"ENSAIO-E9-SHOW-{tag}", description="RACCHETTA BT 2026 SHOW", ean=ean)
    assert product["sku"] != ean
    s = c.post("/api/suppliers", json={"name": f"Heroes-a0-{tag}", "country_code": "IT"}).json()
    o = c.post(
        "/api/orders",
        json={
            "code": f"ENSAIO-E9-F244-{tag}",
            "supplier_id": s["id"],
            "currency": "EUR",
            "notes": "Pedido de ensaio Elo 9 — não é Ordine do fornecedor",
        },
    ).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": product["id"],
            "quantity": "200",
            "unit_price": "99.83",
        },
    ).json()
    o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    doc_id = _ingest_fattura_244(c)
    blocked = c.post(
        f"/api/ingestion/documents/{doc_id}/commit-fattura",
        json={"operation_key": f"e9-no-oid-{doc_id}", "policy": "A"},
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json().get("error") == "order_id_required"
    preview = _preview_a(c, doc_id, o["id"])
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_commit"] is True
    r = _commit_a(c, doc_id, o["id"], f"e9-a0-{doc_id}")
    assert r.status_code == 200, r.text
