"""Continue TESTE-CICLO-001 walk: apply remaining T-001 credit, T-002, 244, T-003, remainders."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8081"
PDF_244 = (
    Path(__file__).resolve().parents[4]
    / "v2"
    / "tests"
    / "fixtures"
    / "ingestion"
    / "corpus_244"
    / "Fattura_244.pdf"
)
OUT = Path(__file__).with_name("ciclo-walk-continue.json")


def uid() -> str:
    return uuid.uuid4().hex[:8]


def main() -> None:
    log: dict = {}
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        r = c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
        r.raise_for_status()

        def post(url, **kw):
            resp = c.post(url, **kw)
            if resp.status_code >= 400:
                raise RuntimeError(f"POST {url} {resp.status_code} {resp.text}")
            return resp.json() if resp.content else {}

        def put(url, **kw):
            resp = c.put(url, **kw)
            if resp.status_code >= 400:
                raise RuntimeError(f"PUT {url} {resp.status_code} {resp.text}")
            return resp.json()

        def get(url, **kw):
            resp = c.get(url, **kw)
            if resp.status_code >= 400:
                raise RuntimeError(f"GET {url} {resp.status_code} {resp.text}")
            return resp.json()

        # --- apply remaining 84k of advance 25 to payable 23 ---
        pay25 = get("/api/payments/25")
        p23 = get("/api/payables/23")
        pay25 = post(
            "/api/payments/25/allocations",
            json={
                "expected_version": pay25["version"],
                "idempotency_key": f"ciclo-t001-84k-{uid()}",
                "allocations": [
                    {
                        "payable_id": 23,
                        "amount": "84000.00",
                        "expected_version": p23["version"],
                    }
                ],
            },
        )
        v23 = get("/api/payables/23/fx-view")
        log["t001_p23"] = {
            "status": get("/api/payables/23")["status"],
            "cost_brl": v23["cost_brl"],
            "unalloc_25": pay25["amount_unallocated"],
        }

        order = get("/api/orders/34")
        item_id = order["items"][0]["id"]

        def issue_manual(number: str, qty: str, price: str, terms: list[dict]) -> dict:
            inv = post(f"/api/orders/34/invoices", json={"invoice_number": number})
            inv = put(
                f"/api/invoices/{inv['id']}/items",
                json={
                    "expected_version": inv["version"],
                    "items": [
                        {
                            "order_item_id": item_id,
                            "quantity": qty,
                            "unit_price_gross": price,
                            "discount_type": "NONE",
                        }
                    ],
                },
            )
            inv = put(
                f"/api/invoices/{inv['id']}/terms",
                json={"expected_version": inv["version"], "mode": "AMOUNT", "terms": terms},
            )
            inv = post(
                f"/api/invoices/{inv['id']}/issue",
                json={
                    "expected_version": inv["version"],
                    "issue_without_document": True,
                    "reason_code": "TESTE-CICLO-001",
                },
            )
            return inv

        inv2 = issue_manual(
            "T-002",
            "3000",
            "60.00",
            [
                {"due_date": "2026-05-15", "amount": "90000.00"},
                {"due_date": "2026-07-15", "amount": "90000.00"},
            ],
        )
        pays2 = sorted(inv2["payables"], key=lambda p: p["due_date"])
        p90a, p90b = pays2[0], pays2[1]
        log["t002"] = {
            "invoice_id": inv2["id"],
            "net": inv2["net_amount"],
            "p90a": p90a["id"],
            "p90b": p90b["id"],
        }

        # apply remaining 60k @ 6.15 to first 90k
        pay26 = get("/api/payments/26")
        p90a = get(f"/api/payables/{p90a['id']}")
        post(
            "/api/payments/26/allocations",
            json={
                "expected_version": pay26["version"],
                "idempotency_key": f"ciclo-t002-60k-{uid()}",
                "allocations": [
                    {
                        "payable_id": p90a["id"],
                        "amount": "60000.00",
                        "expected_version": p90a["version"],
                    }
                ],
            },
        )
        log["t002_credit"] = {
            "p90a_status": get(f"/api/payables/{p90a['id']}")["status"],
            "p90a_balance": get(f"/api/payables/{p90a['id']}")["balance"],
            "p90a_cost": get(f"/api/payables/{p90a['id']}/fx-view")["cost_brl"],
        }

        def pay_remainder(payable_id: int, amount: str, rate: str, exec_date: str, pay_date: str) -> dict:
            p = get(f"/api/payables/{payable_id}")
            rem = post(
                "/api/payments",
                json={
                    "supplier_id": 27,
                    "order_id": 34,
                    "amount": amount,
                    "currency": "EUR",
                    "payment_date": pay_date,
                    "register_without_document": True,
                    "reason_code": "TESTE-CICLO-REM",
                },
            )
            post(
                f"/api/payments/{rem['id']}/fx-executions",
                json={
                    "foreign_amount": amount,
                    "rate": rate,
                    "execution_date": exec_date,
                    "register_without_document": True,
                    "reason_code": "FX_NO_DOC",
                },
            )
            rem = get(f"/api/payments/{rem['id']}")
            rem = post(
                f"/api/payments/{rem['id']}/allocations",
                json={
                    "expected_version": rem["version"],
                    "idempotency_key": f"ciclo-rem-{payable_id}-{uid()}",
                    "allocations": [
                        {
                            "payable_id": payable_id,
                            "amount": amount,
                            "expected_version": p["version"],
                        }
                    ],
                },
            )
            view = get(f"/api/payables/{payable_id}/fx-view")
            st = get(f"/api/payables/{payable_id}")
            return {
                "payment_id": rem["id"],
                "status": st["status"],
                "balance": st["balance"],
                "cost_brl": view["cost_brl"],
            }

        log["t002_rem_30k"] = pay_remainder(p90a["id"], "30000.00", "6.20", "2026-05-14", "2026-05-15")
        log["t002_rem_90k"] = pay_remainder(p90b["id"], "90000.00", "5.95", "2026-07-14", "2026-07-15")

        # --- Fattura 244 ---
        batch = post("/api/ingestion/batches", json={})
        with open(PDF_244, "rb") as f:
            up = c.post(
                f"/api/ingestion/batches/{batch['id']}/files",
                files=[("files", (PDF_244.name, f, "application/pdf"))],
            )
        if up.status_code >= 400:
            raise RuntimeError(up.text)
        occ_id = up.json()["results"][0]["id"]
        ir = post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura")
        doc_id = ir["id"]
        preview = get(
            f"/api/ingestion/documents/{doc_id}/preview-commit-fattura",
            params={"policy": "A", "order_id": 34},
        )
        log["fattura244_preview"] = {
            "doc_id": doc_id,
            "can_commit": preview.get("can_commit"),
            "blocked": preview.get("blocked"),
            "warnings": preview.get("warnings"),
        }
        commit = post(
            f"/api/ingestion/documents/{doc_id}/commit-fattura",
            json={"operation_key": f"ciclo-244-{uid()}", "policy": "A", "order_id": 34},
        )
        log["fattura244_commit"] = {
            "status": commit.get("status"),
            "ops": [
                {
                    "op_key": o.get("op_key"),
                    "status": o.get("status"),
                    "entity_id": o.get("entity_id"),
                }
                for o in (commit.get("operations") or [])
            ],
        }
        inv244_id = None
        for o in commit.get("operations") or []:
            if o.get("op_key") == "create_invoice" and o.get("entity_id"):
                inv244_id = int(o["entity_id"])
                break
        if inv244_id is None:
            invoices = get("/api/orders/34/invoices")
            rows = invoices if isinstance(invoices, list) else invoices.get("items", [])
            for inv in rows:
                if str(inv.get("invoice_number")) == "244":
                    inv244_id = inv["id"]
        if inv244_id:
            inv244 = get(f"/api/invoices/{inv244_id}")
            if inv244["status"] == "DRAFT":
                inv244 = post(
                    f"/api/invoices/{inv244_id}/issue",
                    json={"expected_version": inv244["version"]},
                )
            log["fattura244_invoice"] = {
                "id": inv244["id"],
                "status": inv244["status"],
                "net": inv244.get("net_amount"),
                "payables": [
                    {"id": p["id"], "amount": p["amount"], "due": p["due_date"]}
                    for p in inv244.get("payables") or []
                ],
            }
            for p in inv244.get("payables") or []:
                amt = f"{float(p['amount']):.2f}"
                log[f"fattura244_pay_{p['id']}"] = pay_remainder(
                    p["id"], amt, "6.40", "2026-04-19", "2026-04-20"
                )

        inv3 = issue_manual(
            "T-003",
            "4800",
            "62.50",
            [{"due_date": "2026-08-01", "amount": "300000.00"}],
        )
        p3 = inv3["payables"][0]
        log["t003"] = {
            "invoice_id": inv3["id"],
            "net": inv3["net_amount"],
            "payable_id": p3["id"],
        }
        log["t003_rem"] = pay_remainder(p3["id"], "300000.00", "6.40", "2026-07-31", "2026-08-01")

        summary = get("/api/orders/34/summary")
        log["cockpit"] = {
            "kpis": summary.get("kpis"),
            "fx": summary.get("fx"),
            "treasury_cost": summary.get("treasury", {}).get("cost_brl"),
            "invoiced": summary.get("kpis", {}).get("invoiced"),
        }
        qty = get("/api/orders/34/invoiced-quantities")
        log["qty"] = qty
        o31 = get("/api/orders/31")
        log["order_589"] = {
            "id": o31["id"],
            "code": o31["code"],
            "status": o31["status"],
            "items": [
                {"kind": i.get("line_kind"), "qty": i.get("quantity")} for i in o31.get("items") or []
            ],
        }
        s31 = get("/api/orders/31/summary")
        log["order_589_kpis"] = s31.get("kpis")

    OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(log, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
