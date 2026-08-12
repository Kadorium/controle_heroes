"""Temporary PDF text extract helper for J# planning (not a V2 fixture).

Method: pdfplumber digital text extraction — NO OCR.
Writes *.txt (page-tagged extract_text) and optionally word coords.

Source corpus: v1/tests/Fwd_ A_C Ricardo/
"""
import glob
import os

import pdfplumber

base = r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\v1\tests\Fwd_ A_C Ricardo"
outdir = r"c:\Users\ricar\Desktop\projetos\EPIC\Controle\docs\v2\_tmp_pdf_extract"
os.makedirs(outdir, exist_ok=True)

files = [
    "PackingList_202.pdf",
    "PackingListGrouped_202.pdf",
    "FatturaDoganale_202.pdf",
    "Fattura_202.pdf",
    "PrintDeclaration_202.pdf",
    "Ordine_589 (1) (1).pdf",
]
files += [os.path.basename(p) for p in glob.glob(os.path.join(base, "SOLICIT*.pdf"))]
files += [
    os.path.join("F328 ita", "F328 ita", "PackingList_328.pdf"),
    os.path.join("F328 ita", "F328 ita", "PackingListGrouped_328.pdf"),
]

for fname in files:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print("MISSING", path)
        continue
    safe = os.path.basename(fname).replace(" ", "_")
    with pdfplumber.open(path) as pdf:
        print(fname, "pages=", len(pdf.pages))
        parts = []
        for i, page in enumerate(pdf.pages):
            parts.append(f"=== PAGE {i+1}/{len(pdf.pages)} ===\n{page.extract_text() or ''}")
        out_txt = os.path.join(outdir, safe.replace(".pdf", "") + ".txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("\n\n".join(parts))
