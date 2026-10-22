"""PAINEL-UX2 — disponibilidade comercial, exceções e série FX."""

from __future__ import annotations

from decimal import Decimal

from app.reporting import commercial as commercial_mod
from app.reporting import exceptions as exceptions_mod
from app.reporting.registry import ROLE_DEFAULT_PRESET, presets_by_id, validate_registry


def test_registry_three_visible_presets():
    validate_registry()
    presets = presets_by_id()
    visible = [p.preset_id for p in presets.values() if not p.hidden]
    assert visible == ["executiva", "comercial", "controle"]
    assert ROLE_DEFAULT_PRESET["comprador"] == "comercial"
    assert ROLE_DEFAULT_PRESET["aduana"] == "controle"
    assert ROLE_DEFAULT_PRESET["estoque"] == "controle"
    assert "financeiro" in presets and presets["financeiro"].hidden


def test_commercial_availability_endpoint(admin_client, db):
    r = admin_client.get("/api/reporting/commercial-availability", params={"limit": 20})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "rows" in body
    assert "totals" in body
    assert body["state"] in ("ok", "empty")
    for row in body["rows"]:
        if row.get("incoming_qty") is not None:
            assert Decimal(str(row["incoming_qty"])) >= 0
        else:
            assert row["incoming_qty"] is None


def test_commercial_incoming_never_invents_zero(db):
    data = commercial_mod.availability(db, limit=200, offset=0)
    for row in data["rows"]:
        assert row["incoming_qty"] != "0" or row["incoming_qty"] is None
        if row["incoming_qty"] is None:
            continue
        assert Decimal(str(row["incoming_qty"])) > 0


def test_control_exceptions_merge(admin_client, db):
    snap = admin_client.get("/api/reporting/dashboard", params={"view": "controle"}).json()
    wids = [w["widget_id"] for w in snap["widgets"]]
    assert "control.exceptions" in wids
    merged = exceptions_mod.collect(db, permissions=set(), is_admin=True, limit=40)
    assert "items" in merged
    assert merged["state"] in ("ok", "empty")
    for item in merged["items"]:
        assert item.get("kind")
        assert item.get("severity")
        assert item.get("title")
        assert item.get("href")


def test_fx_series_public(db):
    from app.treasury.public import fx

    series = fx.fx_quote_series(db, foreign="EUR", base="BRL", days=30)
    assert "points" in series
    assert series["empty"] is (len(series["points"]) == 0)
    dates = [p["date"] for p in series["points"]]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))


def test_executiva_snapshot_shape(admin_client):
    snap = admin_client.get("/api/reporting/dashboard", params={"view": "executiva"}).json()
    wids = [w["widget_id"] for w in snap["widgets"]]
    assert wids[:4] == ["ap.overdue", "ap.cash_due", "treasury.fx_exposure", "orders.to_invoice"]
    assert "treasury.fx_trend" in wids
    assert "commercial.availability" not in wids
    sizes = {w["widget_id"]: w.get("size") for w in snap["widgets"]}
    assert sizes["ap.overdue"] == "stat"
    assert sizes["ap.cash_committed"] == "panel"
    assert sizes["attention.inbox"] == "wide"


def test_comercial_snapshot(admin_client):
    snap = admin_client.get("/api/reporting/dashboard", params={"view": "comercial"}).json()
    assert snap["base_preset"] == "comercial"
    assert [w["widget_id"] for w in snap["widgets"]] == ["commercial.availability"]
