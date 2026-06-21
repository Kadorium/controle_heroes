from app.models import AuditLog, TechnicalLog


def test_login_success_sets_httponly_cookie(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@epic.com.br"
    assert "users:write" in data["permissions"]
    cookie_name = "epic_session"
    assert cookie_name in response.cookies
    set_cookie = response.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower()


def test_login_invalid_credentials(client, db):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "wrong"},
    )
    assert response.status_code == 401
    tech = db.query(TechnicalLog).filter(TechnicalLog.category == "login").first()
    assert tech is not None
    assert tech.message == "Falha de login"


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_after_login(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_logout(client):
    client.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    assert client.get("/api/auth/me").status_code == 401
