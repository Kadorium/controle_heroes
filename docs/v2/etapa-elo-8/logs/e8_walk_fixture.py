"""Pré-W1 fixture Elo 8 — epic_v2_test / :8082 only.

Leaves PARTIALLY_CLEARED + nat CONFIRMED + ARRIVED + zero receipts.
Product names from EAN_DESC. Does not POST inventory receipts.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8082"
OUT = Path(__file__).resolve().parent / "e8-walk-fixture.json"

EAN_DESC = {
    "8057628950936": "WASH BAG REBEL - PURPLE",
    "8057628953104": "WASH BAG FIERCE",
    "8057628954194": "WASH BAG SHOW - LIGHT BLUE",
    "8057628953814": "WASH BAG STARLIGHT - RED",
    "8057628955191": "THUNDER ARION",
    "8057628955207": "GRAVITY ARION",
    "8057628955214": "WASH BAG ARION",
}

# Walk SKUs: 3814 residual 50 of 200; 3104 full 10 for W5/W6.
WALK = [
    {"sku": "8057628953814", "qty": "200", "nat_qty": "50", "unit_price": "10"},
    {"sku": "8057628953104", "qty": "10", "nat_qty": "10", "unit_price": "12"},
]


def _ok(r: httpx.Response, step: str):
    if r.status_code >= 400:
        raise SystemExit(f"{step} {r.status_code}: {r.text[:800]}")
    return r.json() if r.content else {}


def main() -> None:
    today = date.today()
    due = (today + timedelta(days=30)).isoformat()
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        health = _ok(c.get("/api/health"), "health")
        if health.get("logical_database") != "epic_v2_test":
            raise SystemExit(f"REFUSADO: logical_database={health.get('logical_database')!r}")
        _ok(
            c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}),
            "login",
        )
        supplier = _ok(
            c.post("/api/suppliers", json={"name": "Heroe's Srl", "country_code": "IT"}),
            "supplier",
        )
        products = {}
        for sku, desc in EAN_DESC.items():
            p = _ok(c.post("/api/products", json={"sku": sku, "description": desc}), f"product-{sku}")
            products[sku] = p
        order = _ok(
            c.post(
                "/api/orders",
                json={
                    "code": "E8-202-MOCK",
                    "supplier_id": supplier["id"],
                    "currency": "EUR",
                    "notes": "MOCK operacional Elo 8 — continuação da família 202; pedido não veio de Ordine.",
                },
            ),
            "order",
        )
        for ln in WALK:
            order = _ok(
                c.post(
                    f"/api/orders/{order['id']}/items",
                    json={
                        "expected_version": order["version"],
                        "product_id": products[ln["sku"]]["id"],
                        "quantity": ln["qty"],
                        "unit_price": ln["unit_price"],
                    },
                ),
                f"item-{ln['sku']}",
            )
        order = _ok(
            c.post(f"/api/orders/{order['id']}/confirm", json={"expected_version": order["version"]}),
            "confirm-order",
        )
        inv = _ok(
            c.post(
                f"/api/orders/{order['id']}/invoices",
                json={"invoice_number": "202", "invoice_type": "FINAL"},
            ),
            "invoice",
        )
        inv_items = []
        for oi in order["items"]:
            inv_items.append(
                {
                    "order_item_id": oi["id"],
                    "quantity": oi["quantity"],
                    "unit_price_gross": oi["unit_price"],
                    "discount_type": "PERCENT",
                    "discount_percent": "0",
                }
            )
        inv = _ok(
            c.put(
                f"/api/invoices/{inv['id']}/items",
                json={"expected_version": inv["version"], "items": inv_items},
            ),
            "invoice-items",
        )
        inv = _ok(
            c.put(
                f"/api/invoices/{inv['id']}/terms",
                json={
                    "expected_version": inv["version"],
                    "mode": "PERCENT",
                    "terms": [{"due_date": due, "percent": "100"}],
                },
            ),
            "invoice-terms",
        )
        files = {"file": ("f.pdf", BytesIO(b"%PDF-1.4 x"), "application/pdf")}
        data = {"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"}
        doc = c.post("/api/documents", files=files, data=data)
        _ok(doc, "invoice-pdf")
        inv = _ok(
            c.post(f"/api/invoices/{inv['id']}/issue", json={"expected_version": inv["version"]}),
            "issue",
        )
        provider = _ok(
            c.post(
                "/api/logistics-providers",
                json={
                    "legal_name": "E8 Mock Transportador LTDA",
                    "provider_type": "TRANSPORTADOR",
                    "active": True,
                },
            ),
            "provider",
        )
        sh = _ok(
            c.post("/api/shipments", json={"modal": "SEA", "logistics_provider_id": provider["id"]}),
            "shipment",
        )
        for oi in order["items"]:
            sh = _ok(
                c.post(
                    f"/api/shipments/{sh['id']}/items",
                    json={
                        "expected_version": sh["version"],
                        "order_item_id": oi["id"],
                        "quantity": oi["quantity"],
                    },
                ),
                f"shp-item-{oi['id']}",
            )
        event_date = today.isoformat()
        for _ in range(3):
            sh = _ok(
                c.post(
                    f"/api/shipments/{sh['id']}/advance",
                    json={"expected_version": sh["version"], "event_date": event_date},
                ),
                "advance",
            )
        if sh["status"] != "ARRIVED":
            raise SystemExit(f"shipment status={sh['status']}")
        proc = _ok(c.post("/api/import-processes", json={"external_reference": "TEST-DUIMP-E8-202"}), "process")
        proc = _ok(
            c.post(
                f"/api/import-processes/{proc['id']}/invoices",
                json={"expected_version": proc["version"], "invoice_id": inv["id"]},
            ),
            "link-inv",
        )
        proc = _ok(
            c.post(
                f"/api/import-processes/{proc['id']}/shipments",
                json={"expected_version": proc["version"], "shipment_id": sh["id"]},
            ),
            "link-shp",
        )
        for it in inv["items"]:
            proc = _ok(
                c.post(
                    f"/api/import-processes/{proc['id']}/invoice-items/allocate",
                    json={
                        "expected_version": proc["version"],
                        "invoice_item_id": it["id"],
                        "allocated_qty": it["quantity"],
                    },
                ),
                f"alloc-inv-{it['id']}",
            )
        for it in sh["items"]:
            proc = _ok(
                c.post(
                    f"/api/import-processes/{proc['id']}/shipment-items/allocate",
                    json={
                        "expected_version": proc["version"],
                        "shipment_item_id": it["id"],
                        "allocated_qty": it["quantity"],
                    },
                ),
                f"alloc-shp-{it['id']}",
            )
        proc = _ok(
            c.post(
                f"/api/import-processes/{proc['id']}/submit",
                json={"expected_version": proc["version"]},
            ),
            "submit",
        )
        nat = _ok(
            c.post(f"/api/import-processes/{proc['id']}/nationalizations", json={}),
            "nat-create",
        )
        order_item_by_product = {oi["product_id"]: oi["id"] for oi in order["items"]}
        shp_item_by_order_item = {it["order_item_id"]: it["id"] for it in sh["items"]}
        inv_item_by_order_item = {it["order_item_id"]: it["id"] for it in inv["items"]}
        items = []
        for ln in WALK:
            pid = products[ln["sku"]]["id"]
            oi = order_item_by_product[pid]
            items.append(
                {
                    "quantity": ln["nat_qty"],
                    "product_id": pid,
                    "shipment_item_id": shp_item_by_order_item[oi],
                    "invoice_item_id": inv_item_by_order_item[oi],
                }
            )
        nat = _ok(
            c.post(
                f"/api/import-processes/{proc['id']}/nationalizations/{nat['id']}/items",
                json={"expected_version": nat["version"], "items": items},
            ),
            "nat-items",
        )
        nat = _ok(
            c.post(
                f"/api/import-processes/{proc['id']}/nationalizations/{nat['id']}/confirm",
                json={"expected_version": nat["version"]},
            ),
            "nat-confirm",
        )
        proc = _ok(c.get(f"/api/import-processes/{proc['id']}"), "process-get")
        residuals = _ok(
            c.get(f"/api/inventory/processes/{proc['id']}/receipt-residuals"),
            "residuals",
        )
        receipts = _ok(c.get(f"/api/inventory/receipts?process_id={proc['id']}"), "receipts")
        if receipts:
            raise SystemExit(f"expected zero receipts, got {receipts}")

    payload = {
        "health": health,
        "process_id": proc["id"],
        "process_status": proc["status"],
        "process_code": proc.get("code"),
        "shipment_status": sh["status"],
        "nationalization_id": nat["id"],
        "nationalization_status": nat["status"],
        "products": {sku: p["id"] for sku, p in products.items()},
        "residuals": residuals,
        "receipts": receipts,
        "walk_skus": WALK,
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
