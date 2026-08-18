"""Logistics J#4 + J4-UX1 API tests."""

from decimal import Decimal


def _sup_prod_order(client, *, tag="L4", qty="10"):
    s = client.post("/api/suppliers", json={"name": f"Sup {tag}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": f"SKU-{tag}", "description": f"P {tag}"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{tag}", "supplier_id": s["id"], "currency": "EUR", "external_ref": f"EXT-{tag}"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={"expected_version": o["version"], "product_id": p["id"], "quantity": qty, "unit_price": "5"},
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    return s, p, o


def _provider(client, *, tag="P1", provider_type="TRANSPORTADOR", active=True, trade_name=None):
    body = {
        "legal_name": f"Provider {tag} LTDA",
        "provider_type": provider_type,
        "active": active,
    }
    if trade_name is not None:
        body["trade_name"] = trade_name
    r = client.post("/api/logistics-providers", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_shipment_create_item_advance_annul(admin_client):
    c = admin_client
    _, _, order = _sup_prod_order(c, tag="A1")
    item_id = order["items"][0]["id"]
    provider = _provider(c, tag="A1", trade_name="Carrier A1")

    r = c.post(
        "/api/shipments",
        json={"modal": "SEA", "logistics_provider_id": provider["id"]},
    )
    assert r.status_code == 201, r.text
    sh = r.json()
    assert sh["code"].startswith("SHP-")
    assert sh["status"] == "PLANNED"
    assert sh["version"] == 1
    assert sh["logistics_provider_id"] == provider["id"]
    assert sh["carrier_name_snapshot"] == "Carrier A1"

    audit = c.get("/api/audit", params={"entity_type": "shipment", "entity_id": str(sh["id"])})
    assert audit.status_code == 200, audit.text
    creates = [row for row in audit.json() if row["action"] == "shipment.create"]
    assert len(creates) == 1

    r = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": item_id, "quantity": "4"},
    )
    assert r.status_code == 201, r.text
    sh = r.json()
    assert len(sh["items"]) == 1
    assert sh["items"][0]["quantity"] == "4.0000" or sh["items"][0]["quantity"].startswith("4")

    r = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": item_id, "quantity": "1"},
    )
    assert r.status_code == 400, r.text

    r = c.post(
        f"/api/shipments/{sh['id']}/advance",
        json={"expected_version": sh["version"], "event_date": "2026-07-01"},
    )
    assert r.status_code == 200, r.text
    sh = r.json()
    assert sh["status"] == "BOOKED"

    r = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={"expected_version": sh["version"], "package_type": "CARTON", "package_count": 1},
    )
    assert r.status_code == 409, r.text


def test_invalid_modal_rejected(admin_client):
    c = admin_client
    r = c.post("/api/shipments", json={"modal": "TRAIN"})
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "invalid_modal"


def test_planned_without_provider_ok(admin_client):
    c = admin_client
    r = c.post("/api/shipments", json={"modal": "AIR"})
    assert r.status_code == 201, r.text
    sh = r.json()
    assert sh["logistics_provider_id"] is None
    assert sh["modal"] == "AIR"


def test_booked_requires_modal_and_provider(admin_client):
    c = admin_client
    _, _, order = _sup_prod_order(c, tag="BK")
    item_id = order["items"][0]["id"]
    provider = _provider(c, tag="BK")

    sh = c.post("/api/shipments", json={}).json()
    sh = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": item_id, "quantity": "1"},
    ).json()
    r = c.post(
        f"/api/shipments/{sh['id']}/advance",
        json={"expected_version": sh["version"], "event_date": "2026-07-01"},
    )
    assert r.status_code == 409, r.text
    assert "modal" in r.json()["message"].lower()

    sh = c.patch(
        f"/api/shipments/{sh['id']}",
        json={"expected_version": sh["version"], "modal": "SEA"},
    ).json()
    r = c.post(
        f"/api/shipments/{sh['id']}/advance",
        json={"expected_version": sh["version"], "event_date": "2026-07-01"},
    )
    assert r.status_code == 409, r.text
    assert "prestador" in r.json()["message"].lower()

    sh = c.patch(
        f"/api/shipments/{sh['id']}",
        json={"expected_version": sh["version"], "logistics_provider_id": provider["id"]},
    ).json()
    r = c.post(
        f"/api/shipments/{sh['id']}/advance",
        json={"expected_version": sh["version"], "event_date": "2026-07-01"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "BOOKED"


def test_inactive_and_despachante_not_selectable(admin_client):
    c = admin_client
    inactive = _provider(c, tag="INACT", active=False)
    desp = _provider(c, tag="DESP", provider_type="DESPACHANTE")

    r = c.post("/api/shipments", json={"logistics_provider_id": inactive["id"]})
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "provider_inactive"

    r = c.post("/api/shipments", json={"logistics_provider_id": desp["id"]})
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "provider_type_not_eligible"


def test_list_filters_modal_and_provider(admin_client):
    c = admin_client
    p1 = _provider(c, tag="F1", trade_name="F1")
    p2 = _provider(c, tag="F2", trade_name="F2")
    c.post("/api/shipments", json={"modal": "SEA", "logistics_provider_id": p1["id"]})
    c.post("/api/shipments", json={"modal": "AIR", "logistics_provider_id": p2["id"]})

    sea = c.get("/api/shipments", params={"modal": "SEA"}).json()
    assert all(x["modal"] == "SEA" for x in sea)
    assert any(x["logistics_provider_id"] == p1["id"] for x in sea)

    by_p = c.get("/api/shipments", params={"logistics_provider_id": p2["id"]}).json()
    assert all(x["logistics_provider_id"] == p2["id"] for x in by_p)


def test_provider_list_shipment_eligible(admin_client):
    c = admin_client
    _provider(c, tag="ELIG", provider_type="TRANSPORTADOR")
    _provider(c, tag="CUST", provider_type="DESPACHANTE")
    rows = c.get(
        "/api/logistics-providers",
        params={"shipment_eligible_only": True, "active_only": True},
    ).json()
    assert all(x["provider_type"] != "DESPACHANTE" for x in rows)
    assert any(x["legal_name"].startswith("Provider ELIG") for x in rows)


def test_overship_and_package_derived(admin_client):
    c = admin_client
    _, _, order = _sup_prod_order(c, tag="A2", qty="5")
    item_id = order["items"][0]["id"]
    sh = c.post("/api/shipments", json={}).json()
    r = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": item_id, "quantity": "6"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "overship"

    sh = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": item_id, "quantity": "2"},
    ).json()

    r = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={
            "expected_version": sh["version"],
            "package_type": "CARTON",
            "package_count": 3,
            "net_weight_kg": "10",
            "length": "100",
            "width": "50",
            "height": "40",
            "dimension_unit": "CM",
        },
    )
    assert r.status_code == 201, r.text
    sh = r.json()
    pkg = sh["packages"][0]
    assert pkg["package_count"] == 3
    assert pkg["volume_is_derived"] is True
    assert Decimal(pkg["volume_m3"]) == Decimal("0.200000")

    d = c.get(f"/api/shipments/{sh['id']}/totals/derived").json()
    assert Decimal(d["net_weight_kg"]) == Decimal("30.0000") or Decimal(d["net_weight_kg"]) == Decimal("30")
    assert d["carton_count"] == 3


def test_candidates_sku_only_400(admin_client):
    c = admin_client
    r = c.get("/api/shipments/order-item-candidates", params={"sku": "X"})
    assert r.status_code == 400, r.text


def test_parent_count_rule(admin_client):
    c = admin_client
    sh = c.post("/api/shipments", json={}).json()
    sh = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={"expected_version": sh["version"], "package_type": "PALLET", "package_count": 2},
    ).json()
    parent_id = sh["packages"][0]["id"]
    r = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={
            "expected_version": sh["version"],
            "package_type": "CARTON",
            "package_count": 1,
            "parent_package_id": parent_id,
        },
    )
    assert r.status_code == 400, r.text


def test_logistics_providers_rbac(client, db, admin_client):
    import json

    from app.identity.models import Role, User
    from app.identity.security import hash_password

    role = Role(
        name="logistics_reader_ux1",
        description="r",
        permissions_json=json.dumps(["logistics:read"]),
    )
    db.add(role)
    db.flush()
    db.add(
        User(
            email="logread@example.com",
            name="Log Reader",
            password_hash=hash_password("test123"),
            role_id=role.id,
            is_active=True,
        )
    )
    db.commit()
    r = client.post("/api/auth/login", json={"email": "logread@example.com", "password": "test123"})
    assert r.status_code == 200, r.text
    assert client.get("/api/logistics-providers").status_code == 200
    assert (
        client.post(
            "/api/logistics-providers",
            json={"legal_name": "X", "provider_type": "TRANSPORTADOR"},
        ).status_code
        == 403
    )
    assert admin_client.get("/api/shipments").status_code == 200


def test_logistics_providers_q_filter(admin_client):
    c = admin_client
    _provider(c, tag="AlphaSearch", trade_name="Alpha Trade")
    _provider(c, tag="BetaOther", trade_name="Other")
    r = c.get("/api/logistics-providers", params={"q": "Alpha"})
    assert r.status_code == 200, r.text
    names = [x["legal_name"] for x in r.json()]
    assert any("AlphaSearch" in n for n in names)
    assert not any("BetaOther" in n for n in names)


def test_delete_empty_and_annul(admin_client):
    c = admin_client
    sh = c.post("/api/shipments", json={}).json()
    r = c.delete(f"/api/shipments/{sh['id']}", params={"expected_version": sh["version"]})
    assert r.status_code == 204, r.text

    _, _, order = _sup_prod_order(c, tag="A3")
    sh = c.post("/api/shipments", json={}).json()
    sh = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={
            "expected_version": sh["version"],
            "order_item_id": order["items"][0]["id"],
            "quantity": "1",
        },
    ).json()
    r = c.post(f"/api/shipments/{sh['id']}/annul", json={"expected_version": sh["version"]})
    assert r.status_code == 200, r.text
    assert r.json()["cancelled_at"] is not None
    rows = c.get("/api/shipments").json()
    assert all(x["id"] != sh["id"] for x in rows)
