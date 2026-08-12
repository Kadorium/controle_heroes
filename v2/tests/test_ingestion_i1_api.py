"""J3-I1 — API + RBAC for staging IR."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.ingestion_i0_fixtures import minimal_pdf_bytes


def _upload_stored(admin_client: TestClient, tag: str = "api") -> tuple[int, int]:
    r = admin_client.post("/api/ingestion/batches", json={"notes": "i1"})
    assert r.status_code == 200, r.text
    batch_id = r.json()["id"]
    pdf = minimal_pdf_bytes(tag=tag)
    r2 = admin_client.post(
        f"/api/ingestion/batches/{batch_id}/files",
        files=[("files", (f"{tag}.pdf", pdf, "application/pdf"))],
    )
    assert r2.status_code == 200, r2.text
    occ_id = r2.json()["results"][0]["id"]
    assert r2.json()["results"][0]["status"] == "STORED"
    return batch_id, occ_id


def test_seed_and_correct_via_api(admin_client: TestClient):
    batch_id, occ_id = _upload_stored(admin_client, "seed-api")
    r = admin_client.post(
        "/api/ingestion/documents",
        json={
            "occurrence_id": occ_id,
            "doc_type": "ORDINE",
            "sections": [{"section_key": "h", "title": "H"}],
            "fields": [
                {
                    "field_key": "supplier",
                    "raw_value": "ACME",
                    "section_key": "h",
                    "locator_json": None,
                },
                {"field_key": "qty", "raw_value": None, "value_type": "number", "section_key": "h"},
            ],
            "issues": [{"code": "X", "message": "warn", "severity": "WARNING"}],
        },
    )
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["occurrence_id"] == occ_id
    assert doc["batch_id"] == batch_id
    assert doc["open_issue_count"] == 1
    qty = next(f for f in doc["fields"] if f["field_key"] == "qty")
    assert qty["raw_value"] is None
    assert qty["effective_value"] is None

    # quarantine content for viewer
    rc = admin_client.get(f"/api/ingestion/occurrences/{occ_id}/content")
    assert rc.status_code == 200
    assert rc.content[:4] == b"%PDF" or len(rc.content) > 0

    supplier = next(f for f in doc["fields"] if f["field_key"] == "supplier")
    r2 = admin_client.patch(
        f"/api/ingestion/fields/{supplier['id']}",
        json={"corrected_value": "ACME SPA", "expected_version": supplier["version"]},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["raw_value"] == "ACME"
    assert r2.json()["corrected_value"] == "ACME SPA"
    assert r2.json()["effective_value"] == "ACME SPA"

    # stale version → 409
    r3 = admin_client.patch(
        f"/api/ingestion/fields/{supplier['id']}",
        json={"corrected_value": "X", "expected_version": supplier["version"]},
    )
    assert r3.status_code == 409

    r4 = admin_client.get(f"/api/ingestion/documents/{doc['id']}/changes")
    assert r4.status_code == 200
    assert len(r4.json()) >= 1

    r5 = admin_client.get("/api/ingestion/staging/queue")
    assert r5.status_code == 200
    assert any(d["id"] == doc["id"] for d in r5.json())


def test_document_set_api(admin_client: TestClient):
    batch_id, occ_id = _upload_stored(admin_client, "set-api")
    r = admin_client.post(
        "/api/ingestion/documents",
        json={"occurrence_id": occ_id, "doc_type": "ORDINE"},
    )
    doc_id = r.json()["id"]
    rs = admin_client.post(
        "/api/ingestion/document-sets",
        json={"batch_id": batch_id, "projection_key": "k1", "label": "set"},
    )
    assert rs.status_code == 200, rs.text
    set_id = rs.json()["id"]
    rm = admin_client.post(
        f"/api/ingestion/document-sets/{set_id}/members",
        json={"document_id": doc_id, "role": "primary"},
    )
    assert rm.status_code == 200, rm.text
    rg = admin_client.get(f"/api/ingestion/document-sets/{set_id}")
    assert len(rg.json()["members"]) == 1


def test_unauth_staging(client: TestClient):
    r = client.get("/api/ingestion/staging/queue")
    assert r.status_code == 401
