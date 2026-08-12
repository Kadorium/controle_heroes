"""FIN-23 UI: upload Fattura_244.pdf via API (file picker blocked in browser MCP)."""
from __future__ import annotations

import json
import pathlib
import urllib.request
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8081"
PDF = pathlib.Path(
    r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v2\tests\fixtures\ingestion\corpus_244\Fattura_244.pdf"
)
OUT = pathlib.Path(
    r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\etapa-j4-fin\logs\fin23-fattura244-adapter.json"
)


def main() -> None:
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": "admin@epic.com.br", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    login = json.loads(opener.open(req).read())
    print("login", login.get("email"))

    req = urllib.request.Request(
        BASE + "/api/ingestion/batches",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    batch = json.loads(opener.open(req).read())
    print("batch", batch["id"])

    boundary = "----EpicFin23"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="Fattura_244.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode() + PDF.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE}/api/ingestion/batches/{batch['id']}/files",
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    up = json.loads(opener.open(req).read())
    occ = up["results"][0]
    print("occ", occ["id"], occ.get("status"), occ.get("original_filename"))

    req = urllib.request.Request(
        f"{BASE}/api/ingestion/occurrences/{occ['id']}/run-adapter-fattura",
        data=b"",
        method="POST",
    )
    doc = json.loads(opener.open(req).read())
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DOC_ID", doc.get("id"), "TYPE", doc.get("document_type"), "STATUS", doc.get("status"))


if __name__ == "__main__":
    main()
