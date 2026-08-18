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


def test_patch_product_and_supplier(admin_client):
    c = admin_client
    r = c.post("/api/suppliers", json={"name": "Patch Co", "code": "PATCH-CO"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    r = c.patch(f"/api/suppliers/{sid}", json={"name": "Patch Co Renomeado", "is_active": False})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Patch Co Renomeado"
    assert r.json()["is_active"] is False

    r = c.post("/api/products", json={"sku": "PATCH-SKU", "description": "Antes"})
    assert r.status_code == 201
    pid = r.json()["id"]
    r = c.patch(f"/api/products/{pid}", json={"description": "Depois"})
    assert r.status_code == 200, r.text
    assert r.json()["description"] == "Depois"


def test_product_list_report_envelope(admin_client):
    c = admin_client
    c.post("/api/products", json={"sku": "ENV-A", "description": "Alpha"})
    c.post("/api/products", json={"sku": "ENV-B", "description": "Beta"})
    r = c.get("/api/catalog/product-list", params={"q": "ENV-", "limit": 1, "offset": 0})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body and "total" in body
    assert body["total"] >= 2
    assert body["limit"] == 1
    assert isinstance(body["items"], list)
    r_arr = c.get("/api/products", params={"q": "ENV-"})
    assert r_arr.status_code == 200
    assert isinstance(r_arr.json(), list)


def test_supplier_list_report_envelope(admin_client):
    c = admin_client
    c.post("/api/suppliers", json={"name": "Envelope Ltda"})
    r = c.get("/api/catalog/supplier-list", params={"q": "Envelope"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert isinstance(body["items"], list)


def test_patch_l006_and_tax_id(admin_client):
    c = admin_client
    r = c.post("/api/products", json={"sku": "L006-SKU", "description": "Camisa"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = c.patch(
        f"/api/products/{pid}",
        json={
            "ncm": "61.09.10.00",
            "ean": "7891234567890",
            "size": "  M  ",
            "color": "Preto",
            "country_of_origin": "it",
            "unit": "pz",
            "net_weight_kg": "0.2500",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ncm"] == "61091000"
    assert body["ean"] == "7891234567890"
    assert body["size"] == "M"
    assert body["color"] == "Preto"
    assert body["country_of_origin"] == "IT"
    assert body["unit"] == "PZ"
    assert float(body["net_weight_kg"]) == 0.25

    r = c.patch(f"/api/products/{pid}", json={"net_weight_kg": "0"})
    assert r.status_code == 422, r.text

    r = c.post("/api/products", json={"sku": "L006-SKU-2", "description": "Outro"})
    pid2 = r.json()["id"]
    r = c.patch(f"/api/products/{pid2}", json={"ean": "7891234567890"})
    assert r.status_code in (409, 422), r.text

    r = c.get("/api/catalog/product-list", params={"incomplete": True, "q": "L006-"})
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["items"]]
    assert pid2 in ids

    r = c.get("/api/catalog/product-attribute-values", params={"field": "size"})
    assert r.status_code == 200
    assert "M" in r.json()["values"]

    r = c.post(
        "/api/suppliers",
        json={"name": "IVA Co", "country_code": "IT", "tax_id": "IT02610500395"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["tax_id"] == "02610500395"
    sid = r.json()["id"]
    r = c.post(
        "/api/suppliers",
        json={"name": "IVA Dup", "country_code": "IT", "tax_id": "02610500395"},
    )
    assert r.status_code in (409, 422), r.text
    r = c.patch(f"/api/suppliers/{sid}", json={"tax_id": "02610500395"})
    assert r.status_code == 200


def test_inactive_sku_still_unique(admin_client):
    c = admin_client
    r = c.post("/api/products", json={"sku": "UNIQUE-X", "description": "a", "is_active": False})
    assert r.status_code == 201
    r = c.post("/api/products", json={"sku": "UNIQUE-X", "description": "b", "is_active": True})
    assert r.status_code == 409
