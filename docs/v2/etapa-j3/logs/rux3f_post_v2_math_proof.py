"""RUX-3F-POST V2 — prove MATH_TOTAL_MISMATCH still fires from PDF total_document (read-only)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.ingestion.adapters.ordine_heroes_v1 import extract, _validate_math

pdf = Path("tests/fixtures/ingestion/corpus_589/Ordine_589.pdf")
raw = extract(pdf.read_bytes())
print("extracted_total_document=", raw.total_document)
print("line_count=", len(raw.lines))
print("sum_line_totals=", sum((ln.line_total or Decimal(0)) for ln in raw.lines))
print("taxable=", raw.total_taxable, "exempt=", raw.total_exempt)
print("taxes=", getattr(raw, "total_taxes", None), "discounts=", getattr(raw, "total_discounts", None), "shipping=", getattr(raw, "shipping_spese", None) or getattr(raw, "total_shipping", None))
print("raw_fields=", [a for a in dir(raw) if not a.startswith("_")])

ok = _validate_math(raw)
print("golden_codes=", [(i["code"], i["severity"]) for i in ok])

# Inject absurd printed total — must raise MATH_TOTAL_MISMATCH when composition clear
raw.total_document = Decimal("1.00")
bad = _validate_math(raw)
codes = [(i["code"], i["severity"]) for i in bad]
print("absurd_total_codes=", codes)
mismatch = [i for i in bad if i["code"] == "MATH_TOTAL_MISMATCH"]
print("MATH_TOTAL_MISMATCH_present=", bool(mismatch))
if mismatch:
    print("message=", mismatch[0]["message"])
    print("severity=", mismatch[0]["severity"])

from dataclasses import replace

raw2 = extract(pdf.read_bytes())
if raw2.lines:
    ln0 = raw2.lines[0]
    raw2.lines[0] = replace(ln0, quantity=Decimal("99999"))
    line_bad = _validate_math(raw2)
    print(
        "qty_corrupt_codes=",
        [(i["code"], i["severity"]) for i in line_bad if i["code"].startswith("MATH_")],
    )
