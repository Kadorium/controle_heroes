"""Seed throwaway Ordine on epic_v2 for WARNING screenshot — does NOT touch Order 31/589."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[4]
load_dotenv(root / "v2" / ".env")

BASE = os.environ.get("EPIC_UI_BASE", "http://127.0.0.1:8081")
PDF = root / "v2" / "tests" / "fixtures" / "ingestion" / "corpus_589" / "Ordine_589.pdf"

with httpx.Client(base_url=BASE, timeout=60.0) as c:
    login = c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"})
    login.raise_for_status()
    print("login_keys", list(login.json().keys())[:12], "cookies", list(c.cookies.keys()))

    batch = c.post("/api/ingestion/batches", json={}).json()
    with open(PDF, "rb") as f:
        up = c.post(
            f"/api/ingestion/batches/{batch['id']}/files",
            files=[("files", (PDF.name, f, "application/pdf"))],
        )
    up.raise_for_status()
    occ_id = up.json()["results"][0]["id"]
    doc = c.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter").json()
    doc_id = doc["id"]
    detail = c.get(f"/api/ingestion/documents/{doc_id}").json()
    row = detail["rows"][0]
    cells = json.loads(row["cells_json"])
    cells["quantity"] = {
        "raw": cells["quantity"].get("raw"),
        "normalized": "99999",
    }
    patch = c.patch(
        f"/api/ingestion/rows/{row['id']}",
        json={
            "cells_json": json.dumps(cells, ensure_ascii=False),
            "expected_version": row["version"],
            "reason": "rux3f-post3-screenshot",
        },
    )
    print("patch_status", patch.status_code, patch.text[:200])
    patch.raise_for_status()
    after = c.get(f"/api/ingestion/documents/{doc_id}").json()
    warns = [
        i
        for i in after.get("issues") or []
        if i.get("status") == "OPEN" and i.get("code") == "MATH_LINE_EDIT_DIVERGENCE"
    ]
    print(
        json.dumps(
            {
                "doc_id": doc_id,
                "warn_count": len(warns),
                "message": warns[0]["message"] if warns else None,
                "issue_codes": [(i.get("code"), i.get("severity"), i.get("status")) for i in after.get("issues") or []],
            },
            ensure_ascii=False,
        )
    )
