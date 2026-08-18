"""API: amostras dedicadas A0-F5. Não toca pedidos 31/589 nem 34/TESTE-CICLO-001."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8081"
PDF = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_244\Fattura_244.pdf")
OUT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\etapa-j4-fin\logs\a0-f5-seed.json")
SKU_244 = "8057628953586"
PROTECTED = {31, 34}


def _login(c: httpx.Client) -> None:
    r = c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    r.raise_for_status()


def _ingest(c: httpx.Client) -> dict:
    batch = c.post("/api/ingestion/batches", json={}).json()
    with PDF.open("rb") as f:
        up = c.post(
            f"/api/ingestion/batches/{batch['id']}/files",
            files=[("files", (PDF.name, f, "application/pdf"))],
        )
    up.raise_for_status()
    occ_id = up.json()["results"][0]["id"]
    doc = c.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura")
    doc.raise_for_status()
    return doc.json()


def _correct_invoice_number(c: httpx.Client, doc: dict, number: str) -> dict:
    field = next(f for f in doc["fields"] if f["field_key"] == "invoice_number")
    r = c.patch(
        f"/api/ingestion/fields/{field['id']}",
        json={
            "corrected_value": number,
            "expected_version": field["version"],
            "reason": "A0-F5 amostra dedicada — evitar colisão do número 244",
        },
    )
    r.raise_for_status()
    return c.get(f"/api/ingestion/documents/{doc['id']}").json()


def _correct_row_sku(c: httpx.Client, doc: dict, sku: str, product_id: int) -> dict:
    for row in doc["rows"]:
        cells = json.loads(row["cells_json"])
        cells["sku"] = {"raw": sku, "normalized": sku, "corrected": sku}
        cells["product_id_catalog"] = {
            "raw": str(product_id),
            "normalized": str(product_id),
            "corrected": str(product_id),
        }
        r = c.patch(
            f"/api/ingestion/rows/{row['id']}",
            json={
                "cells_json": json.dumps(cells, ensure_ascii=False),
                "expected_version": row["version"],
                "reason": "A0-F5 isolar SKU da amostra (não usar 31/34)",
            },
        )
        r.raise_for_status()
        doc = c.get(f"/api/ingestion/documents/{doc['id']}").json()
    return doc


def _confirmed_order(c: httpx.Client, *, code: str, supplier_id: int, product_id: int, qty: str, price: str) -> dict:
    o = c.post(
        "/api/orders",
        json={"code": code, "supplier_id": supplier_id, "currency": "EUR"},
    )
    o.raise_for_status()
    body = o.json()
    assert body["id"] not in PROTECTED
    body = c.post(
        f"/api/orders/{body['id']}/items",
        json={
            "expected_version": body["version"],
            "product_id": product_id,
            "quantity": qty,
            "unit_price": price,
            "unit": "PZ",
        },
    ).json()
    body = c.post(
        f"/api/orders/{body['id']}/confirm",
        json={"expected_version": body["version"]},
    ).json()
    return body


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=90.0) as c:
        _login(c)
        for oid in PROTECTED:
            r = c.get(f"/api/orders/{oid}")
            r.raise_for_status()
            o = r.json()
            print(f"protected {oid} {o['code']} {o['status']} invoices={len(o.get('invoices') or [])}")

        heroes = c.get("/api/suppliers", params={"q": "Heroe", "limit": 5}).json()
        supplier_id = next(s["id"] for s in heroes if "hero" in (s.get("name") or "").lower())

        p_one = c.post(
            "/api/products",
            json={"sku": "A0-F5-ONE-8057", "description": "A0 F5 caso 1 isolado"},
        )
        if p_one.status_code == 201:
            prod_one = p_one.json()["id"]
        else:
            existing = c.get("/api/products", params={"q": "A0-F5-ONE-8057"}).json()
            prod_one = existing[0]["id"]

        p244 = c.get("/api/products", params={"q": SKU_244, "limit": 5}).json()
        prod_244 = next(p["id"] for p in p244 if p.get("sku") == SKU_244)

        order_one = _confirmed_order(
            c, code="A0-F5-ONE", supplier_id=supplier_id, product_id=prod_one, qty="1000", price="99.83"
        )
        order_n1 = _confirmed_order(
            c, code="A0-F5-N1", supplier_id=supplier_id, product_id=prod_244, qty="2000", price="99.83"
        )
        order_n2 = _confirmed_order(
            c, code="A0-F5-N2", supplier_id=supplier_id, product_id=prod_244, qty="2000", price="99.83"
        )

        o_amb = c.post(
            "/api/orders",
            json={"code": "A0-F5-AMB", "supplier_id": supplier_id, "currency": "EUR"},
        ).json()
        o_amb = c.post(
            f"/api/orders/{o_amb['id']}/items",
            json={
                "expected_version": o_amb["version"],
                "product_id": prod_244,
                "quantity": "1000",
                "unit_price": "50.00",
                "unit": "PZ",
            },
        ).json()
        o_amb = c.post(
            f"/api/orders/{o_amb['id']}/items",
            json={
                "expected_version": o_amb["version"],
                "product_id": prod_244,
                "quantity": "1000",
                "unit_price": "55.00",
                "unit": "PZ",
            },
        ).json()
        o_amb = c.post(
            f"/api/orders/{o_amb['id']}/confirm",
            json={"expected_version": o_amb["version"]},
        ).json()
        assert o_amb["id"] not in PROTECTED

        doc1 = _ingest(c)
        doc1 = _correct_invoice_number(c, doc1, "A0-F5-C1")
        doc1 = _correct_row_sku(c, doc1, "A0-F5-ONE-8057", prod_one)

        doc2 = _ingest(c)
        doc2 = _correct_invoice_number(c, doc2, "A0-F5-C2")

        doc3 = _ingest(c)
        doc3 = _correct_invoice_number(c, doc3, "A0-F5-C3")

        payload = {
            "protected": {
                "31": c.get("/api/orders/31").json()["code"],
                "34": c.get("/api/orders/34").json()["code"],
            },
            "supplier_id": supplier_id,
            "case1": {"order_id": order_one["id"], "doc_id": doc1["id"], "sku": "A0-F5-ONE-8057"},
            "case2": {
                "order_ids": [order_n1["id"], order_n2["id"]],
                "doc_id": doc2["id"],
            },
            "case3": {"order_id": o_amb["id"], "doc_id": doc3["id"], "item_ids": [it["id"] for it in o_amb["items"]]},
        }
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
