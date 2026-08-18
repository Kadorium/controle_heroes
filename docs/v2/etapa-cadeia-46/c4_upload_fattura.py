"""Upload Fattura_328 to epic_v2_test via :8082. Operator commit stays in the UI."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8082"
PDF = Path(
    r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_328\Fattura_328.pdf"
)
OUT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\etapa-cadeia-46\c4-fattura-upload.json")


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        r = c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
        r.raise_for_status()
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
        body = doc.json()
        OUT.write_text(json.dumps({"occurrence_id": occ_id, "document": body}, indent=2, default=str), encoding="utf-8")
        print("document_id", body.get("id"), "invoice", next((f.get("normalized_value") for f in body.get("fields") or [] if f.get("field_key") == "invoice_number"), None))


if __name__ == "__main__":
    main()
