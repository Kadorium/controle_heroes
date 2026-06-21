from app.models import AuditLog, ReasonCode, Role, User


def _login(client, email="admin@epic.com.br", password="admin123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_operador_cannot_create_user(client):
    _login(client, "operador@epic.com.br", "oper123")
    response = client.post(
        "/api/users",
        json={
            "email": "novo@epic.com.br",
            "name": "Novo",
            "password": "senha123",
            "role_name": "operador",
        },
    )
    assert response.status_code == 403
    assert "Permissão negada" in response.json()["detail"]


def test_admin_creates_user_writes_audit_log(client, db):
    _login(client)
    response = client.post(
        "/api/users",
        json={
            "email": "comprador@epic.com.br",
            "name": "Comprador",
            "password": "senha123",
            "role_name": "comprador",
        },
    )
    assert response.status_code == 201
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "user", AuditLog.action == "create")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert "comprador@epic.com.br" in (audit.new_value or "")


def test_cancel_user_requires_reason(client, db):
    from app.core.security import hash_password

    _login(client)
    role = db.query(Role).filter(Role.name == "operador").first()
    user = User(
        email="temp@epic.com.br",
        name="Temp",
        password_hash=hash_password("temp123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    bad = client.post(f"/api/users/{user.id}/cancel", json={"reason": ""})
    assert bad.status_code == 422

    good = client.post(
        f"/api/users/{user.id}/cancel",
        json={"reason": "Usuário de teste", "reason_code": "USER_CANCEL"},
    )
    assert good.status_code == 200
    db.refresh(user)
    assert user.is_active is False
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == str(user.id), AuditLog.action == "cancel")
        .first()
    )
    assert audit is not None


def test_reason_codes_seeded(client, db):
    count = db.query(ReasonCode).filter(ReasonCode.is_active.is_(True)).count()
    assert count >= 12
    _login(client)
    response = client.get("/api/users/reason-codes")
    assert response.status_code == 200
    codes = [item["code"] for item in response.json()]
    assert "MODAL_CHANGE_COST" in codes
