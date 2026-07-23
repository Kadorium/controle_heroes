def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert body["database"] == "ok"


def test_login_and_me(admin_client):
    me = admin_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@epic.com.br"


def test_login_writes_audit(admin_client):
    rows = admin_client.get("/api/audit", params={"entity_type": "user", "entity_id": "1"})
    assert rows.status_code == 200
    actions = [x["action"] for x in rows.json()]
    assert "login" in actions


def test_document_upload_and_list(admin_client):
    files = {"file": ("hello.txt", b"hello-v2", "text/plain")}
    data = {"entity_type": "order", "entity_id": "demo-1", "role": "attachment"}
    up = admin_client.post("/api/documents", files=files, data=data)
    assert up.status_code == 200, up.text
    listed = admin_client.get("/api/documents", params={"entity_type": "order", "entity_id": "demo-1"})
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
    assert listed.json()[0]["original_filename"] == "hello.txt"
