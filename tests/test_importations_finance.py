"""Fases 3 e 4 — testes críticos."""

import uuid
from decimal import Decimal

import pytest

from app.core.parse import optional_decimal
from app.models import AuditLog, Credit, Invoice


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


@pytest.fixture()
def supplier(admin_client):
    r = admin_client.post(
        "/api/suppliers",
        json={"name": f"Heroes China {_uid()}", "country": "CN", "currency_default": "EUR"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def product(admin_client):
    r = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-{_uid()}", "description": "Produto teste", "ncm": "12345678"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def importation(admin_client, supplier, product):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "incoterm": "FOB",
            "estimated_total": "10000",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity_ordered": 100,
                    "unit_price_foreign": "10",
                }
            ],
        },
    )
    assert r.status_code == 201
    return r.json()


def _create_invoice(client, importation_id, invoice_type, number, amount, **extra):
    payload = {
        "importation_id": importation_id,
        "invoice_type": invoice_type,
        "invoice_number": number,
        "currency": "EUR",
        "amount": amount,
        **extra,
    }
    return client.post("/api/invoices", json=payload)


def _pay(client, invoice_id, amount, payment_type="PARTIAL", exchange_rate="5.20", **extra):
    return client.post(
        "/api/finance/payments",
        json={
            "invoice_id": invoice_id,
            "payment_type": payment_type,
            "amount_foreign": amount,
            "exchange_rate": exchange_rate,
            "receipt_reference": "REC-001",
            **extra,
        },
    )


# 1. Criar importação com 3 invoices, incluindo ANTECIPO
def test_importation_with_three_invoices_including_antecipo(admin_client, importation):
    imp_id = importation["id"]
    inv1 = _create_invoice(admin_client, imp_id, "ANTECIPO", "ANT-001", "2000")
    inv2 = _create_invoice(admin_client, imp_id, "PROFORMA", "PRO-001", "5000")
    inv3 = _create_invoice(admin_client, imp_id, "SALDO", "SAL-001", "3000")
    assert inv1.status_code == 201
    assert inv2.status_code == 201
    assert inv3.status_code == 201
    assert inv1.json()["invoice_type"] == "ANTECIPO"

    listed = admin_client.get(f"/api/invoices?importation_id={imp_id}")
    assert listed.status_code == 200
    assert len(listed.json()) == 3


# 2. Criar importação com mais de 3 invoices
def test_complementar_and_ajuste_invoice_types(admin_client, importation):
    comp = _create_invoice(
        admin_client, importation["id"], "COMPLEMENTAR", f"COMP-{_uid()}", "500"
    )
    ajuste = _create_invoice(admin_client, importation["id"], "AJUSTE", f"AJU-{_uid()}", "200")
    assert comp.status_code == 201
    assert ajuste.status_code == 201
    listed = admin_client.get(f"/api/invoices?importation_id={importation['id']}").json()
    types = {i["invoice_type"] for i in listed}
    assert "COMPLEMENTAR" in types
    assert "AJUSTE" in types


def test_importation_with_more_than_three_invoices(admin_client, supplier):
    r = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"PO-MULTI-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
        },
    )
    imp_id = r.json()["id"]
    for i in range(5):
        resp = _create_invoice(admin_client, imp_id, "PROFORMA", f"PF-{i}", str(1000 + i * 100))
        assert resp.status_code == 201
    listed = admin_client.get(f"/api/invoices?importation_id={imp_id}")
    assert len(listed.json()) == 5


# 3. Invoice com campo vazio não vira zero
def test_empty_invoice_amount_not_zero(admin_client, importation):
    r = _create_invoice(admin_client, importation["id"], "PROFORMA", "EMPTY-001", "")
    assert r.status_code == 201
    assert r.json()["amount"] is None
    assert optional_decimal("") is None


# 4. Alteração de invoice gera audit log
def test_invoice_update_generates_audit_log(admin_client, importation, db):
    inv = _create_invoice(admin_client, importation["id"], "PROFORMA", "AUD-001", "5000").json()
    upd = admin_client.patch(f"/api/invoices/{inv['id']}", json={"amount": "5500"})
    assert upd.status_code == 200
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "invoice", AuditLog.entity_id == str(inv["id"]))
        .all()
    )
    assert any(l.action == "update" and l.field_changed == "amount" for l in logs)


# 5. Anulação de invoice preserva histórico
def test_invoice_cancel_preserves_history(admin_client, importation, db):
    inv = _create_invoice(admin_client, importation["id"], "PROFORMA", "CAN-001", "1000").json()
    cancel = admin_client.post(f"/api/invoices/{inv['id']}/cancel", json={"reason": "Erro documental"})
    assert cancel.status_code == 200
    assert cancel.json()["is_active"] is False

    inactive = admin_client.get(f"/api/invoices?importation_id={importation['id']}&include_inactive=true")
    assert any(i["id"] == inv["id"] for i in inactive.json())
    assert db.query(Invoice).filter(Invoice.id == inv["id"]).first() is not None


# 6. Invoice com múltiplos pagamentos
def test_invoice_multiple_payments(admin_client, importation):
    inv = _create_invoice(admin_client, importation["id"], "PROFORMA", "PAY-MULTI", "10000").json()
    p1 = _pay(admin_client, inv["id"], "3000", payment_type="ADVANCE")
    p2 = _pay(admin_client, inv["id"], "2000", payment_type="PARTIAL")
    assert p1.status_code == 201
    assert p2.status_code == 201
    payments = admin_client.get(f"/api/finance/payments?invoice_id={inv['id']}")
    assert len(payments.json()) == 2


# 7. Pagamento parcial calcula saldo
def test_partial_payment_balance(admin_client, importation):
    inv = _create_invoice(admin_client, importation["id"], "SALDO", "BAL-001", "10000").json()
    _pay(admin_client, inv["id"], "4000", payment_type="PARTIAL")
    detail = admin_client.get(f"/api/invoices/{inv['id']}")
    assert detail.status_code == 200
    data = detail.json()
    assert Decimal(data["paid_total"]) == Decimal("4000")
    assert Decimal(data["balance"]) == Decimal("6000")


# 8. Pagamento com câmbio diferente do previsto
def test_payment_exchange_differs_from_expected(admin_client, importation, db):
    inv = _create_invoice(
        admin_client,
        importation["id"],
        "PROFORMA",
        "FX-001",
        "5000",
        expected_exchange_rate="5.00",
    ).json()
    pay = _pay(admin_client, inv["id"], "5000", exchange_rate="5.35", payment_type="FINAL")
    assert pay.status_code == 201
    logs = db.query(AuditLog).filter(AuditLog.action == "exchange_variance").all()
    assert len(logs) >= 1


# 9. Desconto direto em invoice
def test_discount_on_invoice(admin_client, importation):
    inv = _create_invoice(admin_client, importation["id"], "PROFORMA", "DISC-001", "8000").json()
    disc = admin_client.post(
        "/api/finance/discounts",
        json={
            "invoice_id": inv["id"],
            "discount_type": "GLOBAL",
            "amount": "500",
            "currency": "EUR",
            "reason": "Negociação",
        },
    )
    assert disc.status_code == 201
    detail = admin_client.get(f"/api/invoices/{inv['id']}")
    assert Decimal(detail.json()["balance"]) == Decimal("7500")


# 10. Crédito Heroes com saldo parcial
def test_heroes_credit_partial_use(admin_client, supplier, importation):
    credit = admin_client.post(
        "/api/finance/credits",
        json={"supplier_id": supplier["id"], "amount": "1000", "currency": "EUR"},
    )
    assert credit.status_code == 201
    cid = credit.json()["id"]
    apply1 = admin_client.post(
        f"/api/finance/credits/{cid}/apply",
        json={"importation_id": importation["id"], "amount": "400"},
    )
    assert apply1.status_code == 201
    refreshed = admin_client.get("/api/finance/credits")
    c = next(x for x in refreshed.json() if x["id"] == cid)
    assert c["status"] == "PARTIAL"
    assert Decimal(c["amount_available"]) == Decimal("600")


# 11. Tentativa de uso duplicado de crédito bloqueada
def test_duplicate_credit_use_blocked(admin_client, supplier, importation):
    credit = admin_client.post(
        "/api/finance/credits",
        json={"supplier_id": supplier["id"], "amount": "500", "currency": "EUR"},
    ).json()
    inv = _create_invoice(admin_client, importation["id"], "CREDITO", "CR-001", "500").json()
    first = admin_client.post(
        f"/api/finance/credits/{credit['id']}/apply",
        json={"importation_id": importation["id"], "invoice_id": inv["id"], "amount": "200"},
    )
    assert first.status_code == 201
    second = admin_client.post(
        f"/api/finance/credits/{credit['id']}/apply",
        json={"importation_id": importation["id"], "invoice_id": inv["id"], "amount": "100"},
    )
    assert second.status_code == 400


# 12. Conta corrente Brasil registrada com impacto estimado
def test_brazil_current_account_with_impact(admin_client, supplier):
    r = admin_client.post(
        "/api/finance/brazil-accounts",
        json={
            "supplier_id": supplier["id"],
            "description": "Saldo favorável Heroes BR",
            "amount": "15000",
            "currency": "BRL",
            "financial_impact_estimated": "15000",
            "fiscal_impact_estimated": "12000",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert Decimal(data["financial_impact_estimated"]) == Decimal("15000")
    assert Decimal(data["amount_available"]) == Decimal("15000")


# 13. Alteração de câmbio gera audit log
def test_exchange_rate_change_audit(admin_client, importation, db):
    inv = _create_invoice(
        admin_client,
        importation["id"],
        "PROFORMA",
        "FX-AUD-001",
        "3000",
        expected_exchange_rate="5.10",
    ).json()
    admin_client.patch(f"/api/invoices/{inv['id']}", json={"expected_exchange_rate": "5.25"})
    logs = db.query(AuditLog).filter(AuditLog.entity_type == "exchange_rate").all()
    assert len(logs) >= 1


# 14. Status transition blocked
def test_invalid_status_transition_blocked(admin_client, importation):
    r = admin_client.post(
        f"/api/importations/{importation['id']}/transition",
        json={"new_status": "SHIPPED"},
    )
    assert r.status_code == 400


# Consolidated balance
def test_consolidated_balance(admin_client, importation):
    imp_id = importation["id"]
    _create_invoice(admin_client, imp_id, "ANTECIPO", "C-ANT", "2000")
    inv2 = _create_invoice(admin_client, imp_id, "PROFORMA", "C-PRO", "8000").json()
    _pay(admin_client, inv2["id"], "3000")
    summary = admin_client.get(f"/api/finance/importations/{imp_id}/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert Decimal(data["total_invoiced"]) == Decimal("10000")
    assert Decimal(data["total_paid"]) == Decimal("3000")


# UI smoke — API endpoints used by frontend
def test_ui_api_smoke(admin_client, importation):
    assert admin_client.get("/api/importations").status_code == 200
    assert admin_client.get("/api/products").status_code == 200
    assert admin_client.get(f"/api/importations/{importation['id']}").status_code == 200
    assert admin_client.get(f"/api/finance/importations/{importation['id']}/summary").status_code == 200
