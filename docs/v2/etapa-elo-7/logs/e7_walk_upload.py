"""Upload + adapter the five 202 PDFs into epic_v2_test. Commits happen in the UI."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8082"
ROOT = Path(r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_202")
OUT = Path(__file__).resolve().parent / "e7-walk-upload.json"

FILES = [
    ("Fattura_202.pdf", "fattura_heroes_v1"),
    ("PackingList_202.pdf", "packing_list_detail_v1"),
    ("FatturaDoganale_202.pdf", "fattura_doganale_v1"),
    ("PrintDeclaration_202.pdf", "print_declaration_v1"),
    ("Solicitacao_Numerario.pdf", "solicitacao_numerario_v1"),
]


def _ok(r: httpx.Response, step: str):
    if r.status_code >= 400:
        raise SystemExit(f"{step} {r.status_code}: {r.text[:800]}")
    return r.json() if r.content else {}


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=120.0) as c:
        health = _ok(c.get("/api/health"), "health")
        if health.get("logical_database") != "epic_v2_test":
            raise SystemExit(f"REFUSADO db={health.get('logical_database')!r}")
        _ok(
            c.post("/api/auth/login", json={"email": "admin@epic.com.br", "password": "admin123"}),
            "login",
        )
        docs = {}
        for name, adapter in FILES:
            path = ROOT / name
            batch = _ok(c.post("/api/ingestion/batches", json={"notes": f"e7-walk-{name}"}), f"batch-{name}")
            with path.open("rb") as f:
                up = _ok(
                    c.post(
                        f"/api/ingestion/batches/{batch['id']}/files",
                        files=[("files", (name, f, "application/pdf"))],
                    ),
                    f"upload-{name}",
                )
            occ_id = up["results"][0]["id"]
            if adapter == "fattura_heroes_v1":
                doc = _ok(c.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter-fattura"), f"adapter-{name}")
            else:
                doc = _ok(
                    c.post(
                        f"/api/ingestion/occurrences/{occ_id}/run-adapter",
                        json={"adapter_id": adapter},
                    ),
                    f"adapter-{name}",
                )
            docs[name] = {
                "document_id": doc["id"],
                "adapter": adapter,
                "doc_type": doc.get("doc_type"),
                "row_count": len(doc.get("rows") or []),
                "workspace": f"http://127.0.0.1:5174/ingestion/{doc['id']}",
            }
    OUT.write_text(json.dumps({"health": health, "docs": docs}, indent=2), encoding="utf-8")
    print(json.dumps({"docs": docs}, indent=2))


if __name__ == "__main__":
    main()
