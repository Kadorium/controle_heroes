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


def test_list_roles(client):
    _login(client)
    response = client.get("/api/users/roles")
    assert response.status_code == 200
    names = [r["name"] for r in response.json()]
    assert "admin" in names
    assert "operador" in names


def test_visibility_cancelled(client, db):
    from app.core.security import hash_password

    _login(client)
    role = db.query(Role).filter(Role.name == "operador").first()
    user = User(
        email="vis-cancel@epic.com.br",
        name="Vis Cancel",
        password_hash=hash_password("temp123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    client.post(
        f"/api/users/{user.id}/cancel",
        json={"reason": "Teste visibilidade", "reason_code": "USER_CANCEL"},
    )
    active = client.get("/api/users?visibility=active").json()
    cancelled = client.get("/api/users?visibility=cancelled").json()
    assert not any(u["id"] == user.id for u in active)
    assert any(u["id"] == user.id for u in cancelled)


def test_admin_updates_user_role_writes_audit(client, db):
    from app.core.security import hash_password

    _login(client)
    role = db.query(Role).filter(Role.name == "operador").first()
    user = User(
        email="patch-role@epic.com.br",
        name="Patch Role",
        password_hash=hash_password("temp123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    r = client.patch(f"/api/users/{user.id}", json={"role_name": "comprador"})
    assert r.status_code == 200
    assert r.json()["role"] == "comprador"
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == str(user.id), AuditLog.field_changed == "role")
        .first()
    )
    assert audit is not None
    assert audit.old_value == "operador"
    assert audit.new_value == "comprador"


def test_admin_resets_password(client, db):
    from app.core.security import hash_password

    _login(client)
    role = db.query(Role).filter(Role.name == "operador").first()
    user = User(
        email="reset-pw@epic.com.br",
        name="Reset PW",
        password_hash=hash_password("oldpass123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    r = client.patch(f"/api/users/{user.id}", json={"password": "newpass456"})
    assert r.status_code == 200
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == str(user.id), AuditLog.action == "password_reset")
        .first()
    )
    assert audit is not None


def test_cannot_demote_last_admin(client, db):
    from app.services.user_admin import count_active_admins

    _login(client)
    admin = db.query(User).filter(User.email == "admin@epic.com.br", User.is_active.is_(True)).first()
    assert admin is not None
    if count_active_admins(db) > 1:
        return
    r = client.patch(f"/api/users/{admin.id}", json={"role_name": "operador"})
    assert r.status_code == 400
    assert "administrador" in r.json()["detail"].lower()


def test_cancel_revokes_sessions(client, db):
    from app.core.security import hash_password
    from app.models import UserSession

    role = db.query(Role).filter(Role.name == "operador").first()
    user = User(
        email="sess-revoke@epic.com.br",
        name="Sess Revoke",
        password_hash=hash_password("temp123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    client.post("/api/auth/login", json={"email": user.email, "password": "temp123"})
    sessions_before = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .count()
    )
    assert sessions_before >= 1

    _login(client)
    client.post(
        f"/api/users/{user.id}/cancel",
        json={"reason": "Revogar sessões teste", "reason_code": "USER_CANCEL"},
    )
    sessions_after = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .count()
    )
    assert sessions_after == 0
