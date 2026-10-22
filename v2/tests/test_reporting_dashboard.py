"""J#7 painel — registry, snapshot, ACL, views."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path

from app.identity.models import Role, User
from app.identity.security import hash_password
from app.reporting.registry import (
    METRICS,
    ROLE_DEFAULT_PRESET,
    render_catalog_markdown,
    validate_registry,
)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _login_role(admin_client, db, role_name: str):
    role = db.query(Role).filter(Role.name == role_name).first()
    assert role is not None
    email = f"{role_name}-{_uid()}@epic.com.br"
    u = User(
        email=email,
        name=role_name,
        password_hash=hash_password("pass1234"),
        role_id=role.id,
        is_active=True,
    )
    db.add(u)
    db.commit()
    r = admin_client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    assert r.status_code == 200, r.text
    return admin_client


def test_registry_labels_and_delta_policy():
    validate_registry()
    for m in METRICS:
        assert m.label
        assert m.unit_label
        assert m.short_description
        assert "Fila AP" not in m.label
        if m.time_basis in (None, "as_of"):
            assert m.delta_policy == "none"
        if m.metric_id.startswith("ap.") is False:
            continue


def test_registry_markdown_drift():
    path = Path(__file__).resolve().parents[2] / "docs" / "v2" / "etapa-j7" / "METRIC_CATALOG.md"
    generated = render_catalog_markdown()
    assert path.exists(), "gerar METRIC_CATALOG.md a partir do registry"
    assert path.read_text(encoding="utf-8") == generated


def test_metric_catalog_and_dashboard_admin(admin_client):
    c = admin_client
    cat = c.get("/api/reporting/metric-catalog")
    assert cat.status_code == 200, cat.text
    body = cat.json()
    ids = {m["metric_id"] for m in body["metrics"]}
    assert "attention.inbox" in ids
    assert "ap.next_7d" in ids
    assert "ap.cash_committed" in ids
    assert "treasury.fx_exposure" in ids
    assert "goods.flow" in ids
    assert "orders.billing_progress" in ids
    labels = [m["label"] for m in body["metrics"]]
    assert all("Fila AP" not in x for x in labels)

    dash = c.get("/api/reporting/dashboard", params={"view": "executiva"})
    assert dash.status_code == 200, dash.text
    snap = dash.json()
    assert snap["base_preset"] == "executiva"
    assert snap["filters"]["period"] == "next_90"
    assert snap["lane"]["lane"] == "test"
    assert snap["lane"]["includes_trial_mass"] is True
    wids = [w["widget_id"] for w in snap["widgets"]]
    assert "attention.inbox" in wids
    assert "ap.cash_committed" in wids
    assert "treasury.fx_exposure" in wids
    assert "goods.flow" in wids
    assert "orders.billing_progress" in wids
    assert "ap.overdue" in wids
    assert "ap.cash_due" in wids
    assert "orders.to_invoice" in wids
    assert "import.situation" not in wids
    assert "costing.operational_published" not in wids
    assert "ap.next_7d" not in wids
    assert "catalog.quality" not in wids
    assert "ap.top_n" not in wids
    assert "treasury.fx_quote" not in wids
    assert all(w["status"] != "PARTIAL" for w in snap["widgets"])
    assert all("previous_value" not in w for w in snap["widgets"])
    flow = next(w for w in snap["widgets"] if w["widget_id"] == "goods.flow")
    assert flow["display"].get("not_a_funnel") is True
    assert "Não é o mesmo conjunto de peças" in flow["display"].get("disclaimer", "")
    cash = next(w for w in snap["widgets"] if w["widget_id"] == "ap.cash_committed")
    assert cash["display"].get("includes_overdue") is True
    assert set((cash["display"].get("labels") or {})).issuperset({"overdue", "m0", "m1", "m2"})
    fx = next(w for w in snap["widgets"] if w["widget_id"] == "treasury.fx_exposure")
    if fx["display"].get("empty"):
        assert "moeda estrangeira" in (fx["display"].get("message") or "")
    quote_fin = c.get("/api/reporting/dashboard", params={"view": "financeiro"}).json()
    fxq = next(w for w in quote_fin["widgets"] if w["widget_id"] == "treasury.fx_quote")
    if fxq["display"].get("unavailable"):
        assert fxq["display"]["message"] == "Cotação indisponível"


def test_dashboard_filters_echo_querystring(admin_client):
    today = date.today().isoformat()
    r = admin_client.get(
        "/api/reporting/dashboard",
        params={"view": "financeiro", "date_from": today, "currency": "EUR"},
    )
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["filters"]["date_from"] == today
    assert snap["filters"]["currency"] == "EUR"
    ap = next(w for w in snap["widgets"] if w["widget_id"] == "ap.next_7d")
    assert "date_from" in ap["filters_applied"]
    assert "currency" in ap["filters_applied"]
    aging = next(w for w in snap["widgets"] if w["widget_id"] == "ap.aging_bar")
    assert aging["kind"] == "aging_bar"
    assert "kpis_by_currency" in aging["display"]


def test_views_crud_and_conflict(admin_client):
    c = admin_client
    created = c.post(
        "/api/reporting/views",
        json={"name": f"Meu painel {_uid()}", "base_preset": "executiva", "is_default": True},
    )
    assert created.status_code == 200, created.text
    view = created.json()
    assert view["version"] == 1
    listed = c.get("/api/reporting/views")
    assert any(v["id"] == view["id"] for v in listed.json())

    bad = c.patch(
        f"/api/reporting/views/{view['id']}",
        json={"version": 99, "name": "x"},
    )
    assert bad.status_code == 409

    ok = c.patch(
        f"/api/reporting/views/{view['id']}",
        json={"version": 1, "name": "Painel pessoal"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["version"] == 2

    restored = c.post(
        f"/api/reporting/views/{view['id']}/restore",
        json={"version": 2},
    )
    assert restored.status_code == 200, restored.text

    gone = c.delete(f"/api/reporting/views/{view['id']}")
    assert gone.status_code == 200


def test_comprador_default_comercial_and_can_open_financeiro(admin_client, db):
    c = _login_role(admin_client, db, "comprador")
    me = c.get("/api/auth/me")
    assert me.status_code == 200
    assert "reporting:read" in me.json()["permissions"]
    dash = c.get("/api/reporting/dashboard")
    assert dash.status_code == 200, dash.text
    assert dash.json()["default_preset"] == ROLE_DEFAULT_PRESET["comprador"]
    assert dash.json()["base_preset"] == "comercial"
    fin = c.get("/api/reporting/dashboard", params={"view": "financeiro"})
    assert fin.status_code == 200, fin.text
    wids = [w["widget_id"] for w in fin.json()["widgets"]]
    assert "ap.next_7d" in wids
    cat = c.get("/api/reporting/metric-catalog").json()
    assert any(m["metric_id"] == "ap.next_7d" for m in cat["metrics"])


def test_aduana_no_ap_payload(admin_client, db):
    c = _login_role(admin_client, db, "aduana")
    dash = c.get("/api/reporting/dashboard", params={"view": "aduana"})
    assert dash.status_code == 200, dash.text
    wids = [w["widget_id"] for w in dash.json()["widgets"]]
    assert "ap.next_7d" not in wids
    assert "ap.top_n" not in wids
    cat = c.get("/api/reporting/metric-catalog").json()
    assert not any(m["metric_id"].startswith("ap.") for m in cat["metrics"])
    ap = c.get("/api/reporting/ap-queue")
    assert ap.status_code == 403


def test_estoque_inventory_widget(admin_client, db):
    c = _login_role(admin_client, db, "estoque")
    dash = c.get("/api/reporting/dashboard", params={"view": "estoque"})
    assert dash.status_code == 200, dash.text
    wids = [w["widget_id"] for w in dash.json()["widgets"]]
    assert "inventory.overview" in wids
    assert "ap.next_7d" not in wids
    ov = next(w for w in dash.json()["widgets"] if w["widget_id"] == "inventory.overview")
    sku_n = int(ov["display"].get("sku_with_balance") or 0)
    assert ov["display"].get("empty") is (sku_n == 0)
    if sku_n == 0:
        assert ov["display"].get("empty") is True


def test_attention_empty_copy_not_sem_pendencias(admin_client):
    r = admin_client.get("/api/reporting/dashboard", params={"view": "executiva"})
    inbox = next(w for w in r.json()["widgets"] if w["widget_id"] == "attention.inbox")
    copy = inbox["display"].get("empty_copy") or ""
    assert "Sem pendências" not in copy
    src = Path(__file__).resolve().parents[1] / "app" / "reporting" / "dashboard.py"
    text = src.read_text(encoding="utf-8")
    assert "Nada precisa da sua decisão agora." in text
    assert "Nenhuma importação em andamento" in text
    assert "Nenhum custo operacional publicado" in text
    assert "Nenhum saldo com quantidade" in text


def test_view_rejects_unknown_widget(admin_client):
    r = admin_client.post(
        "/api/reporting/views",
        json={
            "name": f"bad {_uid()}",
            "base_preset": "executiva",
            "layout_json": {
                "schema_version": 1,
                "slots": [{"widget_id": "revenue.margin", "col": 1, "span": 4}],
            },
        },
    )
    assert r.status_code == 400


def test_public_aggregates_no_n_plus_one_shape(admin_client, db):
    from app.billing.public import invoice_status_counts, qty_to_invoice_residual
    from app.costing.public import operational_summary
    from app.customs.public import process_counts_by_status
    from app.inventory.public import stock_overview_by_location_type
    from app.logistics.public import shipment_counts_by_status
    from app.orders.public import order_status_counts
    from app.treasury.public import unallocated_registered_bulk

    assert "DRAFT" in invoice_status_counts(db)
    assert "residual_qty" in qty_to_invoice_residual(db)
    cs = operational_summary(db)
    assert "published_cases" in cs
    if int(cs.get("published_cases") or 0) == 0:
        assert cs["included_total_brl"] is None
    pc = process_counts_by_status(db)
    assert "operational_total" in pc
    assert int(pc["operational_total"]) >= 0
    ov = stock_overview_by_location_type(db)
    assert "by_location_type" in ov
    assert "sku_with_balance" in ov
    assert "CONFIRMED" in order_status_counts(db)
    assert "PLANNED" in shipment_counts_by_status(db)
    assert "by_currency" in unallocated_registered_bulk(db)


def test_cash_committed_and_human_titles(admin_client, db):
    from datetime import date, timedelta
    from decimal import Decimal

    from app.billing.public import cash_committed_by_month, order_billing_progress_by_currency
    from tests.test_reporting_api import _issued_two_payables

    cash = cash_committed_by_month(db)
    assert cash["includes_overdue"] is True
    assert set(cash["labels"]) >= {"overdue", "m0", "m1", "m2"}

    _issued_two_payables(admin_client)
    cash2 = cash_committed_by_month(db)
    assert cash2["by_currency"]
    eur = next(r for r in cash2["by_currency"] if r["currency"] == "EUR")
    month_total = sum(Decimal(eur["buckets"][k]) for k in ("overdue", "m0", "m1", "m2"))
    assert month_total > 0

    progress = order_billing_progress_by_currency(db)
    assert "by_currency" in progress

    snap = admin_client.get("/api/reporting/dashboard", params={"view": "executiva"}).json()
    inbox = next(w for w in snap["widgets"] if w["widget_id"] == "attention.inbox")
    for item in inbox["display"].get("items") or []:
        title = str(item.get("title") or "")
        assert title
        assert not title.isdigit()
        if item.get("item_type", "").startswith("ap_"):
            assert "Obrigação vencida " not in title or " · " in title

    fx = next(w for w in snap["widgets"] if w["widget_id"] == "treasury.fx_exposure")
    eur_row = fx["display"].get("eur")
    if eur_row and fx["display"].get("quote"):
        shock = Decimal(str(fx["display"]["shock_1pct_brl"]))
        hero = Decimal(str(fx["display"]["hero_brl"]))
        assert shock == (hero * Decimal("0.01")).quantize(Decimal("0.01")) or abs(shock - hero * Decimal("0.01")) < Decimal("0.02")
        assert fx["display"]["quote"].get("rate_full")

    custom = admin_client.get(
        "/api/reporting/dashboard",
        params={"view": "executiva", "period": "custom", "date_from": (date.today() - timedelta(days=1)).isoformat()},
    )
    assert custom.status_code == 200, custom.text
    assert custom.json()["filters"]["period"] == "custom"
