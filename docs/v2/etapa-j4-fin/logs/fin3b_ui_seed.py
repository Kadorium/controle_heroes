import json
import pathlib
import sys

import requests

base = "http://127.0.0.1:8081"
s = requests.Session()
r = s.post(
    base + "/api/auth/login",
    json={"email": "admin@epic.com.br", "password": "admin123"},
)
r.raise_for_status()
sups = s.get(base + "/api/suppliers", params={"q": "Heroe", "limit": 20}).json()
heroes = next((x for x in sups if x.get("name") == "Heroe's Srl"), sups[0])
prods = s.get(base + "/api/products", params={"q": "8057628953586", "limit": 5}).json()
if isinstance(prods, dict):
    prods = prods.get("items") or prods.get("results") or []
pid = None
for p in prods:
    if p.get("sku") == "8057628953586":
        pid = p["id"]
        break
if pid is None:
    created = s.post(
        base + "/api/products",
        json={"sku": "8057628953586", "description": "RACCHETTA BT 2026 SHOW"},
    )
    created.raise_for_status()
    pid = created.json()["id"]

order = s.post(
    base + "/api/orders",
    json={"code": "FIN3B-244", "supplier_id": heroes["id"], "currency": "EUR"},
)
order.raise_for_status()
order = order.json()
item = s.post(
    f"{base}/api/orders/{order['id']}/items",
    json={
        "expected_version": order["version"],
        "product_id": pid,
        "quantity": "14600",
        "unit_price": "50.00",
        "unit": "PZ",
    },
)
item.raise_for_status()
order = item.json()
conf = s.post(
    f"{base}/api/orders/{order['id']}/confirm",
    json={"expected_version": order["version"]},
)
conf.raise_for_status()
order = conf.json()
print(
    "ORDER_ID",
    order["id"],
    "STATUS",
    order["status"],
    "SUP",
    heroes["id"],
    "PID",
    pid,
    flush=True,
)

pdf = pathlib.Path(
    r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_244\Fattura_244.pdf"
)
batch = s.post(base + "/api/ingestion/batches", json={}).json()
up = s.post(
    f"{base}/api/ingestion/batches/{batch['id']}/files",
    files=[("files", (pdf.name, pdf.read_bytes(), "application/pdf"))],
)
up.raise_for_status()
occ = up.json()["results"][0]["id"]
doc = s.post(f"{base}/api/ingestion/occurrences/{occ}/run-adapter-fattura")
doc.raise_for_status()
doc = doc.json()
print("DOC_ID", doc["id"], "BATCH", batch["id"], "OCC", occ, flush=True)
prev = s.get(
    f"{base}/api/ingestion/documents/{doc['id']}/preview-commit-fattura",
    params={"policy": "A", "order_id": order["id"]},
)
prev.raise_for_status()
prev = prev.json()
print("CAN_COMMIT", prev.get("can_commit"), flush=True)
for op in prev.get("operations") or []:
    print("OP", op.get("op_key"), op.get("description")[:160], flush=True)
pathlib.Path(__file__).with_name("fin3b_ui_seed.json").write_text(
    json.dumps(
        {
            "order_id": order["id"],
            "doc_id": doc["id"],
            "batch_id": batch["id"],
            "occ_id": occ,
            "can_commit": prev.get("can_commit"),
        },
        indent=2,
    ),
    encoding="utf-8",
)
