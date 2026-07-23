"""Catalog API Inc-1."""


def test_create_list_search_supplier_product(admin_client):
    c = admin_client
    r = c.post(
        "/api/suppliers",
        json={"name": "Catalog Co", "code": "CAT-CO", "country_code": "IT"},
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    r = c.get("/api/suppliers", params={"q": "Catalog"})
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    r = c.post("/api/products", json={"sku": "CAT-SKU-1", "description": "Item A", "is_active": True})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = c.get("/api/products", params={"q": "CAT-SKU"})
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    r = c.get(f"/api/products/{pid}")
    assert r.status_code == 200
    assert r.json()["sku"] == "CAT-SKU-1"


def test_inactive_sku_still_unique(admin_client):
    c = admin_client
    r = c.post("/api/products", json={"sku": "UNIQUE-X", "description": "a", "is_active": False})
    assert r.status_code == 201
    r = c.post("/api/products", json={"sku": "UNIQUE-X", "description": "b", "is_active": True})
    assert r.status_code == 409
