import uuid

import pytest


@pytest.fixture
def sample_product(admin_client):
    sku = f"CAT-COL-{uuid.uuid4().hex[:8]}"
    r = admin_client.post(
        "/api/products",
        json={
            "sku_code": sku,
            "description": "Produto colunas teste",
            "product_group": "Raquetes",
            "lifecycle_status": "ACTIVE",
        },
    )
    assert r.status_code == 201
    return r.json()


def test_aggregate_product_quantities_empty(db):
    from app.services.product_catalog import _aggregate_product_quantities

    assert _aggregate_product_quantities(db, []) == {}


def test_list_product_groups(db, admin_client, sample_product):
    r = admin_client.get("/api/products/groups")
    assert r.status_code == 200
    groups = r.json()
    assert isinstance(groups, list)
    assert sample_product["product_group"] in groups


def test_catalog_includes_qty_fields(db, admin_client, sample_product):
    r = admin_client.get("/api/products/catalog?visibility=active")
    assert r.status_code == 200
    row = next(i for i in r.json()["items"] if i["sku_code"] == sample_product["sku_code"])
    for field in ("qty_ordered", "qty_in_transit", "qty_nationalization", "qty_stock"):
        assert field in row
        assert row[field] == 0


def test_catalog_filter_by_product_group(db, admin_client, sample_product):
    group = sample_product["product_group"]
    r = admin_client.get(f"/api/products/catalog?visibility=active&product_group={group}")
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["product_group"] == group
