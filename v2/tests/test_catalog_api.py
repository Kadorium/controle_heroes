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
    assert "summary" in r.json()
    assert "incomplete" in r.json()["summary"]

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


def test_product_list_facets_summary_and_beyond_50(admin_client):
    c = admin_client
    for i in range(1, 56):
        r = c.post(
            "/api/products",
            json={"sku": f"MASS-{i:03d}", "description": f"Massa visual {i}"},
        )
        assert r.status_code == 201, r.text
    r = c.patch(
        "/api/products/" + str(c.get("/api/catalog/product-list", params={"q": "MASS-001"}).json()["items"][0]["id"]),
        json={"size": "M", "color": "Red", "country_of_origin": "IT", "ncm": "42029200", "ean": "7900000000001"},
    )
    assert r.status_code == 200, r.text
    r = c.patch(
        "/api/products/" + str(c.get("/api/catalog/product-list", params={"q": "MASS-002"}).json()["items"][0]["id"]),
        json={"size": "L", "color": "Blue", "is_active": False},
    )
    assert r.status_code == 200

    page = c.get("/api/catalog/product-list", params={"q": "MASS-", "limit": 50, "offset": 0})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] >= 55
    assert body["summary"]["total"] >= 55
    assert "MASS-055" not in [x["sku"] for x in body["items"]]

    found = c.get("/api/catalog/product-list", params={"q": "MASS-055"})
    assert found.status_code == 200
    assert any(x["sku"] == "MASS-055" for x in found.json()["items"])

    picker = c.get("/api/products", params={"q": "MASS-055", "active_only": True, "limit": 20})
    assert picker.status_code == 200
    assert any(x["sku"] == "MASS-055" for x in picker.json())

    sizes = c.get("/api/catalog/product-attribute-values", params={"field": "country_of_origin"})
    assert sizes.status_code == 200
    assert "IT" in sizes.json()["values"]

    origin = c.get("/api/catalog/product-list", params={"origin": "IT", "q": "MASS-"})
    assert origin.status_code == 200
    assert all(x["country_of_origin"] == "IT" for x in origin.json()["items"])

    multi = c.get("/api/catalog/product-list", params={"size": "M,L", "q": "MASS-"})
    assert multi.status_code == 200
    assert {x["size"] for x in multi.json()["items"]} <= {"M", "L"}

    inactive = c.get("/api/catalog/product-list", params={"is_active": False, "q": "MASS-"})
    assert inactive.status_code == 200
    assert all(x["is_active"] is False for x in inactive.json()["items"])

    active_picker = c.get("/api/products", params={"q": "MASS-002", "active_only": True})
    assert active_picker.status_code == 200
    assert all(x["sku"] != "MASS-002" for x in active_picker.json())

