"""J3-P0-a disposable forensic inventory — not a production dependency.

Environment: v2/.venv Python + pypdf + system poppler pdftotext (optional).
Does NOT import v1 application code. Does NOT add production requirements.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import IndirectObject

ROOT = Path(__file__).resolve().parents[4]  # repo root
FIX = ROOT / "v2" / "tests" / "fixtures" / "ingestion"
OUT = Path(__file__).resolve().parent
PDFTOTEXT = Path(r"C:\Users\ricar\poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin\pdftotext.exe")


def resolve(obj):
    while isinstance(obj, IndirectObject):
        obj = obj.get_object()
    return obj


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mime_magic(path: Path) -> str:
    head = path.read_bytes()[:8]
    if head.startswith(b"%PDF"):
        return "application/pdf"
    if head[:2] == b"PK":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream"


def list_annots(page) -> list[dict]:
    annots = resolve(page.get("/Annots")) or []
    out = []
    for a in annots:
        a = resolve(a)
        rect = a.get("/Rect")
        rect_f = [float(x) for x in rect] if rect is not None else None
        contents = a.get("/Contents")
        if contents is not None and not isinstance(contents, str):
            try:
                contents = str(contents)
            except Exception:
                contents = repr(contents)
        out.append(
            {
                "subtype": str(a.get("/Subtype")),
                "rect": rect_f,
                "name": str(a.get("/T")) if a.get("/T") is not None else None,
                "contents": contents,
                "ft": str(a.get("/FT")) if a.get("/FT") is not None else None,
            }
        )
    return out


def content_hits_origin(page) -> list[dict]:
    hits = []

    def visitor(text, cm, tm, font_dict, font_size):
        if not text:
            return
        low = text.lower()
        if any(k in low for k in ("italy", "china", "origin", "acquisition", "country")):
            hits.append(
                {
                    "text": text,
                    "x": float(tm[4]),
                    "y": float(tm[5]),
                    "size": float(font_size) if font_size else None,
                }
            )

    page.extract_text(visitor_text=visitor)
    return hits


def digital_text_stats(page) -> dict:
    text = page.extract_text() or ""
    return {
        "chars": len(text),
        "non_ws": len(re.sub(r"\s+", "", text)),
        "has_italy": "Italy" in text or "italy" in text.lower(),
        "has_china_in_content_extract": "china" in text.lower(),
        "sample_lines": [ln for ln in text.splitlines() if any(k in ln.lower() for k in ("origin", "china", "italy", "country", "units per", "amount", "ncm"))][:30],
    }


def pdftotext_layout(path: Path, first: int | None = None, last: int | None = None) -> str | None:
    if not PDFTOTEXT.exists():
        return None
    cmd = [str(PDFTOTEXT), "-layout"]
    if first is not None:
        cmd += ["-f", str(first), "-l", str(last or first)]
    cmd += [str(path), "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        return r.stdout
    except Exception as e:
        return f"ERROR: {e}"


def analyze_pdf(path: Path) -> dict:
    reader = PdfReader(str(path))
    pages_out = []
    all_freetext = []
    for i, page in enumerate(reader.pages):
        annots = list_annots(page)
        for a in annots:
            if a["subtype"] == "/FreeText":
                all_freetext.append({"page": i + 1, **a})
        pages_out.append(
            {
                "page": i + 1,
                "annots": annots,
                "content_origin_hits": content_hits_origin(page),
                "text_stats": digital_text_stats(page),
                "acroform_on_reader": bool(reader.get_fields()),
            }
        )
    layout = pdftotext_layout(path)
    origin_lines = []
    if layout:
        for ln in layout.splitlines():
            if any(k in ln.lower() for k in ("origin", "china", "italy", "country of")):
                origin_lines.append(ln.rstrip())
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "mime": mime_magic(path),
        "pdf_pages": len(reader.pages),
        "acroform_fields": list((reader.get_fields() or {}).keys()),
        "pages": pages_out,
        "freetext_annotations": all_freetext,
        "pdftotext_origin_lines": origin_lines[:40],
    }


def extract_grouped_tables_heuristic(path: Path) -> dict:
    """Heuristic line parse via pdftotext -layout for PL Grouped semantics."""
    layout = pdftotext_layout(path) or ""
    lines = layout.splitlines()
    # Capture rows that look like data under Units/NCM/Description/Amount
    data_rows = []
    for ln in lines:
        if re.search(r"\d", ln) and ("4202" in ln or "4819" in ln or "9506" in ln or "ARION" in ln or "Imball" in ln or "Box" in ln or "imballo" in ln.lower() or "WASH" in ln or "GRAVITY" in ln or "racchetta" in ln.lower() or "STARLIGHT" in ln):
            data_rows.append(ln.rstrip())
    return {"layout_rows_candidate": data_rows, "full_layout": layout}


def main() -> None:
    pdfs = sorted(FIX.rglob("*.pdf"))
    inventory = []
    for p in pdfs:
        print("analyzing", p.name)
        inventory.append(analyze_pdf(p))

    origin_focus = []
    for item in inventory:
        name = Path(item["path"]).name
        if any(k in name for k in ("Doganale_202", "Grouped_202", "PackingList_202", "Doganale_328", "Grouped_328", "PackingList_328")):
            origin_focus.append(
                {
                    "file": name,
                    "freetext": item["freetext_annotations"],
                    "content_hits_by_page": [
                        {"page": pg["page"], "hits": pg["content_origin_hits"]} for pg in item["pages"]
                    ],
                    "pdftotext_origin_lines": item["pdftotext_origin_lines"],
                    "digital_chars_page1": item["pages"][0]["text_stats"]["chars"] if item["pages"] else 0,
                }
            )

    grouped = {}
    for name in ("PackingListGrouped_202.pdf", "PackingListGrouped_328.pdf", "PackingListGrouped_181.pdf"):
        matches = list(FIX.rglob(name))
        if matches:
            grouped[name] = extract_grouped_tables_heuristic(matches[0])

    # F181 acconto text sample
    f181 = FIX / "corpus_181" / "Fattura_181-con_acconti.pdf"
    f181_info = None
    if f181.exists():
        txt = (PdfReader(str(f181)).pages[0].extract_text() or "")
        f181_info = {
            "sha256": sha256(f181),
            "bytes": f181.stat().st_size,
            "pages": len(PdfReader(str(f181)).pages),
            "acconto_mentions": [ln for ln in txt.splitlines() if re.search(r"accont|anticip|BONIFICO|scadenz", ln, re.I)],
            "sample_head": txt[:1500],
        }

    report = {
        "tooling": {
            "python": "v2/.venv",
            "pypdf": True,
            "pdfplumber": False,
            "pdftotext": str(PDFTOTEXT) if PDFTOTEXT.exists() else None,
            "note": "pdfplumber not in production venv; not added to requirements",
        },
        "inventory": inventory,
        "origin_focus": origin_focus,
        "pl_grouped_heuristic": {k: {"layout_rows_candidate": v["layout_rows_candidate"]} for k, v in grouped.items()},
        "f181": f181_info,
    }

    (OUT / "INVENTORY.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write grouped full layouts separately (large)
    for k, v in grouped.items():
        (OUT / f"layout_{k}.txt").write_text(v["full_layout"], encoding="utf-8")

    # Cross-doc qty snapshot for 202 from pdftotext of key files
    cross = {}
    for label, rel in [
        ("fattura_202", "corpus_202/Fattura_202.pdf"),
        ("doganale_202", "corpus_202/FatturaDoganale_202.pdf"),
        ("pl_grouped_202", "corpus_202/PackingListGrouped_202.pdf"),
        ("pl_detail_202", "corpus_202/PackingList_202.pdf"),
    ]:
        p = FIX / rel
        cross[label] = pdftotext_layout(p) or ""
        (OUT / f"layout_{label}.txt").write_text(cross[label], encoding="utf-8")

    print("Wrote", OUT / "INVENTORY.json")
    print("PDFs analyzed:", len(inventory))
    print("Origin focus files:", len(origin_focus))


if __name__ == "__main__":
    main()
