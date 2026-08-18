"""API: upload Fattura_244 and run adapter (F0 path A)."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8081"
PDF = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_244\Fattura_244.pdf")
OUT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\etapa-j4-fin\logs\a0-f0-seed.json")


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
        payload = {
            "pathB": 37,
            "pathA": 38,
            "batch": batch["id"],
            "occ": occ_id,
            "doc": body["id"],
            "doc_type": body.get("doc_type"),
            "review_status": body.get("review_status"),
        }
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
