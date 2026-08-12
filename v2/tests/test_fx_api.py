"""Inc-4 FX API — cenário canônico, valuation freeze, quotes, RBAC."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json

import pytest

from app.identity.models import Role, User
from app.identity.security import hash_password
from app.treasury.fx_provider import FixtureFxQuoteProvider, FxQuoteUnavailable, set_quote_provider
from app.treasury.fx_provider_http import HttpFxQuoteProvider


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _issued_payable_1000(client):
    """Uma fatura / um payable €1000 (permite alloc 400 + open 600)."""
    sku = f"FX-{_uid()}"
    s = client.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "10",
            "unit_price": "100",
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = client.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{_uid()}"},
    ).json()
    item = inv["items"][0]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "10",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    today = date.today()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": today.isoformat(), "amount": "1000"}],
        },
    ).json()
    client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    inv = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    ).json()
    assert len(inv["payables"]) == 1
    return s, inv, inv["payables"][0]


def _register_payment(client, supplier_id, amount="400"):
    r = client.post(
        "/api/payments",
        json={
            "supplier_id": supplier_id,
            "amount": amount,
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(autouse=True)
def _reset_provider():
    set_quote_provider(None)
    yield
    set_quote_provider(None)


def test_canonical_fx_view_and_reforecast_freeze(admin_client):
    c = admin_client
    s, inv, payable = _issued_payable_1000(c)
    pid = payable["id"]

    r = c.post(
        f"/api/payables/{pid}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    assert r.status_code == 200, r.text

    r = c.post(
        f"/api/payables/{pid}/fx-plan",
        json={
            "kind": "REFORECAST",
            "rate": "6.10",
            "effective_from": date.today().isoformat(),
            "reason_code": "MARKET_UPDATE",
        },
    )
    assert r.status_code == 200, r.text

    r = c.post("/api/fx/quotes", json={"foreign_currency": "EUR", "rate": "6.25", "source": "MANUAL"})
    assert r.status_code == 200, r.text

    pay = _register_payment(c, s["id"], amount="400")
    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"fx-{_uid()}",
            "allocations": [
                {"payable_id": pid, "amount": "400", "expected_version": payable["version"]},
            ],
        },
    )
    assert r.status_code == 200, r.text
    pay = r.json()
    alloc_id = pay["allocations"][0]["id"]

    r = c.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "400",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    )
    assert r.status_code == 200, r.text
    ex = r.json()

    r = c.post(
        "/api/fx/execution-allocations",
        json={"fx_execution_id": ex["id"], "payment_allocation_id": alloc_id},
    )
    assert r.status_code == 200, r.text

    r = c.post("/api/fx/valuations/complete", json={"payment_allocation_id": alloc_id})
    assert r.status_code == 200, r.text
    val = r.json()
    assert Decimal(val["realized_result_vs_reference"]) == Decimal("-40.00")
    assert Decimal(val["planned_rate_snapshot"]) == Decimal("6.100000")
    assert val["benchmark"] == "frozen_reference"

    view = c.get(f"/api/payables/{pid}/fx-view").json()
    assert Decimal(view["open_foreign"]) == Decimal("600.00")
    assert Decimal(view["realized_brl"]) == Decimal("2480.00")
    assert Decimal(view["realized_result_vs_reference"]) == Decimal("-40.00")
    assert Decimal(view["realized_result_vs_initial"]) == Decimal("-80.00")
    assert Decimal(view["online_result_vs_current"]) == Decimal("-90.00")
    assert Decimal(view["online_result_vs_initial"]) == Decimal("-150.00")
    assert Decimal(view["total_vs_current"]) == Decimal("-130.00")
    assert Decimal(view["total_vs_initial"]) == Decimal("-230.00")
    assert view["benchmarks"]["realized_result_vs_reference"] == "frozen_reference"

    r = c.post(
        f"/api/payables/{pid}/fx-plan",
        json={
            "kind": "REFORECAST",
            "rate": "6.15",
            "effective_from": date.today().isoformat(),
            "reason_code": "MARKET_UPDATE",
        },
    )
    assert r.status_code == 200, r.text

    view2 = c.get(f"/api/payables/{pid}/fx-view").json()
    assert Decimal(view2["realized_result_vs_reference"]) == Decimal("-40.00")
    assert Decimal(view2["online_result_vs_current"]) == Decimal("-60.00")
    assert Decimal(view2["total_vs_current"]) == Decimal("-100.00")


def test_missing_quote_online_null_not_zero(admin_client, db):
    from app.treasury.fx_models import FxMarketQuote

    db.query(FxMarketQuote).delete()
    db.commit()

    c = admin_client
    _, _, payable = _issued_payable_1000(c)
    pid = payable["id"]
    c.post(
        f"/api/payables/{pid}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    view = c.get(f"/api/payables/{pid}/fx-view").json()
    assert view["market"]["rate"] is None
    assert view["market"]["status"] == "missing"
    assert view["online_result_vs_current"] is None
    assert view["market_open_brl"] is None


def test_stale_quote_still_calculates(admin_client, db):
    from app.treasury.fx_models import FxMarketQuote

    db.query(FxMarketQuote).delete()
    db.commit()

    c = admin_client
    _, _, payable = _issued_payable_1000(c)
    pid = payable["id"]
    c.post(
        f"/api/payables/{pid}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    now = datetime.now(timezone.utc)
    q = FxMarketQuote(
        foreign_currency="EUR",
        base_currency="BRL",
        rate=Decimal("6.25"),
        source="MANUAL",
        observed_at=now - timedelta(hours=2),
        retrieved_at=now - timedelta(hours=2),
        stale_after=now - timedelta(minutes=5),
    )
    db.add(q)
    db.commit()

    view = c.get(f"/api/payables/{pid}/fx-view").json()
    assert view["market"]["stale"] is True
    assert view["market"]["status"] == "stale"
    assert Decimal(view["online_result_vs_current"]) == Decimal("-250.00")  # 1000*(6-6.25)


def test_quote_for_date_exact_day_or_missing(admin_client, db):
    """FIN-1C-FIX-2 V3 — cotação do dia; sem vizinho inventado."""
    from datetime import date, datetime, timezone

    from app.treasury import fx_commands as fx

    fx.persist_market_quote(
        db,
        foreign_currency="EUR",
        rate="5.770000",
        source="TEST_FIX2",
        observed_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
    )
    db.commit()

    c = admin_client
    hit = c.get("/api/fx/quotes/for-date", params={"as_of": "2026-08-05", "foreign": "EUR"})
    assert hit.status_code == 200, hit.text
    body = hit.json()
    assert body["status"] != "missing"
    assert body["rate"] is not None
    assert body["as_of"] == "2026-08-05"

    miss = c.get("/api/fx/quotes/for-date", params={"as_of": "2026-01-01", "foreign": "EUR"})
    assert miss.status_code == 200, miss.text
    empty = miss.json()
    assert empty["status"] == "missing"
    assert empty["rate"] is None
    assert "Sem cotação" in (empty.get("message") or "")


def test_refresh_with_fixture_provider(admin_client):
    c = admin_client
    set_quote_provider(FixtureFxQuoteProvider(rate="6.33"))
    r = c.post("/api/fx/quotes/refresh", params={"foreign": "EUR", "base": "BRL"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(body["rate"]) == Decimal("6.330000")
    assert body["source"] == "FIXTURE"
    latest = c.get("/api/fx/quotes/latest").json()
    assert Decimal(latest["rate"]) == Decimal("6.330000")


def test_refresh_provider_failure_keeps_previous(admin_client, monkeypatch):
    c = admin_client
    c.post("/api/fx/quotes", json={"foreign_currency": "EUR", "rate": "6.25", "source": "MANUAL"})

    class Boom:
        def get_latest_quote(self, foreign, base="BRL"):
            raise FxQuoteUnavailable("down")

    set_quote_provider(Boom())
    r = c.post("/api/fx/quotes/refresh")
    assert r.status_code == 400
    latest = c.get("/api/fx/quotes/latest").json()
    assert Decimal(latest["rate"]) == Decimal("6.250000")


def test_http_provider_frankfurter_then_awesome(monkeypatch):
    """Legacy monkeypatch ainda cobre fallback; ver também test_fx_provider_http.py."""
    provider = HttpFxQuoteProvider(timeout=1.0)

    class Resp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200
            self.headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    calls = []

    class Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            calls.append(str(url))
            if "frankfurter" in str(url):
                raise RuntimeError("offline")
            return Resp({"EURBRL": {"bid": "6.40"}})

    monkeypatch.setattr("app.treasury.fx_provider_http.httpx.Client", Client)
    dto = provider.get_latest_quote("EUR", "BRL")
    assert dto.source.startswith("AwesomeAPI")
    assert dto.rate == Decimal("6.40")
    assert any("frankfurter" in u for u in calls)


def test_execution_requires_document_or_override(admin_client):
    c = admin_client
    s, _, payable = _issued_payable_1000(c)
    pay = _register_payment(c, s["id"], amount="100")
    r = c.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "100",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": False,
        },
    )
    assert r.status_code == 400


def test_fx_read_rbac(client, db, admin_client):
    role = Role(
        name=f"fxr-{_uid()}",
        description="fx read",
        permissions_json=json.dumps(["treasury:fx_read"]),
    )
    db.add(role)
    db.flush()
    email = f"fxr-{_uid()}@epic.com.br"
    u = User(
        email=email,
        name="FX Reader",
        password_hash=hash_password("test123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(u)
    db.commit()

    _, _, payable = _issued_payable_1000(admin_client)
    login = client.post("/api/auth/login", json={"email": email, "password": "test123"})
    assert login.status_code == 200
    r = client.get(f"/api/payables/{payable['id']}/fx-view")
    assert r.status_code == 200
    r = client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    assert r.status_code == 403
