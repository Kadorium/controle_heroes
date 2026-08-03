"""DR-UX — document content download + Order supplier_name enrichment."""

from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.documents.models import Document
from app.identity.models import Role, User
from app.identity.security import hash_password


def _sup_prod(client, tag="DRUX"):
    s = client.post("/api/suppliers", json={"name": f"Sup {tag}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": f"SKU-{tag}", "description": "A"}).json()
    return s, p


def test_order_detail_includes_supplier_name(admin_client):
    c = admin_client
    s, _ = _sup_prod(c, "NAME")
    o = c.post(
        "/api/orders",
        json={"code": "ORD-DRUX-SUP", "supplier_id": s["id"], "order_date": "2026-06-04"},
    ).json()
    r = c.get(f"/api/orders/{o['id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["supplier_id"] == s["id"]
    assert body["supplier_name"] == s["name"]
    assert body["supplier_is_active"] is True


def test_order_detail_inactive_supplier(admin_client, db: Session):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": "Sup Inactive", "country_code": "IT"}).json()
    from app.catalog.models import Supplier

    row = db.get(Supplier, s["id"])
    assert row is not None
    row.is_active = False
    db.commit()

    o = c.post(
        "/api/orders",
        json={"code": "ORD-DRUX-INACT", "supplier_id": s["id"]},
    ).json()
    body = c.get(f"/api/orders/{o['id']}").json()
    assert body["supplier_name"] == "Sup Inactive"
    assert body["supplier_is_active"] is False


def test_document_content_download_ok(admin_client, db: Session):
    c = admin_client
    s, _ = _sup_prod(c, "DOC")
    o = c.post("/api/orders", json={"code": "ORD-DRUX-DOC", "supplier_id": s["id"]}).json()
    payload = b"%PDF-1.4 drux-bytes"
    up = c.post(
        "/api/documents",
        data={"entity_type": "order", "entity_id": str(o["id"]), "role": "official"},
        files={"file": ("Ordine.pdf", BytesIO(payload), "application/pdf")},
    )
    assert up.status_code in (200, 201), up.text
    doc_id = up.json()["id"]
    before = db.query(AuditLog).filter(AuditLog.entity_type == "document").count()

    r = c.get(f"/api/documents/{doc_id}/content")
    assert r.status_code == 200, r.text
    assert r.content == payload
    assert r.headers.get("content-type", "").startswith("application/pdf")
    cd = r.headers.get("content-disposition", "")
    assert "inline" in cd.lower() or "filename" in cd.lower()
    assert "Ordine.pdf" in cd
    assert "absolute" not in r.text.lower()
    assert "attachments" not in r.text.lower()
    assert ".." not in cd

    after = db.query(AuditLog).filter(AuditLog.entity_type == "document").count()
    assert after == before  # GET content não cria Audit

    r_dl = c.get(f"/api/documents/{doc_id}/content?download=1")
    assert r_dl.status_code == 200
    assert "attachment" in r_dl.headers.get("content-disposition", "").lower()
    assert r_dl.content == payload


def test_document_content_404_missing(admin_client):
    c = admin_client
    r = c.get("/api/documents/999999/content")
    assert r.status_code == 404
    assert "attachments" not in r.text.lower()
    assert "\\" not in r.text


def test_document_content_404_missing_file(admin_client, db: Session):
    c = admin_client
    s, _ = _sup_prod(c, "MISS")
    o = c.post("/api/orders", json={"code": "ORD-DRUX-MISS", "supplier_id": s["id"]}).json()
    up = c.post(
        "/api/documents",
        data={"entity_type": "order", "entity_id": str(o["id"]), "role": "official"},
        files={"file": ("gone.pdf", BytesIO(b"%PDF-1.4 gone"), "application/pdf")},
    )
    assert up.status_code in (200, 201), up.text
    doc_id = up.json()["id"]
    doc = db.get(Document, doc_id)
    assert doc is not None
    path = Path(doc.storage_path)
    # storage_path is relative; resolve via attachments if needed
    from app.foundation.settings import get_settings

    full = Path(get_settings().attachments_path) / doc.storage_path
    assert full.is_file()
    full.unlink()
    r = c.get(f"/api/documents/{doc_id}/content")
    assert r.status_code == 404
    assert "attachments" not in r.text.lower()
    assert str(full) not in r.text


def test_document_content_path_traversal_rejected(admin_client, db: Session):
    c = admin_client
    s, _ = _sup_prod(c, "TRAV")
    o = c.post("/api/orders", json={"code": "ORD-DRUX-TRAV", "supplier_id": s["id"]}).json()
    up = c.post(
        "/api/documents",
        data={"entity_type": "order", "entity_id": str(o["id"]), "role": "official"},
        files={"file": ("ok.pdf", BytesIO(b"%PDF-1.4 ok"), "application/pdf")},
    )
    doc_id = up.json()["id"]
    doc = db.get(Document, doc_id)
    assert doc is not None
    doc.storage_path = "../etc/passwd"
    db.commit()
    r = c.get(f"/api/documents/{doc_id}/content")
    assert r.status_code == 404
    assert "passwd" not in r.text.lower()
    assert "etc" not in r.text.lower()


def test_document_content_403_without_entity_permission(admin_client, client, db: Session):
    """documents:read alone is insufficient — need linked entity read permission."""
    c = admin_client
    sh = c.post("/api/shipments", json={}).json()
    up = c.post(
        "/api/documents",
        data={"entity_type": "shipment", "entity_id": str(sh["id"]), "role": "official"},
        files={"file": ("PL.pdf", BytesIO(b"%PDF-1.4 pl"), "application/pdf")},
    )
    assert up.status_code in (200, 201), up.text
    doc_id = up.json()["id"]

    role = Role(
        name="docs_only_drux",
        description="Somente documents:read",
        permissions_json='["documents:read"]',
    )
    db.add(role)
    db.flush()
    user = User(
        email="docs-only-drux@epic.com.br",
        name="Docs Only",
        password_hash=hash_password("docs12345"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    login = client.post(
        "/api/auth/login",
        json={"email": "docs-only-drux@epic.com.br", "password": "docs12345"},
    )
    assert login.status_code == 200, login.text
    r = client.get(f"/api/documents/{doc_id}/content")
    assert r.status_code == 403, r.text
