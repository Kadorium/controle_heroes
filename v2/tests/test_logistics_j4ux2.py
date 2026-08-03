"""J4-UX2 — PackageContent snapshots, batch packages, DocumentSummary provenance."""

from decimal import Decimal
from io import BytesIO


def _sup_prod_order(client, *, tag="UX2", qty="100"):
    s = client.post("/api/suppliers", json={"name": f"Sup {tag}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": f"SKU-{tag}", "description": f"P {tag}"}).json()
    o = client.post(
        "/api/orders",
        json={
            "code": f"ORD-{tag}",
            "supplier_id": s["id"],
            "currency": "EUR",
            "external_ref": f"EXT-{tag}",
        },
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": qty,
            "unit_price": "5",
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    return s, p, o


def _upload_shipment_doc(client, shipment_id: int, name: str = "pl.pdf"):
    r = client.post(
        "/api/documents",
        data={"entity_type": "shipment", "entity_id": str(shipment_id), "role": "official"},
        files={"file": (name, BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_package_content_snapshots_and_packaging_ncm(admin_client):
    c = admin_client
    _, _, order = _sup_prod_order(c, tag="SNAP")
    item_id = order["items"][0]["id"]
    sh = c.post("/api/shipments", json={}).json()
    sh = c.post(
        f"/api/shipments/{sh['id']}/items",
        json={"expected_version": sh["version"], "order_item_id": item_id, "quantity": "6"},
    ).json()
    si_id = sh["items"][0]["id"]

    # Package físico + NCM embalagem (sem item)
    sh = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={
            "expected_version": sh["version"],
            "package_type": "CARTON",
            "package_count": 1,
            "external_package_no": "1",
            "packaging_ncm": "4819100000",
            "description": "Imballaggio",
            "length": "47",
            "width": "34",
            "height": "56",
            "dimension_unit": "CM",
            "raw_dimensions": "47,00x34,00x56,00",
            "net_weight_kg": "5.40",
            "gross_weight_kg": "6.00",
        },
    ).json()
    pkg = sh["packages"][0]
    assert pkg["external_package_no"] == "1"
    assert pkg["packaging_ncm"] == "4819100000"
    assert pkg["volume_is_derived"] is True
    assert Decimal(pkg["net_weight_kg"]) == Decimal("5.4000") or Decimal(pkg["net_weight_kg"]) == Decimal(
        "5.4"
    )

    # Segunda linha comercial com NCM produto nos contents (não packaging_ncm)
    sh = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={
            "expected_version": sh["version"],
            "package_type": "CARTON",
            "package_count": 1,
            "external_package_no": "2",
            "net_weight_kg": "5.40",
            "gross_weight_kg": "6.00",
            "raw_dimensions": "47,00x34,00x56,00",
            "length": "47",
            "width": "34",
            "height": "56",
            "dimension_unit": "CM",
        },
    ).json()
    pkg2 = next(p for p in sh["packages"] if p["external_package_no"] == "2")

    r = c.put(
        f"/api/shipments/{sh['id']}/packages/{pkg2['id']}/contents",
        json={
            "expected_version": sh["version"],
            "contents": [
                {
                    "shipment_item_id": si_id,
                    "contained_quantity": "6",
                    "units_per_package": "6",
                    "source_unit": "PZ",
                    "source_ncm": "4202221000",
                    "source_description": "GRAVITY ARION",
                    "unit_net_weight_kg": "0.90",
                    "unit_gross_weight_kg": "1.00",
                    "source_total_net_weight_kg": "5.40",
                    "source_total_gross_weight_kg": "6.00",
                    "source_line_reference": "PL-202-L1",
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    sh = r.json()
    content = next(p for p in sh["packages"] if p["id"] == pkg2["id"])["contents"][0]
    assert content["source_ncm"] == "4202221000"
    assert content["units_per_package"] in ("6", "6.0000")
    assert content["unit_net_weight_kg"] in ("0.9", "0.90", "0.9000")
    assert content["source_total_net_weight_kg"] in ("5.4", "5.40", "5.4000")
    # packaging NCM do outro package permanece distinto
    assert next(p for p in sh["packages"] if p["external_package_no"] == "1")["packaging_ncm"] == "4819100000"
    assert next(p for p in sh["packages"] if p["id"] == pkg2["id"]).get("packaging_ncm") in (None, "")


def test_packages_batch_range_scale(admin_client):
    c = admin_client
    sh = c.post("/api/shipments", json={}).json()
    r = c.post(
        f"/api/shipments/{sh['id']}/packages/batch",
        json={
            "expected_version": sh["version"],
            "range_from": 1,
            "range_to": 100,
            "template": {
                "package_type": "CARTON",
                "package_count": 1,
                "net_weight_kg": "5.40",
                "gross_weight_kg": "6.00",
                "length": "47",
                "width": "34",
                "height": "56",
                "dimension_unit": "CM",
            },
        },
    )
    assert r.status_code == 201, r.text
    sh = r.json()
    assert len(sh["packages"]) == 100
    nos = {p["external_package_no"] for p in sh["packages"]}
    assert "1" in nos and "100" in nos
    assert sh["version"] == 2  # single bump


def test_packages_batch_update(admin_client):
    c = admin_client
    sh = c.post("/api/shipments", json={}).json()
    sh = c.post(
        f"/api/shipments/{sh['id']}/packages/batch",
        json={
            "expected_version": sh["version"],
            "packages": [
                {"package_type": "CARTON", "package_count": 1, "external_package_no": "A"},
                {"package_type": "CARTON", "package_count": 1, "external_package_no": "B"},
            ],
        },
    ).json()
    ids = [p["id"] for p in sh["packages"]]
    r = c.patch(
        f"/api/shipments/{sh['id']}/packages/batch",
        json={
            "expected_version": sh["version"],
            "package_ids": ids,
            "net_weight_kg": "1.40",
            "gross_weight_kg": "1.49",
            "packaging_ncm": None,
            "description": "THUNDER batch",
        },
    )
    assert r.status_code == 200, r.text
    sh = r.json()
    assert all(p["description"] == "THUNDER batch" for p in sh["packages"])
    assert all(Decimal(p["net_weight_kg"]) == Decimal("1.4000") or Decimal(p["net_weight_kg"]) == Decimal("1.4") for p in sh["packages"])


def test_document_summary_provenance_doganale_snapshot(admin_client):
    c = admin_client
    sh = c.post("/api/shipments", json={}).json()
    doc = _upload_shipment_doc(c, sh["id"], "FatturaDoganale_202.pdf")
    r = c.put(
        f"/api/shipments/{sh['id']}/document-summaries",
        json={
            "expected_version": sh["version"],
            "document_id": doc["id"],
            "declared_net_weight_kg": "850",
            "declared_gross_weight_kg": "1000",
            "declared_pallet_count": 100,
            "declared_provenance": "FATTURA_DOGANALE",
            "raw_notes": "Snapshot documental — não SoT Customs/Logistics",
        },
    )
    assert r.status_code == 200, r.text
    sh = r.json()
    summary = sh["document_summaries"][0]
    assert summary["declared_provenance"] == "FATTURA_DOGANALE"
    assert summary["declared_pallet_count"] == 100
    assert Decimal(summary["declared_net_weight_kg"]) in (Decimal("850"), Decimal("850.0000"))

    d = c.get(f"/api/shipments/{sh['id']}/totals/divergences").json()
    assert isinstance(d, list)

    r = c.put(
        f"/api/shipments/{sh['id']}/document-summaries",
        json={
            "expected_version": sh["version"],
            "document_id": doc["id"],
            "declared_provenance": "INVALID",
        },
    )
    assert r.status_code == 400, r.text


def test_nm_contents_two_items(admin_client):
    c = admin_client
    s = c.post("/api/suppliers", json={"name": "Sup NM", "country_code": "IT"}).json()
    p1 = c.post("/api/products", json={"sku": "SKU-NM-1", "description": "A"}).json()
    p2 = c.post("/api/products", json={"sku": "SKU-NM-2", "description": "B"}).json()
    o = c.post(
        "/api/orders",
        json={"code": "ORD-NM", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={"expected_version": o["version"], "product_id": p1["id"], "quantity": "10", "unit_price": "1"},
    ).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={"expected_version": o["version"], "product_id": p2["id"], "quantity": "10", "unit_price": "1"},
    ).json()
    o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    sh = c.post("/api/shipments", json={}).json()
    for oi in o["items"]:
        sh = c.post(
            f"/api/shipments/{sh['id']}/items",
            json={"expected_version": sh["version"], "order_item_id": oi["id"], "quantity": "3"},
        ).json()
    sh = c.post(
        f"/api/shipments/{sh['id']}/packages",
        json={"expected_version": sh["version"], "package_type": "PALLET", "package_count": 1},
    ).json()
    pkg_id = sh["packages"][0]["id"]
    ids = [i["id"] for i in sh["items"]]
    r = c.put(
        f"/api/shipments/{sh['id']}/packages/{pkg_id}/contents",
        json={
            "expected_version": sh["version"],
            "contents": [
                {"shipment_item_id": ids[0], "contained_quantity": "3", "source_ncm": "4202"},
                {"shipment_item_id": ids[1], "contained_quantity": "3", "source_ncm": "4202"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["packages"][0]["contents"]) == 2
