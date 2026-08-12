"""Upload Ordine_589.pdf into epic_v2 via API (dryrun AUTO_LIMIT for browser file input)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8081"
PDF = (
    Path(__file__).resolve().parents[4]
    / "v2"
    / "tests"
    / "fixtures"
    / "ingestion"
    / "corpus_589"
    / "Ordine_589.pdf"
)


def main() -> int:
    if not PDF.is_file():
        print("MISSING", PDF)
        return 2
    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        r = client.post(
            "/api/auth/login",
            json={"email": "admin@epic.com.br", "password": "admin123"},
        )
        r.raise_for_status()
        batch = client.post("/api/ingestion/batches", json={}).json()
        bid = batch["id"]
        with PDF.open("rb") as f:
            up = client.post(
                f"/api/ingestion/batches/{bid}/files",
                files=[("files", (PDF.name, f, "application/pdf"))],
            )
        up.raise_for_status()
        body = up.json()
        occ_id = body["results"][0]["id"]
        print(json.dumps({"batch_id": bid, "occurrence_id": occ_id, "upload": body}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
