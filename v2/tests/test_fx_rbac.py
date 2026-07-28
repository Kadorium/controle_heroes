"""RBAC mínimo FX — autorizado vs 403 por rota crítica."""

from __future__ import annotations

import json
import uuid
from datetime import date
from io import BytesIO

from app.identity.models import Role, User
from app.identity.security import hash_password


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _user_with_perms(db, perms: list[str]) -> tuple[str, str]:
    role = Role(
        name=f"fxrbac-{_uid()}",
        description="fx rbac",
        permissions_json=json.dumps(perms),
    )
    db.add(role)
    db.flush()
    email = f"fxrbac-{_uid()}@epic.com.br"
    password = "test123"
    u = User(
        email=email,
        name="FX RBAC",
        password_hash=hash_password(password),
        role_id=role.id,
        is_active=True,
    )
    db.add(u)
    db.commit()
    return email, password


def _login(client, email: str, password: str = "test123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return client


def _issued_payable(admin_client):
    sku = f"RB-{_uid()}"
    s = admin_client.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = admin_client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = admin_client.post(
        "/api/orders",
        json={"code": f"ORD-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = admin_client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "1",
            "unit_price": "100",
        },
    ).json()
    o = admin_client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = admin_client.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{_uid()}"},
    ).json()
    item = inv["items"][0]
    inv = admin_client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "1",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    inv = admin_client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": date.today().isoformat(), "amount": "100"}],
        },
    ).json()
    admin_client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    inv = admin_client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    ).json()
    return s, inv["payables"][0]


def test_fx_read_denied_without_permission(client, db, admin_client):
    email, pw = _user_with_perms(db, ["treasury:read"])
    _, payable = _issued_payable(admin_client)
    _login(client, email, pw)
    r = client.get(f"/api/payables/{payable['id']}/fx-view")
    assert r.status_code == 403


def test_fx_plan_write_authorized_and_denied(client, db, admin_client):
    _, payable = _issued_payable(admin_client)
    email_ok, pw = _user_with_perms(db, ["treasury:fx_read", "treasury:fx_write"])
    _login(client, email_ok, pw)
    r = client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    assert r.status_code == 200, r.text

    email_no, pw2 = _user_with_perms(db, ["treasury:fx_read"])
    _login(client, email_no, pw2)
    r = client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={
            "kind": "REFORECAST",
            "rate": "6.10",
            "effective_from": date.today().isoformat(),
            "reason_code": "X",
        },
    )
    assert r.status_code == 403


def test_fx_refresh_requires_quote_refresh(client, db, admin_client):
    from app.treasury.fx_provider import FixtureFxQuoteProvider, set_quote_provider

    set_quote_provider(FixtureFxQuoteProvider(rate="6.33"))
    email_no, pw = _user_with_perms(db, ["treasury:fx_read", "treasury:fx_write"])
    _login(client, email_no, pw)
    r = client.post("/api/fx/quotes/refresh", params={"foreign": "EUR"})
    assert r.status_code == 403

    email_ok, pw2 = _user_with_perms(
        db, ["treasury:fx_read", "treasury:fx_write", "treasury:fx_quote_refresh"]
    )
    _login(client, email_ok, pw2)
    r = client.post("/api/fx/quotes/refresh", params={"foreign": "EUR"})
    assert r.status_code == 200, r.text
    set_quote_provider(None)


def test_fx_without_document_override(client, db, admin_client):
    s, payable = _issued_payable(admin_client)
    admin_client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay = admin_client.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "amount": "100",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    ).json()

    email_no, pw = _user_with_perms(db, ["treasury:fx_write"])
    _login(client, email_no, pw)
    r = client.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "100",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    )
    assert r.status_code == 403

    email_ok, pw2 = _user_with_perms(db, ["treasury:fx_write", "treasury:fx_without_document"])
    _login(client, email_ok, pw2)
    r = client.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "100",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    )
    assert r.status_code == 200, r.text


def test_fx_correction_and_rebind_supersede(client, db, admin_client):
    s, payable = _issued_payable(admin_client)
    plan = admin_client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    ).json()
    pay = admin_client.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "amount": "100",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    ).json()
    # allocation + exec + link + valuation as admin
    r = admin_client.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"rb-{_uid()}",
            "allocations": [
                {"payable_id": payable["id"], "amount": "100", "expected_version": payable["version"]},
            ],
        },
    )
    pay = r.json()
    alloc_id = pay["allocations"][0]["id"]
    ex = admin_client.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "100",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    ).json()
    admin_client.post(
        "/api/fx/execution-allocations",
        json={"fx_execution_id": ex["id"], "payment_allocation_id": alloc_id},
    )
    val = admin_client.post(
        "/api/fx/valuations/complete", json={"payment_allocation_id": alloc_id}
    ).json()

    # CORRECTION uses fx_write (not supersede) — audit action differs; rebind needs supersede
    email_no, pw = _user_with_perms(db, ["treasury:fx_write"])
    _login(client, email_no, pw)
    r = client.post(
        f"/api/fx/valuations/{val['id']}/rebind",
        json={"planned_rate_id": plan["id"], "reason_code": "REBIND_TEST"},
    )
    assert r.status_code == 403

    email_ok, pw2 = _user_with_perms(db, ["treasury:fx_write", "treasury:fx_supersede"])
    _login(client, email_ok, pw2)
    # new reforecast plan first
    new_plan = client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={
            "kind": "REFORECAST",
            "rate": "6.05",
            "effective_from": date.today().isoformat(),
            "reason_code": "UPD",
        },
    )
    assert new_plan.status_code == 200, new_plan.text
    r = client.post(
        f"/api/fx/valuations/{val['id']}/rebind",
        json={"planned_rate_id": new_plan.json()["id"], "reason_code": "REBIND_TEST"},
    )
    assert r.status_code == 200, r.text


def test_fx_link_requires_write(client, db, admin_client):
    s, payable = _issued_payable(admin_client)
    admin_client.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay = admin_client.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "amount": "100",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    ).json()
    r = admin_client.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"lk-{_uid()}",
            "allocations": [
                {"payable_id": payable["id"], "amount": "100", "expected_version": payable["version"]},
            ],
        },
    )
    pay = r.json()
    alloc_id = pay["allocations"][0]["id"]
    ex = admin_client.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "100",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    ).json()

    email_no, pw = _user_with_perms(db, ["treasury:fx_read"])
    _login(client, email_no, pw)
    r = client.post(
        "/api/fx/execution-allocations",
        json={"fx_execution_id": ex["id"], "payment_allocation_id": alloc_id},
    )
    assert r.status_code == 403

    email_ok, pw2 = _user_with_perms(db, ["treasury:fx_write"])
    _login(client, email_ok, pw2)
    r = client.post(
        "/api/fx/execution-allocations",
        json={"fx_execution_id": ex["id"], "payment_allocation_id": alloc_id},
    )
    assert r.status_code == 200, r.text
