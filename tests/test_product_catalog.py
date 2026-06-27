"""Testes cadastro mestre produtos."""

import uuid

import pytest


@pytest.fixture()
def supplier(admin_client):
    r = admin_client.post(
        "/api/suppliers",
        json={"name": "Heroes Catalog Test", "country": "CN", "currency_default": "EUR"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def sample_product(admin_client):
    sku = f"CAT-{uuid.uuid4().hex[:8]}"
    r = admin_client.post(
        "/api/products",
        json={
            "sku_code": sku,
            "description": "Produto catálogo teste",
            "product_group": "Raquetes",
            "lifecycle_status": "ACTIVE",
        },
    )
    assert r.status_code == 201
    return r.json()


def test_catalog_active_visibility(db, admin_client, sample_product):
    r = admin_client.get("/api/products/catalog?visibility=active")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(i["sku_code"] == sample_product["sku_code"] for i in data["items"])


def test_create_minimal_fields_null_weight(admin_client):
    r = admin_client.post(
        "/api/products",
        json={
            "sku_code": "CAT-NULL-W",
            "description": "Sem peso",
            "product_group": "Teste",
            "lifecycle_status": "ACTIVE",
            "weight_kg": None,
        },
    )
    assert r.status_code == 201
    assert r.json()["weight_kg"] is None


def test_archive_hides_from_active(db, admin_client, sample_product):
    pid = sample_product["id"]
    r = admin_client.post(f"/api/products/{pid}/archive", json={"reason": "Não trabalhado mais"})
    assert r.status_code == 200
    cat = admin_client.get("/api/products/catalog?visibility=active").json()
    assert not any(i["id"] == pid for i in cat["items"])
    archived = admin_client.get("/api/products/catalog?visibility=archived").json()
    assert any(i["id"] == pid for i in archived["items"])


def test_restore_from_archive(db, admin_client, sample_product):
    pid = sample_product["id"]
    admin_client.post(f"/api/products/{pid}/archive", json={"reason": "Teste arquivar"})
    r = admin_client.post(f"/api/products/{pid}/restore")
    assert r.status_code == 200
    assert r.json()["lifecycle_status"] == "ACTIVE"


def test_ncm_change_requires_reason_when_used(db, admin_client, sample_product, supplier):
    pid = sample_product["id"]
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": "PO-NCM-TEST",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [{"product_id": pid, "quantity_ordered": 1, "unit_price_foreign": "10"}],
        },
    ).json()
    assert imp["id"]
    r = admin_client.patch(f"/api/products/{pid}", json={"ncm": "95069900"})
    assert r.status_code == 422
    r2 = admin_client.patch(
        f"/api/products/{pid}",
        json={"ncm": "95069900", "ncm_change_reason": "Classificação revisada fiscal"},
    )
    assert r2.status_code == 200
    audit = admin_client.get(f"/api/products/{pid}/audit").json()
    assert any(a.get("field_changed") == "ncm" for a in audit)


def test_discontinued_blocked_without_override(admin_client, sample_product, supplier):
    pid = sample_product["id"]
    admin_client.patch(f"/api/products/{pid}", json={"lifecycle_status": "DISCONTINUED"})
    imp = admin_client.post(
        "/api/importations",
        json={"po_number": "PO-DISC-001", "supplier_id": supplier["id"], "currency": "EUR"},
    ).json()
    r = admin_client.post(
        f"/api/importations/{imp['id']}/items",
        json={"product_id": pid, "quantity_ordered": 1},
    )
    assert r.status_code == 422


def test_product_orders_endpoint(db, admin_client, sample_product, supplier):
    pid = sample_product["id"]
    admin_client.post(
        "/api/importations",
        json={
            "po_number": "PO-ORD-LIST",
            "supplier_id": supplier["id"],
            "currency": "EUR",
            "items": [{"product_id": pid, "quantity_ordered": 5, "unit_price_foreign": "12"}],
        },
    )
    r = admin_client.get(f"/api/products/{pid}/orders")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert r.json()["items"][0]["po_number"] == "PO-ORD-LIST"


def test_pending_flags_ncm():
    from app.models import Product
    from app.services.product_catalog import compute_pending_flags

    p = Product(sku_code="X", description="Y", product_group="G", ncm=None)
    assert "ncm_pending" in compute_pending_flags(p, has_photo=False)


def test_combobox_excludes_discontinued(admin_client, sample_product):
    pid = sample_product["id"]
    admin_client.patch(f"/api/products/{pid}", json={"lifecycle_status": "DISCONTINUED"})
    r = admin_client.get("/api/products?for_combobox=true")
    assert not any(p["id"] == pid for p in r.json())


def test_bulk_archive_partial_skip(admin_client, sample_product):
    pid = sample_product["id"]
    admin_client.post(f"/api/products/{pid}/archive", json={"reason": "Já arquivado teste"})
    r = admin_client.post(
        "/api/products/bulk/archive",
        json={"product_ids": [pid, 999999], "reason": "Bulk archive test"},
    )
    assert r.status_code == 200
    data = r.json()
    assert any(s["id"] == pid for s in data["skipped"])
    assert not data["succeeded"]


def test_bulk_discontinue_and_reactivate(admin_client, sample_product):
    pid = sample_product["id"]
    r = admin_client.post(
        "/api/products/bulk/status",
        json={"product_ids": [pid], "lifecycle_status": "DISCONTINUED"},
    )
    assert r.status_code == 200
    assert pid in r.json()["succeeded"]
    r2 = admin_client.post(
        "/api/products/bulk/status",
        json={"product_ids": [pid], "lifecycle_status": "ACTIVE"},
    )
    assert pid in r2.json()["succeeded"]


def test_bulk_cancel_route_not_shadowed(admin_client, sample_product):
    """POST /bulk/cancel must not match /{product_id}/cancel (product_id=bulk)."""
    pid = sample_product["id"]
    r = admin_client.post(
        "/api/products/bulk/cancel",
        json={"product_ids": [pid], "reason": "Exclusão em massa teste"},
    )
    assert r.status_code == 200, r.text
    assert pid in r.json()["succeeded"]
    cat = admin_client.get("/api/products/catalog?visibility=cancelled").json()
    assert any(i["id"] == pid for i in cat["items"])


def test_import_preview_csv(admin_client):
    csv_content = "sku_code,description,product_group,lifecycle_status\nIMP-001,Import Test,Grupo,ACTIVE\n,BAD,,"
    import io

    r = admin_client.post(
        "/api/products/import/preview",
        files={"file": ("produtos.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid_count"] == 1
    assert data["invalid_count"] == 1


def test_import_preview_heroes_csv_columns(admin_client):
    csv_content = (
        "sku_sugerido,nome_produto,grupo,subgrupo,status_produto,pais_origem,peso_kg\n"
        "HEROES-TEST-001,Raquete Teste,RAQUETES,BT,ACTIVE,ITALIA,0.325\n"
    )
    import io

    r = admin_client.post(
        "/api/products/import/preview",
        files={"file": ("heroes.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid_count"] == 1
    row = data["rows"][0]
    assert row["data"]["sku_code"] == "HEROES-TEST-001"
    assert row["data"]["country_of_origin"] == "IT"


def test_export_xlsx(admin_client):
    r = admin_client.get("/api/products/export?format=xlsx")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
