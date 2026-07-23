"""RBAC, Audit UoW e transições Orders."""

import json

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


def _login(client, email: str, password: str = "test123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return client


def test_rbac_orders_read_without_write(client, db):
    _make_user(
        db,
        email="reader@example.com",
        role_name="reader_orders",
        permissions=["orders:read", "catalog:read"],
    )
    c = _login(client, "reader@example.com")
    assert c.get("/api/orders").status_code == 200
    assert c.post("/api/orders", json={"code": "NOPE", "supplier_id": 1, "currency": "EUR"}).status_code == 403


def test_rbac_cancel_confirmed_requires_cancel_perm(admin_client, client, db):
    a = admin_client
    s = a.post("/api/suppliers", json={"name": "RBAC Sup", "is_active": True}).json()
    p = a.post("/api/products", json={"sku": "RBAC-1", "description": "x", "is_active": True}).json()
    o = a.post("/api/orders", json={"code": "RBAC-ORD", "supplier_id": s["id"], "currency": "EUR"}).json()
    o = a.post(
        f"/api/orders/{o['id']}/items",
        json={"expected_version": o["version"], "product_id": p["id"], "quantity": "1", "unit_price": "1"},
    ).json()
    o = a.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()

    _make_user(
        db,
        email="writer@example.com",
        role_name="writer_no_cancel",
        permissions=["orders:read", "orders:write", "catalog:read", "catalog:write"],
    )
    c = _login(client, "writer@example.com")
    r = c.post(
        f"/api/orders/{o['id']}/cancel",
        json={"expected_version": o["version"], "reason_code": "X"},
    )
    assert r.status_code == 403


def test_no_close_endpoint(admin_client):
    r = admin_client.post("/api/orders/1/close", json={"expected_version": 1})
    assert r.status_code in (404, 405)


def test_audit_rollback_prevents_order_persist(admin_client, monkeypatch):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": "Audit Roll", "is_active": True}).json()

    from app.audit import public as audit_public

    def boom(*_a, **_k):
        raise RuntimeError("audit fail")

    monkeypatch.setattr(audit_public, "record_event", boom)

    with pytest.raises(RuntimeError, match="audit fail"):
        c.post(
            "/api/orders",
            json={"code": "AUDIT-FAIL-1", "supplier_id": s["id"], "currency": "EUR"},
        )

    monkeypatch.undo()
    listed = c.get("/api/orders").json()
    assert all(o["code"] != "AUDIT-FAIL-1" for o in listed)


def test_created_by_actor_is_string(admin_client):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": "Actor Sup", "is_active": True}).json()
    o = c.post("/api/orders", json={"code": "ACTOR-1", "supplier_id": s["id"], "currency": "EUR"}).json()
    assert isinstance(o["created_by_actor_id"], str)
    assert o["created_by_actor_id"].isdigit()


def test_code_is_user_provided_not_generated(admin_client):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": "Code Sup", "is_active": True}).json()
    o = c.post("/api/orders", json={"code": "758", "supplier_id": s["id"], "currency": "EUR"}).json()
    assert o["code"] == "758"
    assert not o["code"].startswith("ORD-")
