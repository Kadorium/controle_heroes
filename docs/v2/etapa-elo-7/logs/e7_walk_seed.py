"""Mock operational seed for Elo 7 walk — epic_v2_test / :8082 only.

Creates supplier, 7 SKUs from Fattura_202 extract, confirmed order, logistics provider.
Does NOT invent tax/document numbers. Order is labeled mock (no Ordine 202 in corpus).
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8082"
ROOT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle")
FATTURA = ROOT / "v2" / "tests" / "fixtures" / "ingestion" / "corpus_202" / "Fattura_202.pdf"
OUT = Path(__file__).resolve().parent / "e7-walk-seed.json"

EAN_DESC = {
    "8057628950936": "WASH BAG REBEL - PURPLE",
    "8057628953104": "WASH BAG FIERCE",
    "8057628954194": "WASH BAG SHOW - LIGHT BLUE",
    "8057628953814": "WASH BAG STARLIGHT - RED",
    "8057628955191": "THUNDER ARION",
    "8057628955207": "GRAVITY ARION",
    "8057628955214": "WASH BAG ARION",
}


def _ok(r: httpx.Response, step: str):
    if r.status_code >= 400:
        raise SystemExit(f"{step} {r.status_code}: {r.text[:800]}")
    return r.json() if r.content else {}


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "v2"))
    from app.ingestion.adapters.fattura_heroes_v1 import extract

    raw = extract(FATTURA.read_bytes())
    lines = [
        {
            "sku": ln.sku,
            "qty": str(ln.quantity),
            "unit_price": str(ln.unit_price),
            "unit": ln.unit or "PZ",
            "description": ln.description,
        }
        for ln in raw.lines
    ]

    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        health = _ok(c.get("/api/health"), "health")
        if health.get("logical_database") != "epic_v2_test":
            raise SystemExit(f"REFUSADO: health.logical_database={health.get('logical_database')!r}")
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
            p = _ok(
                c.post("/api/products", json={"sku": sku, "description": desc}),
                f"product-{sku}",
            )
            products[sku] = p["id"]
        order = _ok(
            c.post(
                "/api/orders",
                json={
                    "code": "E7-202-MOCK",
                    "supplier_id": supplier["id"],
                    "currency": "EUR",
                    "notes": (
                        "MOCK operacional Elo 7 — pedido não veio de Ordine 202 "
                        "(ausente no corpus). Qtys/preços alinhados à Fattura_202.pdf."
                    ),
                },
            ),
            "order",
        )
        for ln in lines:
            pid = products.get(ln["sku"])
            if pid is None:
                p = _ok(
                    c.post(
                        "/api/products",
                        json={"sku": ln["sku"], "description": ln["description"] or ln["sku"]},
                    ),
                    f"product-extra-{ln['sku']}",
                )
                pid = p["id"]
                products[ln["sku"]] = pid
            order = _ok(
                c.post(
                    f"/api/orders/{order['id']}/items",
                    json={
                        "expected_version": order["version"],
                        "product_id": pid,
                        "quantity": ln["qty"],
                        "unit_price": ln["unit_price"],
                        "unit": ln["unit"],
                    },
                ),
                f"item-{ln['sku']}",
            )
        order = _ok(
            c.post(
                f"/api/orders/{order['id']}/confirm",
                json={"expected_version": order["version"]},
            ),
            "confirm",
        )
        provider = _ok(
            c.post(
                "/api/logistics-providers",
                json={
                    "legal_name": "E7 Mock Transportador LTDA",
                    "trade_name": "Mock Carrier",
                    "provider_type": "TRANSPORTADOR",
                    "active": True,
                },
            ),
            "provider",
        )

    payload = {
        "honesty": "order_products_provider_are_mock; fattura_lines_from_pdf_extract",
        "health": health,
        "supplier_id": supplier["id"],
        "order_id": order["id"],
        "order_code": order["code"],
        "order_total": order.get("total_amount"),
        "item_count": len(order.get("items") or []),
        "provider_id": provider["id"],
        "products": products,
        "lines": lines,
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
