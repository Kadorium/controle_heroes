"""J3-I0 — API + RBAC."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.identity.models import Role, User
from app.identity.public import COMPRADOR_PERMISSIONS
from app.identity.security import hash_password
from tests.ingestion_i0_fixtures import minimal_pdf_bytes


@pytest.fixture()
def comprador_client(client: TestClient, db: Session):
    role = db.query(Role).filter(Role.name == "comprador").first()
    assert role is not None
    # refresh perms from seed
    import json

    role.permissions_json = json.dumps(COMPRADOR_PERMISSIONS)
    user = User(
        email="comprador_i0@epic.com.br",
        name="Comprador I0",
        password_hash=hash_password("comprador123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    r = client.post(
        "/api/auth/login", json={"email": "comprador_i0@epic.com.br", "password": "comprador123"}
    )
    assert r.status_code == 200, r.text
    return client


@pytest.fixture()
def anon_client(client: TestClient):
    return client


def test_forbidden_without_auth(client: TestClient):
    r = client.post("/api/ingestion/batches", json={})
    assert r.status_code == 401


def test_admin_batch_upload_get(admin_client: TestClient):
    r = admin_client.post("/api/ingestion/batches", json={"notes": "i0"})
    assert r.status_code == 200, r.text
    batch_id = r.json()["id"]
    pdf = minimal_pdf_bytes()
    r2 = admin_client.post(
        f"/api/ingestion/batches/{batch_id}/files",
        files=[("files", ("doc.pdf", pdf, "application/pdf"))],
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["batch_id"] == batch_id
    assert len(body["results"]) == 1
    assert body["results"][0]["status"] == "STORED"
    occ_id = body["results"][0]["id"]
    r3 = admin_client.get(f"/api/ingestion/occurrences/{occ_id}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "STORED"
    r4 = admin_client.get(f"/api/ingestion/batches/{batch_id}")
    assert len(r4.json()["occurrences"]) == 1


def test_comprador_upload_no_purge(comprador_client: TestClient):
    r = comprador_client.post("/api/ingestion/batches", json={})
    assert r.status_code == 200
    batch_id = r.json()["id"]
    pdf = minimal_pdf_bytes()
    r2 = comprador_client.post(
        f"/api/ingestion/batches/{batch_id}/files",
        files=[("files", ("doc.pdf", pdf, "application/pdf"))],
    )
    assert r2.status_code == 200, r2.text
    r3 = comprador_client.post("/api/ingestion/purge", json={"dry_run": True})
    assert r3.status_code == 403


def test_multi_file_api(admin_client: TestClient):
    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    pdf = minimal_pdf_bytes()
    r2 = admin_client.post(
        f"/api/ingestion/batches/{batch_id}/files",
        files=[
            ("files", ("a.pdf", pdf, "application/pdf")),
            ("files", ("b.pdf", b"bad", "application/pdf")),
            ("files", ("c.pdf", pdf, "application/pdf")),
        ],
    )
    assert r2.status_code == 200, r2.text
    statuses = [x["status"] for x in r2.json()["results"]]
    assert statuses == ["STORED", "REJECTED", "STORED"]


def test_abandon_and_purge_dry_run(admin_client: TestClient):
    r = admin_client.post("/api/ingestion/batches", json={})
    batch_id = r.json()["id"]
    pdf = minimal_pdf_bytes()
    up = admin_client.post(
        f"/api/ingestion/batches/{batch_id}/files",
        files=[("files", ("a.pdf", pdf, "application/pdf"))],
    )
    occ_id = up.json()["results"][0]["id"]
    ab = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/abandon")
    assert ab.status_code == 200
    assert ab.json()["status"] == "ABANDONED"
    pr = admin_client.post("/api/ingestion/purge", json={"dry_run": True})
    assert pr.status_code == 200
    assert "blobs" in pr.json()
