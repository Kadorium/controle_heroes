"""Identity user CRUD via Foundation HTTP."""


def test_users_crud_and_guards(admin_client):
    c = admin_client
    roles = c.get("/api/roles")
    assert roles.status_code == 200, roles.text
    role_map = {r["name"]: r["id"] for r in roles.json()}
    assert "comprador" in role_map

    r = c.post(
        "/api/users",
        json={
            "email": "buyer.mdm@epic.com.br",
            "name": "Comprador MDM",
            "password": "secret123",
            "role_id": role_map["comprador"],
        },
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    assert r.json()["role"] == "comprador"
    assert "password_hash" not in r.json()

    r = c.get("/api/users", params={"q": "buyer.mdm"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = c.patch(f"/api/users/{uid}", json={"name": "Comprador Renomeado"})
    assert r.status_code == 200
    assert r.json()["name"] == "Comprador Renomeado"

    r = c.post(f"/api/users/{uid}/password", json={"password": "secret456"})
    assert r.status_code == 200

    me = c.get("/api/auth/me")
    admin_id = me.json()["id"]
    r = c.patch(f"/api/users/{admin_id}", json={"is_active": False})
    assert r.status_code == 409
    assert r.json()["error"] == "last_admin_guard" or "último administrador" in r.json().get(
        "message", ""
    )


def test_users_forbidden_without_permission(admin_client):
    c = admin_client
    roles = {r["name"]: r["id"] for r in c.get("/api/roles").json()}
    r = c.post(
        "/api/users",
        json={
            "email": "buyer2.mdm@epic.com.br",
            "name": "Buyer 2",
            "password": "secret123",
            "role_id": roles["comprador"],
        },
    )
    assert r.status_code == 201
    login = c.post(
        "/api/auth/login",
        json={"email": "buyer2.mdm@epic.com.br", "password": "secret123"},
    )
    assert login.status_code == 200, login.text
    r = c.get("/api/users")
    assert r.status_code == 403
