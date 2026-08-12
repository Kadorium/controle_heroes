import json
import requests

base = "http://127.0.0.1:8081"
s = requests.Session()
s.post(base + "/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}).raise_for_status()
inv = s.get(base + "/api/invoices/24").json()
items = inv.get("items") or []
print("STATUS", inv.get("status"), "NUMBER", inv.get("invoice_number"), "NET", inv.get("total_net"))
print("NOTES", (inv.get("notes") or "")[:500])
for it in items:
    print(
        "ITEM",
        it.get("id"),
        "oi",
        it.get("order_item_id"),
        "sku",
        it.get("sku_snapshot") or it.get("sku"),
        "qty",
        it.get("quantity"),
        "price",
        it.get("unit_price"),
        "net",
        it.get("line_net") or it.get("net_amount"),
    )
path = __file__.replace("fin3b_ui_invoice.py", "fin3b_ui_invoice.json")
open(path, "w", encoding="utf-8").write(json.dumps({"status": inv.get("status"), "items": items, "notes": inv.get("notes")}, default=str, indent=2))
