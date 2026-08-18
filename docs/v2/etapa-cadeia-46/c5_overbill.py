"""C5: overbill on issue must fail when available_qty is 0."""
from __future__ import annotations

import httpx

BASE = "http://127.0.0.1:8082"


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}).raise_for_status()
        o = c.get("/api/orders/1").json()
        inv = c.post(
            f"/api/orders/1/invoices",
            json={"invoice_number": "C46-OVERBILL", "invoice_date": "2026-08-13"},
        )
        print("create_invoice", inv.status_code, inv.text[:400])
        if inv.status_code >= 400:
            return
        body = inv.json()
        iid = body["id"]
        item = body["items"][0]
        put = c.put(
            f"/api/invoices/{iid}/items",
            json={
                "expected_version": body["version"],
                "items": [
                    {
                        "order_item_id": item["order_item_id"],
                        "quantity": "1",
                        "unit_price_gross": "106.66",
                        "discount_type": "NONE",
                    }
                ],
            },
        )
        print("put_items", put.status_code, put.text[:300])
        body = put.json()
        terms = c.put(
            f"/api/invoices/{iid}/terms",
            json={
                "expected_version": body["version"],
                "mode": "AMOUNT",
                "terms": [{"due_date": "2026-08-13", "amount": "106.66"}],
            },
        )
        print("set_terms", terms.status_code, terms.text[:300])
        body = terms.json()
        issue = c.post(
            f"/api/invoices/{iid}/issue",
            json={"expected_version": body["version"], "allow_without_document": True, "reason_code": "C5_OVERBILL"},
        )
        print("issue", issue.status_code, issue.text[:500])


if __name__ == "__main__":
    main()
