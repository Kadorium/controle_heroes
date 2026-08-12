"""Re-ingest Ordine_589 via existing intake (gate RUX-2R-a)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8081"
PDF = Path(__file__).resolve().parents[3] / "tests/fixtures/ingestion/corpus_589/Ordine_589.pdf"
# script lives in docs/v2/etapa-j3/logs → parents[3] is v2
PDF = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_589\Ordine_589.pdf")


def main() -> int:
    if not PDF.is_file():
        print("PDF missing", PDF)
        return 1
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        r = c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
        r.raise_for_status()
        r = c.post("/api/ingestion/batches", json={})
        r.raise_for_status()
        batch_id = r.json()["id"]
        files = {"files": (PDF.name, PDF.read_bytes(), "application/pdf")}
        r = c.post(f"/api/ingestion/batches/{batch_id}/files", files=files)
        r.raise_for_status()
        occ = r.json()["results"][0]
        occ_id = occ["id"]
        print("occurrence", occ_id, occ.get("status"))
        r = c.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
        r.raise_for_status()
        doc = r.json()
        doc_id = doc["id"]
        print("document", doc_id, doc["doc_type"], "issues", len(doc.get("issues") or []))
        codes = [i["code"] for i in doc.get("issues") or [] if i.get("status") == "OPEN"]
        print("open_codes", codes)
        for row in doc.get("rows") or []:
            cells = json.loads(row["cells_json"])
            d = cells.get("description") or {}
            print("DESC raw:", (d.get("raw") or "")[:80])
            print("DESC norm:", (d.get("normalized") or "")[:80])
        supplier = next((f for f in doc.get("fields") or [] if f["field_key"] == "supplier_name"), None)
        print("supplier", supplier and (supplier.get("effective_value") or supplier.get("raw_value")))
        print("DOC_ID", doc_id)
        return 0


if __name__ == "__main__":
    sys.exit(main())
