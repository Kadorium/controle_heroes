"""Referência FX e câmbio provisionado na abertura."""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.fx_reference import fetch_fx_reference


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_fx_reference_frankfurter():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"date": "2026-06-23", "rates": {"BRL": 6.12}}
    with patch("app.services.fx_reference.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        data = fetch_fx_reference()
    assert data["rate"] == "6.12"
    assert data["source"] == "Frankfurter (ECB)"


def test_fx_reference_api(admin_client: TestClient):
    with patch("app.api.finance.fetch_fx_reference") as mock_fetch:
        mock_fetch.return_value = {
            "currency_from": "EUR",
            "currency_to": "BRL",
            "rate": "6.10",
            "rate_date": "2026-06-23",
            "source": "Frankfurter (ECB)",
            "disclaimer": "Referência de mercado",
        }
        res = admin_client.get("/api/finance/fx-reference")
    assert res.status_code == 200
    assert res.json()["rate"] == "6.10"


def test_create_importation_registers_opening_exchange_rate(admin_client: TestClient):
    uid = uuid.uuid4().hex[:8]
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"FX Sup {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    po = f"PO-FX-{uid}"
    res = admin_client.post(
        "/api/importations",
        json={
            "po_number": po,
            "supplier_id": sup["id"],
            "currency": "EUR",
            "opening_exchange_rate": "5.85",
        },
    )
    assert res.status_code == 201
    imp_id = res.json()["id"]
    rates = admin_client.get(f"/api/finance/exchange-rates?importation_id={imp_id}")
    assert rates.status_code == 200
    rows = rates.json()
    assert any(r["rate_type"] == "OPENING_PROVISION" and Decimal(r["rate_value"]) == Decimal("5.85") for r in rows)
