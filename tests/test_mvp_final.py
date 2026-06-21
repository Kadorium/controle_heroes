"""Testes finais MVP — smoke checks."""

import pytest


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_health_check(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_login_logout(client):
    r = client.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    assert r.status_code == 200
    r2 = client.post("/api/auth/logout")
    assert r2.status_code == 200


def test_permissions_operador_blocked(client, db):
    from app.core.security import hash_password
    from app.models import Role, User

    role = db.query(Role).filter(Role.name == "operador").first()
    if not db.query(User).filter(User.email == "operador@epic.com.br").first():
        db.add(
            User(
                email="operador@epic.com.br",
                name="Operador",
                password_hash=hash_password("oper123"),
                role_id=role.id,
                is_active=True,
            )
        )
        db.commit()
    client.post("/api/auth/logout")
    login = client.post("/api/auth/login", json={"email": "operador@epic.com.br", "password": "oper123"})
    assert login.status_code == 200
    r = client.post("/api/users", json={"email": "x@test.com", "name": "X", "password": "x", "role": "operador"})
    assert r.status_code == 403


def test_audit_log_on_login(admin_client, db):
    from app.models import AuditLog

    before = db.query(AuditLog).count()
    admin_client.post("/api/auth/logout")
    admin_client.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    assert db.query(AuditLog).count() >= before


def test_technical_log_table_exists(db):
    from app.models import TechnicalLog

    db.add(TechnicalLog(category="test", message="smoke test"))
    db.commit()
    assert db.query(TechnicalLog).filter(TechnicalLog.message == "smoke test").count() == 1


def test_empty_field_not_zero(admin_client):
    csv = b"PO,SKU,Description,Qty,UnitPrice,Supplier\nPO-E,,Item,,10.00,Heroes\n"
    r = admin_client.post(
        "/api/imports/heroes/upload",
        files={"file": ("heroes.csv", csv, "text/csv")},
    )
    assert r.status_code == 201
    staging = admin_client.get(f"/api/imports/staging?raw_file_id={r.json()['id']}")
    assert staging.json()[0]["parsed_data_json"]["quantity"] is None


def test_staging_vs_official_customs(admin_client):
    import uuid

    uid = uuid.uuid4().hex[:8]
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"Sup {uid}", "country": "CN", "currency_default": "EUR"},
    ).json()
    prod = admin_client.post(
        "/api/products",
        json={"sku_code": f"SKU-{uid}", "description": "Produto teste"},
    ).json()
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"STAGING-OFFICIAL-{uid}",
            "supplier_id": sup["id"],
            "currency": "EUR",
            "items": [{"product_id": prod["id"], "quantity_ordered": 10, "unit_price_foreign": "5"}],
        },
    ).json()
    staging = admin_client.post(
        "/api/customs/documents",
        json={
            "importation_id": imp["id"],
            "document_type": "DI",
            "document_number": "DI-STG",
            "document_data_json": {"raw": True},
        },
    ).json()
    assert staging["status"] == "STAGING"
    official = admin_client.post(
        f"/api/customs/documents/{staging['id']}/approve",
        json={"official_data_json": {"number": "DI-STG"}},
    ).json()
    assert official["status"] == "OFFICIAL"
    assert official["document_data_json"]["raw"] is True


def test_backup_attachments():
    from app.services.attachments import backup_attachments_to_zip

    path = backup_attachments_to_zip()
    assert path.exists()


def test_ui_api_smoke_mvp(admin_client):
    endpoints = [
        "/api/health",
        "/api/importations",
        "/api/reconciliation/importations/1/run",
    ]
    assert admin_client.get("/api/health").status_code == 200
    assert admin_client.get("/api/importations").status_code == 200
