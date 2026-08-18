"""Seed TESTE-FIX-C3 — prova C3 (refetch custo BRL). Não toca 589 nem CICLO-001."""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import httpx

BASE = "http://127.0.0.1:8081"


def main() -> None:
    uid = uuid.uuid4().hex[:8]
    with httpx.Client(base_url=BASE, timeout=30) as c:
        r = c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
        r.raise_for_status()
        s = c.post(
            "/api/suppliers",
            json={"name": f"TESTE - FIX-C3 nao e compra real ({uid})", "country_code": "IT"},
        ).json()
        p = c.post("/api/products", json={"sku": f"FIXC3-{uid}", "description": "Item FIX-C3"}).json()
        o = c.post(
            "/api/orders",
            json={
                "code": f"TESTE-FIX-C3-{uid}",
                "supplier_id": s["id"],
                "currency": "EUR",
                "notes": "FIN-CICLO-FIX C3 refetch; nao e compra real; nao e 589",
            },
        ).json()
        o = c.post(
            f"/api/orders/{o['id']}/items",
            json={
                "expected_version": o["version"],
                "product_id": p["id"],
                "quantity": "100",
                "unit_price": "10",
            },
        ).json()
        o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
        adv = c.post(
            f"/api/orders/{o['id']}/advances",
            json={
                "amount": "1000.00",
                "payment_date": date.today().isoformat(),
                "execution_date": date.today().isoformat(),
                "rate": "5.80",
                "register_without_fx_document": True,
                "reason_code": "ORDER_ADVANCE",
            },
        ).json()
        inv = c.post(f"/api/orders/{o['id']}/invoices", json={"invoice_number": f"FIX-C3-{uid}"}).json()
        item = inv["items"][0]
        inv = c.put(
            f"/api/invoices/{inv['id']}/items",
            json={
                "expected_version": inv["version"],
                "items": [
                    {
                        "order_item_id": item["order_item_id"],
                        "quantity": "100",
                        "unit_price_gross": "10.00",
                        "discount_type": "NONE",
                    }
                ],
            },
        ).json()
        due = (date.today() + timedelta(days=20)).isoformat()
        inv = c.put(
            f"/api/invoices/{inv['id']}/terms",
            json={
                "expected_version": inv["version"],
                "mode": "AMOUNT",
                "terms": [{"due_date": due, "amount": "1000.00"}],
            },
        ).json()
        inv = c.post(
            f"/api/invoices/{inv['id']}/issue",
            json={
                "expected_version": inv["version"],
                "issue_without_document": True,
                "reason_code": "TESTE-FIX-C3",
            },
        ).json()
        pay = inv["payables"][0]
        fx = c.get(f"/api/payables/{pay['id']}/fx-view").json()
        sumy = c.get(f"/api/orders/{o['id']}/summary").json()
        out = {
            "supplier_id": s["id"],
            "product_id": p["id"],
            "order_id": o["id"],
            "order_code": o["code"],
            "advance_payment_id": adv["payment_id"],
            "invoice_id": inv["id"],
            "payable_id": pay["id"],
            "payable_balance": pay["balance"],
            "cost_brl_before": fx.get("cost_brl"),
            "fx_exposure": sumy["kpis"]["fx_exposure"],
            "advanced_credit": sumy["kpis"]["advanced_credit"],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
