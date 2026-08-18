"""API: prova F5 — Invoice ISSUED cria Payables e não cria Payment."""
from __future__ import annotations

import json

import httpx

c = httpx.Client(base_url="http://127.0.0.1:8081", timeout=30)
c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}).raise_for_status()

inv = c.get("/api/invoices/31").json()
pays = inv.get("payables") or []
payments = c.get("/api/payments").json()
pay_ids = {p["id"] for p in pays}
alloc_hits = []
for pay in payments:
    for a in pay.get("allocations") or []:
        if a.get("payable_id") in pay_ids:
            alloc_hits.append(
                {
                    "payment_id": pay.get("id"),
                    "purpose": pay.get("purpose"),
                    "payable_id": a.get("payable_id"),
                    "amount": a.get("amount"),
                }
            )

print(
    json.dumps(
        {
            "invoice_status": inv.get("status"),
            "order_id": inv.get("order_id"),
            "payables": [
                {"id": p.get("id"), "amount": p.get("amount"), "balance": p.get("balance"), "status": p.get("status")}
                for p in pays
            ],
            "payments_n": len(payments),
            "allocations_on_new_payables": alloc_hits,
            "order_31": c.get("/api/orders/31").json().get("code"),
            "order_34": c.get("/api/orders/34").json().get("code"),
        },
        ensure_ascii=False,
        indent=2,
    )
)
