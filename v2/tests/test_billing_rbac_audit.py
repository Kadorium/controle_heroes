"""RBAC e Audit UoW Billing."""

import json
import uuid

import pytest
from sqlalchemy.orm import Session

from app.identity.models import Role, User
from app.identity.security import hash_password


def _make_user(db: Session, *, email: str, role_name: str, permissions: list[str]) -> User:
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name, permissions_json=json.dumps(permissions))
        db.add(role)
        db.flush()
    else:
        role.permissions_json = json.dumps(permissions)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=email,
            password_hash=hash_password("test123"),
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
    else:
        user.role_id = role.id
        user.password_hash = hash_password("test123")
    db.commit()
    return user


def _login(client, email: str):
    r = client.post("/api/auth/login", json={"email": email, "password": "test123"})
    assert r.status_code == 200, r.text
    return client


def _prep_order(c):
    from tests.test_billing_api import _confirmed_order

    suffix = uuid.uuid4().hex[:8]
    return _confirmed_order(c, code=f"RBAC-BILL-{suffix}", sku=f"RBAC-B-{suffix}")


def test_rbac_billing_read_without_write(client, db, admin_client):
    order, _ = _prep_order(admin_client)
    _make_user(
        db,
        email="billread@example.com",
        role_name="bill_reader",
        permissions=["billing:read", "orders:read"],
    )
    c = _login(client, "billread@example.com")
    assert c.get("/api/invoices").status_code == 200
    assert (
        c.post(
            f"/api/orders/{order['id']}/invoices",
            json={"invoice_number": "NOPE"},
        ).status_code
        == 403
    )


def test_audit_rollback_invoice(admin_client, monkeypatch):
    c = admin_client
    order, _ = _prep_order(c)

    from app.audit import public as audit_public

    def boom(*_a, **_k):
        raise RuntimeError("audit fail bill")

    monkeypatch.setattr(audit_public, "record_event", boom)
    with pytest.raises(RuntimeError, match="audit fail bill"):
        c.post(
            f"/api/orders/{order['id']}/invoices",
            json={"invoice_number": "AUDIT-FAIL-INV"},
        )
    monkeypatch.undo()
    listed = c.get("/api/invoices", params={"order_id": order["id"]}).json()
    assert all(i["invoice_number"] != "AUDIT-FAIL-INV" for i in listed)


def test_treasury_routes_exist_post_inc3(admin_client):
    """Inc-2 garantia 'sem payments' → Inc-3 expõe /api/payments (RBAC admin)."""
    assert admin_client.get("/api/payments").status_code == 200
