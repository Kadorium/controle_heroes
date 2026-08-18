"""Prep aceite 1→5 on :8082 (epic_v2_test). Leaves packing IR uncommitted for UI C6."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8082"
ROOT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion")
FATTURA = ROOT / "corpus_328" / "Fattura_328.pdf"
PACKING = ROOT / "corpus_328" / "PackingList_328.pdf"
OUT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\etapa-cadeia-46\aceite16-prep.json")


def _ok(r: httpx.Response, step: str):
    if r.status_code >= 400:
        raise SystemExit(f"{step} {r.status_code}: {r.text[:800]}")
    return r.json() if r.content else {}


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=90.0) as c:
        _ok(c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}), "login")

        supplier = _ok(
            c.post("/api/suppliers", json={"name": "Heroe's Srl", "country_code": "IT"}),
            "supplier",
        )
        product = _ok(
            c.post(
                "/api/products",
                json={"sku": "8057628953593", "description": "RACCHETTA BT 2026 STARLIGHT"},
            ),
            "product",
        )
        order = _ok(
            c.post(
                "/api/orders",
                json={
                    "code": "C46-328",
                    "supplier_id": supplier["id"],
                    "currency": "EUR",
                    "notes": "Mock aceite 1→6 — pedido não veio de Ordine 328 (ausente no corpus).",
                },
            ),
            "order",
        )
        order = _ok(
            c.post(
                f"/api/orders/{order['id']}/items",
                json={
                    "expected_version": order["version"],
                    "product_id": product["id"],
                    "quantity": "50",
                    "unit_price": "106.66",
                    "unit": "PZ",
                },
            ),
            "item",
        )
        order = _ok(
            c.post(
                f"/api/orders/{order['id']}/confirm",
                json={"expected_version": order["version"]},
            ),
            "confirm",
        )

        adv = _ok(
            c.post(
                f"/api/orders/{order['id']}/advances",
                json={
                    "amount": "1250.00",
                    "payment_date": "2026-05-18",
                    "execution_date": "2026-05-18",
                    "rate": "5.9759",
                    "currency": "EUR",
                    "register_without_fx_document": True,
                    "reason_code": "ACEITE16_ADVANCE",
                    "idempotency_key": "aceite16-adv-328",
                },
            ),
            "advance",
        )

        batch = _ok(c.post("/api/ingestion/batches", json={"notes": "aceite16-fattura"}), "batch-fat")
        with FATTURA.open("rb") as f:
            up = _ok(
                c.post(
                    f"/api/ingestion/batches/{batch['id']}/files",
                    files=[("files", (FATTURA.name, f, "application/pdf"))],
                ),
                "upload-fat",
            )
        occ_id = up["results"][0]["id"]
        fat_doc = _ok(c.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura"), "adapter-fat")
        fat_commit = _ok(
            c.post(
                f"/api/ingestion/documents/{fat_doc['id']}/commit-fattura",
                json={
                    "operation_key": "aceite16-fattura-328",
                    "policy": "A",
                    "order_id": order["id"],
                },
            ),
            "commit-fat",
        )
        inv_id = None
        for op in fat_commit.get("operations") or []:
            if op.get("entity_type") == "invoice" and op.get("entity_id"):
                inv_id = int(op["entity_id"])
        if inv_id is None:
            invoices = _ok(c.get("/api/invoices", params={"order_id": order["id"]}), "list-inv")
            inv_id = invoices[0]["id"]
        inv = _ok(c.get(f"/api/invoices/{inv_id}"), "get-inv")
        issued = _ok(
            c.post(
                f"/api/invoices/{inv_id}/issue",
                json={"expected_version": inv["version"]},
            ),
            "issue",
        )
        payables = _ok(c.get("/api/payables", params={"invoice_id": inv_id}), "payables")
        payables = sorted(payables, key=lambda p: p["id"])
        payment_id = adv["payment_id"]
        pay_get = _ok(c.get(f"/api/payments/{payment_id}"), "get-adv-pay")
        first = payables[0]
        _ok(
            c.post(
                f"/api/payments/{payment_id}/allocations",
                json={
                    "expected_version": pay_get["version"],
                    "idempotency_key": "aceite16-alloc-adv",
                    "allocations": [
                        {
                            "payable_id": first["id"],
                            "amount": first["amount"],
                            "expected_version": first["version"],
                        }
                    ],
                },
            ),
            "alloc-adv",
        )
        rest = payables[1]
        settle = _ok(
            c.post(
                "/api/payments",
                json={
                    "supplier_id": supplier["id"],
                    "amount": rest["amount"],
                    "currency": "EUR",
                    "payment_date": str(date.today()),
                    "order_id": order["id"],
                    "register_without_document": True,
                    "reason_code": "ACEITE16_SETTLEMENT",
                    "idempotency_key": "aceite16-settle-328",
                },
            ),
            "settlement",
        )
        rest = _ok(c.get(f"/api/payables/{rest['id']}"), "reload-rest")
        _ok(
            c.post(
                f"/api/payments/{settle['id']}/allocations",
                json={
                    "expected_version": settle["version"],
                    "idempotency_key": "aceite16-alloc-settle",
                    "allocations": [
                        {
                            "payable_id": rest["id"],
                            "amount": rest["amount"],
                            "expected_version": rest["version"],
                        }
                    ],
                },
            ),
            "alloc-settle",
        )

        batch2 = _ok(c.post("/api/ingestion/batches", json={"notes": "aceite16-packing"}), "batch-pl")
        with PACKING.open("rb") as f:
            up2 = _ok(
                c.post(
                    f"/api/ingestion/batches/{batch2['id']}/files",
                    files=[("files", (PACKING.name, f, "application/pdf"))],
                ),
                "upload-pl",
            )
        pl_occ = up2["results"][0]["id"]
        pl_doc = _ok(
            c.post(
                f"/api/ingestion/occurrences/{pl_occ}/run-adapter",
                json={"adapter_id": "packing_list_detail_v1"},
            ),
            "adapter-pl",
        )

        payload = {
            "order_id": order["id"],
            "order_code": order["code"],
            "supplier_id": supplier["id"],
            "product_id": product["id"],
            "invoice_id": inv_id,
            "invoice_status": issued.get("status"),
            "advance_payment_id": payment_id,
            "settlement_payment_id": settle["id"],
            "fattura_ir": fat_doc["id"],
            "packing_ir": pl_doc["id"],
            "packing_rows": len(pl_doc.get("rows") or []),
            "payables": [{"id": p["id"], "amount": p["amount"]} for p in payables],
        }
        OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
