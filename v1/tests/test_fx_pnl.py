"""PnL Cambial operacional — variação BRL vs provisão."""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.fx_pnl import compute_fx_pnl


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _create_importation(client, *, opening_rate: str = "5.00"):
    uid = _uid()
    sup = client.post(
        "/api/suppliers",
        json={"name": f"PnL Sup {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    res = client.post(
        "/api/importations",
        json={
            "po_number": f"PO-PNL-{uid}",
            "supplier_id": sup["id"],
            "currency": "EUR",
            "estimated_total": "10000",
            "opening_exchange_rate": opening_rate,
        },
    )
    assert res.status_code == 201
    return res.json()


def _create_invoice(client, imp_id: int, amount: str, **extra):
    return client.post(
        "/api/invoices",
        json={
            "importation_id": imp_id,
            "invoice_type": "ANTECIPO",
            "invoice_number": f"INV-{extra.get('suffix', _uid())}",
            "currency": "EUR",
            "amount": amount,
            "expected_exchange_rate": extra.get("expected_exchange_rate", "5.00"),
        },
    )


def test_fx_pnl_realized_settled_payment(admin_client):
    """Liquidação com taxa acima da provisão gera PnL realizado negativo."""
    imp = _create_importation(admin_client, opening_rate="5.00")
    inv = _create_invoice(admin_client, imp["id"], "1000").json()

    pay = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "ADVANCE",
            "amount_foreign": "5200",
            "currency_foreign": "BRL",
            "exchange_rate": "5.20",
            "payment_date": "2026-06-01",
            "receipt_reference": "REC-PNL",
        },
    )
    assert pay.status_code == 201

    with patch("app.api.finance.fetch_fx_reference") as mock_ref:
        mock_ref.return_value = {"rate": "5.10"}
        res = admin_client.get(f"/api/finance/importations/{imp['id']}/fx-pnl")

    assert res.status_code == 200
    data = res.json()
    assert Decimal(data["provision_rate"]) == Decimal("5.00")
    assert Decimal(data["pnl_realized_brl"]) == Decimal("-200")
    # saldo em aberto zero — sem não realizado
    assert data["pnl_unrealized_brl"] is None
    assert Decimal(data["pnl_total_brl"]) == Decimal("-200")


def test_fx_pnl_unrealized_open_balance(admin_client):
    """Saldo EUR em aberto marca a mercado vs provisão."""
    imp = _create_importation(admin_client, opening_rate="5.00")
    inv = _create_invoice(admin_client, imp["id"], "1000")
    assert inv.status_code == 201

    with patch("app.api.finance.fetch_fx_reference") as mock_ref:
        mock_ref.return_value = {"rate": "5.10"}
        res = admin_client.get(f"/api/finance/importations/{imp['id']}/fx-pnl")

    assert res.status_code == 200
    data = res.json()
    # 1000 EUR * (5.00 - 5.10) = -100
    assert Decimal(data["pnl_unrealized_brl"]) == Decimal("-100")
    assert data["pnl_realized_brl"] is None
    assert Decimal(data["pnl_total_brl"]) == Decimal("-100")


def test_fx_pnl_planned_payment(admin_client):
    """Pagamento planejado em BRL entra no bucket planejado."""
    imp = _create_importation(admin_client, opening_rate="5.00")
    inv = _create_invoice(admin_client, imp["id"], "1000").json()

    pay = admin_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"],
            "payment_type": "ADVANCE",
            "amount_foreign": "5000",
            "currency_foreign": "BRL",
            "due_date": "2026-07-01",
        },
    )
    assert pay.status_code == 201

    with patch("app.api.finance.fetch_fx_reference") as mock_ref:
        mock_ref.return_value = {"rate": "5.10"}
        res = admin_client.get(f"/api/finance/importations/{imp['id']}/fx-pnl")

    assert res.status_code == 200
    data = res.json()
    # EUR implícito 1000 @ provisão; BRL planejado 5000 = provisão exata → delta 0
    assert Decimal(data["pnl_planned_brl"]) == Decimal("0")
    assert Decimal(data["pnl_unrealized_brl"]) == Decimal("-100")


def test_fx_pnl_summary_endpoint(admin_client):
    imp = _create_importation(admin_client)
    _create_invoice(admin_client, imp["id"], "500")

    with patch("app.api.finance.fetch_fx_reference") as mock_ref:
        mock_ref.return_value = {"rate": "5.10"}
        res = admin_client.get("/api/finance/fx-pnl/summary")

    assert res.status_code == 200
    data = res.json()
    assert data["label"] == "PnL Cambial"
    assert data["orders_with_pnl"] >= 1
