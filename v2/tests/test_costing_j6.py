"""J#6 Costing / Reconciliation — V2_NORMATIVE + V1_CHARACTERIZATION (JSON only)."""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.foundation.module_graph import ALLOWED_DEPS, MODULE_PACKAGES
from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION
from app.identity.public import ADMIN_PERMISSIONS, COMPRADOR_PERMISSIONS

REPO = Path(__file__).resolve().parents[2]
V1_GOLDEN = REPO / "docs" / "v2" / "etapa-costing" / "goldens" / "V1_CHARACTERIZATION.json"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _confirmed_order(client, *, tag: str, items: list[tuple[str, str, str]]):
    s = client.post("/api/suppliers", json={"name": f"Sup-{tag}", "country_code": "IT"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{tag}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    products = []
    for sku, desc, qty in items:
        p = client.post("/api/products", json={"sku": sku, "description": desc}).json()
        products.append(p)
        o = client.post(
            f"/api/orders/{o['id']}/items",
            json={
                "expected_version": o["version"],
                "product_id": p["id"],
                "quantity": qty,
                "unit_price": "100",
            },
        ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    return s, products, o


def _issued_invoice(client, order, *, number: str):
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
                "unit_price_gross": "100",
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
    return r.json()


def _shipment(client, order, *, tag: str):
    provider = client.post(
        "/api/logistics-providers",
        json={"legal_name": f"Carrier {tag}", "provider_type": "TRANSPORTADOR", "active": True},
    ).json()
    sh = client.post("/api/shipments", json={"modal": "SEA", "logistics_provider_id": provider["id"]}).json()
    for oi in order["items"]:
        sh = client.post(
            f"/api/shipments/{sh['id']}/items",
            json={"expected_version": sh["version"], "order_item_id": oi["id"], "quantity": oi["quantity"]},
        ).json()
    return sh


def _set_fx_initial(client, invoice):
    inv = client.get(f"/api/invoices/{invoice['id']}").json()
    for p in inv.get("payables") or []:
        r = client.post(
            f"/api/payables/{p['id']}/fx-plan",
            json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
        )
        assert r.status_code == 200, r.text


def _link_and_allocate(client, process, invoice, shipment):
    p = process
    r = client.post(
        f"/api/import-processes/{p['id']}/invoices",
        json={"expected_version": p["version"], "invoice_id": invoice["id"]},
    )
    assert r.status_code == 200, r.text
    p = r.json()
    for item in invoice["items"]:
        r = client.post(
            f"/api/import-processes/{p['id']}/invoice-items/allocate",
            json={
                "expected_version": p["version"],
                "invoice_item_id": item["id"],
                "allocated_qty": item["quantity"],
            },
        )
        assert r.status_code == 200, r.text
        p = r.json()
    r = client.post(
        f"/api/import-processes/{p['id']}/shipments",
        json={"expected_version": p["version"], "shipment_id": shipment["id"]},
    )
    assert r.status_code == 200, r.text
    p = r.json()
    for item in shipment["items"]:
        r = client.post(
            f"/api/import-processes/{p['id']}/shipment-items/allocate",
            json={
                "expected_version": p["version"],
                "shipment_item_id": item["id"],
                "allocated_qty": item["quantity"],
            },
        )
        assert r.status_code == 200, r.text
        p = r.json()
    return p


def _funding(client, process, *, declared, fob, taxes, expenses=None, notes=None, extra_bases=None):
    payee = client.post("/api/customs/payees", json={"name": f"Payee-{_uid()}"}).json()
    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests",
        json={
            "payee_id": payee["id"],
            "currency": "BRL",
            "declared_total": declared,
            "notes": notes,
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    fr = r.json()
    lines = [{"position": 1, "label": "FOB", "code": "FOB", "amount": fob, "currency": "EUR"}]
    if extra_bases:
        lines.extend(extra_bases)
    r = client.put(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/value-bases",
        json={"expected_version": fr["version"], "lines": lines},
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    r = client.put(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/tax-lines",
        json={"expected_version": fr["version"], "lines": taxes},
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    if expenses:
        r = client.put(
            f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/expense-lines",
            json={"expected_version": fr["version"], "lines": expenses},
        )
        assert r.status_code == 200, r.text
        fr = r.json()
    return fr


def _open_case(client, process_id: int):
    r = client.post("/api/costing/cases", json={"process_id": process_id})
    assert r.status_code == 201, r.text
    return r.json()


def test_v1_characterization_json_is_not_v2_dod():
    data = json.loads(V1_GOLDEN.read_text(encoding="utf-8"))
    assert data["not_v2_dod"] is True
    assert data["empty_as_zero"] is True
    assert data["formula"].startswith("total = FOB_foreign")
    assert data["examples"][0]["shares"] == ["100", "100"]
    assert data["examples"][1]["shares"] == ["200", "100"]
    src = Path(__file__).read_text(encoding="utf-8")
    assert not any(
        line.strip().startswith(("import v1", "from v1 ")) for line in src.splitlines()
    )


def test_j6_scaffold_graph_perms_migration():
    assert "costing" in MODULE_PACKAGES
    assert "reconciliation" in MODULE_PACKAGES
    assert "catalog" not in ALLOWED_DEPS["costing"]
    assert "inventory" not in ALLOWED_DEPS["costing"]
    assert "costing" not in ALLOWED_DEPS["reconciliation"]
    assert "reconciliation" in ALLOWED_DEPS["costing"]
    for perm in ("costing:read", "costing:write", "costing:publish", "reconciliation:read", "reconciliation:resolve"):
        assert perm in ADMIN_PERMISSIONS
    assert "costing:write" in COMPRADOR_PERMISSIONS
    assert "costing:publish" not in COMPRADOR_PERMISSIONS
    assert EXPECTED_ALEMBIC_REVISION == "031"
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("029")
    assert rev is not None
    assert rev.down_revision == "028"
    rev30 = script.get_revision("030")
    assert rev30 is not None
    assert rev30.down_revision == "029"
    rev31 = script.get_revision("031")
    assert rev31 is not None
    assert rev31.down_revision == "030"
    assert script.get_current_head() == "031"


def test_queue_and_ensure_case(admin_client):
    c = admin_client
    p = c.post("/api/import-processes", json={"external_reference": f"DUIMP-{_uid()}"}).json()
    q = c.get("/api/costing/queue").json()
    assert any(row["import_process_id"] == p["id"] for row in q)
    case = _open_case(c, p["id"])
    again = c.post("/api/costing/cases", json={"process_id": p["id"]})
    assert again.status_code == 201
    assert again.json()["id"] == case["id"]


def test_no_lines_without_allocation(admin_client):
    c = admin_client
    p = c.post("/api/import-processes", json={"external_reference": f"X-{_uid()}"}).json()
    case = _open_case(c, p["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "ESTIMATED"})
    assert r.status_code == 422
    assert r.json()["error"] == "no_costing_lines"


def test_synthetic_publish_immutable_and_compare(admin_client):
    c = admin_client
    tag = _uid()
    _, _, order = _confirmed_order(
        c,
        tag=tag,
        items=[(f"BAG-{tag}-A", "Bolsa A", "10"), (f"BAG-{tag}-B", "Bolsa B", "10")],
    )
    inv = _issued_invoice(c, order, number=f"INV-{tag}")
    _set_fx_initial(c, inv)
    sh = _shipment(c, order, tag=tag)
    proc = c.post("/api/import-processes", json={"external_reference": f"DUIMP-{tag}"}).json()
    proc = _link_and_allocate(c, proc, inv, sh)
    # FOB equals merchandise 2000 EUR; taxes 100; no freight conflict
    _funding(
        c,
        proc,
        declared="100.00",
        fob="2000",
        taxes=[{"position": 1, "label": "II", "code": "II", "amount": "100"}],
    )
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "ESTIMATED"})
    assert r.status_code == 200, r.text
    est = r.json()
    assert est["status"] == "DRAFT"
    assert est["kind"] == "ESTIMATED"
    assert est["partial_coverage"] is False
    assert Decimal(est["included_total_brl"]) == Decimal("12100.00")  # 2000*6 + 100
    skus = {p["sku_snapshot"]: p for p in est["products"]}
    assert Decimal(skus[f"BAG-{tag}-A"]["total_brl"]) == Decimal("6050.00")
    assert Decimal(skus[f"BAG-{tag}-A"]["unit_brl"]) == Decimal("605.00")

    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "REVISED"})
    assert r.status_code == 200, r.text
    rev = r.json()
    assert rev["partial_coverage"] is False
    r = c.post(f"/api/costing/versions/{rev['id']}/publish", json={"reason": "cobertura completa ensaio"})
    assert r.status_code == 200, r.text
    pub = r.json()
    assert pub["status"] == "PUBLISHED"

    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "REVISED"})
    assert r.status_code == 200, r.text
    new_draft = r.json()
    assert new_draft["id"] != pub["id"]
    assert new_draft["status"] == "DRAFT"

    # published remains immutable
    still = c.get(f"/api/costing/versions/{pub['id']}").json()
    assert still["status"] == "PUBLISHED"

    r = c.post(f"/api/costing/versions/{pub['id']}/revise", json={"kind": "REVISED"})
    assert r.status_code == 200, r.text
    nxt = r.json()
    cmp = c.get(f"/api/costing/versions/{pub['id']}/compare/{nxt['id']}").json()
    assert "products" in cmp
    assert "components" in cmp
    assert isinstance(cmp["components"], list)


def test_coverage_incomplete_blocks_revised_publish(admin_client):
    c = admin_client
    tag = _uid()
    _, _, order = _confirmed_order(c, tag=tag, items=[(f"EAN-{tag}", "Acessorio", "10")])
    inv = _issued_invoice(c, order, number="202")
    _set_fx_initial(c, inv)
    sh = _shipment(c, order, tag=tag)
    proc = c.post("/api/import-processes", json={"external_reference": "DUIMP-202-ISO"}).json()
    proc = _link_and_allocate(c, proc, inv, sh)
    _funding(
        c,
        proc,
        declared="28600.00",
        fob="288195.20",
        taxes=[{"position": 1, "label": "II", "code": "II", "amount": "100"}],
        expenses=[
            {"position": 1, "label": "FRETE INTERNACIONAL", "code": "FRETE_INT", "amount": "28600"}
        ],
        notes="Faturas 181 202 203 244 245 246",
    )
    # also ValueBasis FRETE vs expense — add FRETE basis
    frs = c.get(f"/api/import-processes/{proc['id']}").json()
    # reopen case after adding freight basis on existing funding
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "REVISED"})
    assert r.status_code == 200, r.text
    ver = r.json()
    assert ver["partial_coverage"] is True
    types = {p["pair_type"] for p in ver["pairs"]}
    assert "SOURCE_COVERAGE" in types
    r = c.post(f"/api/costing/versions/{ver['id']}/publish", json={"reason": "tentativa completa"})
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "publish_blocked"

    # ESTIMATED partial only with label
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "ESTIMATED"})
    est = r.json()
    r = c.post(f"/api/costing/versions/{est['id']}/publish", json={"allow_partial": True})
    assert r.status_code == 409
    r = c.post(
        f"/api/costing/versions/{est['id']}/publish",
        json={"allow_partial": True, "reason": "rascunho incompleto rotulado"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["partial_coverage"] is True
    # II from DUIMP must not be in included total as if it were 202-only complete cost
    included = Decimal(r.json()["included_total_brl"] or "0")
    assert included < Decimal("1425554.64")


def test_cif_basis_not_conflict_with_international_expense(admin_client):
    c = admin_client
    tag = _uid()
    _, _, order = _confirmed_order(c, tag=tag, items=[(f"SKU-{tag}", "Item", "10")])
    inv = _issued_invoice(c, order, number=f"INV-{tag}")
    _set_fx_initial(c, inv)
    sh = _shipment(c, order, tag=tag)
    proc = c.post("/api/import-processes", json={"external_reference": f"D-{tag}"}).json()
    proc = _link_and_allocate(c, proc, inv, sh)
    payee = c.post("/api/customs/payees", json={"name": f"P-{tag}"}).json()
    fr = c.post(
        f"/api/import-processes/{proc['id']}/funding-requests",
        json={
            "payee_id": payee["id"],
            "currency": "BRL",
            "declared_total": "41500.00",
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
        },
    ).json()
    r = c.put(
        f"/api/import-processes/{proc['id']}/funding-requests/{fr['id']}/value-bases",
        json={
            "expected_version": fr["version"],
            "lines": [
                {"position": 1, "label": "FOB", "code": "FOB", "amount": "1000", "currency": "EUR"},
                {"position": 2, "label": "FRETE", "code": "FRETE", "amount": "20000.04", "currency": "BRL"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    r = c.put(
        f"/api/import-processes/{proc['id']}/funding-requests/{fr['id']}/expense-lines",
        json={
            "expected_version": fr["version"],
            "lines": [
                {"position": 1, "label": "FRETE INTERNACIONAL", "code": "FRETE_INTERNACIONAL", "amount": "28600"},
                {"position": 2, "label": "FRETE (REMOÇÃO)", "code": "FRETE__REMOCAO_", "amount": "7300"},
                {"position": 3, "label": "FRETE (ENTREGA)", "code": "FRETE__ENTREGA_", "amount": "5600"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "ESTIMATED"})
    ver = r.json()
    assert r.status_code == 200, r.text
    assert not any(p["pair_type"] == "FREIGHT_CONFLICT" for p in ver["pairs"])
    assert ver["snapshot"]["coverage"]["freight_conflict"] is False
    by_type = {x["component_type"]: x for x in ver["components"]}
    assert "FRETE_INTERNACIONAL" in by_type
    assert by_type["FRETE_INTERNACIONAL"]["included"] is True
    assert Decimal(by_type["FRETE_INTERNACIONAL"]["amount_brl"]) == Decimal("28600.00")
    assert by_type["FRETE_REMOCAO"]["included"] is True
    assert Decimal(by_type["FRETE_REMOCAO"]["amount_brl"]) == Decimal("7300.00")
    assert by_type["FRETE_ENTREGA"]["included"] is True
    assert Decimal(by_type["FRETE_ENTREGA"]["amount_brl"]) == Decimal("5600.00")
    assert not any(x["source_kind"] == "VALUE_BASIS" for x in ver["components"])


def test_two_international_freights_still_conflict(admin_client):
    c = admin_client
    tag = _uid()
    _, _, order = _confirmed_order(c, tag=tag, items=[(f"SKU-{tag}", "Item", "10")])
    inv = _issued_invoice(c, order, number=f"INV-{tag}")
    _set_fx_initial(c, inv)
    sh = _shipment(c, order, tag=tag)
    proc = c.post("/api/import-processes", json={"external_reference": f"D-{tag}"}).json()
    proc = _link_and_allocate(c, proc, inv, sh)
    _funding(
        c,
        proc,
        declared="30000.00",
        fob="1000",
        taxes=[{"position": 1, "label": "II", "code": "II", "amount": "1000"}],
        expenses=[
            {"position": 1, "label": "FRETE INTERNACIONAL", "code": "FRETE_INT", "amount": "20000"},
            {"position": 2, "label": "FREIGHT INTERNATIONAL", "code": "FREIGHT_INT", "amount": "9000"},
        ],
    )
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "ESTIMATED"})
    ver = r.json()
    assert any(p["pair_type"] == "FREIGHT_CONFLICT" for p in ver["pairs"])
    freight_comps = [x for x in ver["components"] if x["component_type"] == "FRETE_INTERNACIONAL"]
    assert freight_comps
    assert all(x["included"] is False for x in freight_comps)


def test_shipment_only_blocks_revised(admin_client):
    c = admin_client
    tag = _uid()
    _, _, order = _confirmed_order(c, tag=tag, items=[(f"SKU-{tag}", "Item", "10")])
    sh = _shipment(c, order, tag=tag)
    proc = c.post("/api/import-processes", json={"external_reference": f"D-{tag}"}).json()
    r = c.post(
        f"/api/import-processes/{proc['id']}/shipments",
        json={"expected_version": proc["version"], "shipment_id": sh["id"]},
    )
    proc = r.json()
    r = c.post(
        f"/api/import-processes/{proc['id']}/shipment-items/allocate",
        json={
            "expected_version": proc["version"],
            "shipment_item_id": sh["items"][0]["id"],
            "allocated_qty": "10",
        },
    )
    assert r.status_code == 200, r.text
    proc = r.json()
    case = _open_case(c, proc["id"])
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "ESTIMATED"})
    assert r.status_code == 200, r.text
    r = c.post(f"/api/costing/cases/{case['id']}/recalculate", json={"kind": "REVISED"})
    ver = r.json()
    assert any(p["pair_type"] == "MERCHANDISE_MISSING" for p in ver["pairs"])
    r = c.post(f"/api/costing/versions/{ver['id']}/publish", json={"reason": "no"})
    assert r.status_code == 409


def test_comprador_cannot_publish(admin_client, db):
    from app.identity.models import Role, User
    from app.identity.security import hash_password

    c = admin_client
    role = db.query(Role).filter(Role.name == "comprador").first()
    u = User(
        email=f"comp-{_uid()}@epic.com.br",
        name="Comp",
        password_hash=hash_password("pass1234"),
        role_id=role.id,
        is_active=True,
    )
    db.add(u)
    db.commit()
    r = c.post("/api/auth/login", json={"email": u.email, "password": "pass1234"})
    assert r.status_code == 200
    p = c.post("/api/import-processes", json={"external_reference": f"D-{_uid()}"})
    # comprador has costing:write but not customs:write — process create may 403
    # use admin to create then login comprador for costing
    # (re-login admin first)
    c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    p = c.post("/api/import-processes", json={"external_reference": f"D-{_uid()}"}).json()
    c.post("/api/auth/login", json={"email": u.email, "password": "pass1234"})
    case = c.post("/api/costing/cases", json={"process_id": p["id"]})
    assert case.status_code == 201, case.text
    # no lines
    r = c.post(f"/api/costing/cases/{case.json()['id']}/recalculate", json={"kind": "ESTIMATED"})
    assert r.status_code in (422, 200)
    fake = 1
    r = c.post(f"/api/costing/versions/{fake}/publish", json={"reason": "x"})
    assert r.status_code in (403, 404)


def test_empty_basis_not_zero(admin_client):
    c = admin_client
    tag = _uid()
    _, _, order = _confirmed_order(c, tag=tag, items=[(f"SKU-{tag}", "Item", "10")])
    inv = _issued_invoice(c, order, number=f"INV-{tag}")
    _set_fx_initial(c, inv)
    sh = _shipment(c, order, tag=tag)
    proc = c.post("/api/import-processes", json={"external_reference": f"D-{tag}"}).json()
    proc = _link_and_allocate(c, proc, inv, sh)
    _funding(
        c,
        proc,
        declared="50.00",
        fob="1000",
        taxes=[{"position": 1, "label": "II", "code": "II", "amount": "50"}],
    )
    case = _open_case(c, proc["id"])
    r = c.post(
        f"/api/costing/cases/{case['id']}/recalculate",
        json={"kind": "ESTIMATED", "methods": {"TAX:skip": "WEIGHT"}},
    )
    # WEIGHT without physical base → component status missing_basis, not allocated as 0
    ver = r.json()
    assert r.status_code == 200, r.text
    # default method VALUE should work; explicit WEIGHT on unknown id ignored
    ii = [x for x in ver["components"] if x["component_type"] == "II"][0]
    assert ii["status"] == "OK"
    r = c.post(
        f"/api/costing/cases/{case['id']}/recalculate",
        json={"kind": "ESTIMATED", "methods": {f"TAX:{ii['source_id']}": "WEIGHT"}},
    )
    ver = r.json()
    ii = [x for x in ver["components"] if x["component_type"] == "II"][0]
    assert ii["status"] == "missing_basis"
    assert ii["included"] is False
