"""FIN-23 UI: remainder FX for payment 24 (file picker blocked). Rate 6.10 ≠ advance 5.9523."""
from __future__ import annotations

import json
import pathlib
import urllib.request
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8081"
OUT = pathlib.Path(
    r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\etapa-j4-fin\logs\fin23-remainder-fx.json"
)


def main() -> None:
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def post(path: str, body: dict) -> dict:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(req) as r:
            return json.loads(r.read())

    def get(path: str) -> dict:
        req = urllib.request.Request(BASE + path)
        with opener.open(req) as r:
            return json.loads(r.read())

    login = post(
        "/api/auth/login",
        {"email": "admin@epic.com.br", "password": "admin123"},
    )
    print("login", login.get("email"))

    pay = get("/api/payments/24")
    allocs = pay.get("allocations") or []
    print("allocations", json.dumps(allocs, ensure_ascii=False)[:800])
    alloc_id = allocs[0]["id"] if allocs else None
    if alloc_id is None:
        raise SystemExit("no allocation on payment 24")

    ex = post(
        "/api/payments/24/fx-executions",
        {
            "foreign_amount": "4400.00",
            "rate": "6.10",
            "execution_date": "2026-08-12",
            "register_without_document": True,
            "reason_code": "FIN23_UI_FILE_PICKER",
            "idempotency_key": "fin23-p24-fx-610",
        },
    )
    print("execution", ex)

    link = post(
        "/api/fx/execution-allocations",
        {
            "fx_execution_id": ex["id"],
            "payment_allocation_id": alloc_id,
            "foreign_amount": "4400.00",
        },
    )
    print("link", link)

    val = post("/api/fx/valuations/complete", {"payment_allocation_id": alloc_id})
    print("valuation", {k: val.get(k) for k in ("id", "realized_brl", "status") if k in val})

    p18 = get("/api/payables/18")
    fxv = get("/api/payables/18/fx-view")
    out = {
        "execution": ex,
        "link": link,
        "valuation": val,
        "payable_18": {
            "status": p18.get("status"),
            "balance": p18.get("balance"),
            "amount": p18.get("amount"),
        },
        "fx_view_keys": list(fxv.keys()) if isinstance(fxv, dict) else type(fxv).__name__,
        "fx_view": fxv,
    }
    OUT.write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
