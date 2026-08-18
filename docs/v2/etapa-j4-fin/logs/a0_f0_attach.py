"""API: attach official PDF to invoice 30 so F0 UI can issue."""
from io import BytesIO

import httpx

BASE = "http://127.0.0.1:8081"

with httpx.Client(base_url=BASE, timeout=30.0) as c:
    c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}).raise_for_status()
    r = c.post(
        "/api/documents",
        files={"file": ("fattura.pdf", BytesIO(b"%PDF-1.4 fake A0-F0"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": "30", "role": "official"},
    )
    print(r.status_code, r.text[:400])
    inv = c.get("/api/invoices/30").json()
    print("status", inv.get("status"), "blockers", inv.get("blockers"), "version", inv.get("version"))
