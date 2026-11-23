from app.costing.coverage import analyze
from app.costing.recon_build import build_pairs


def facts(notes="", reference="OP-EPIC-2026-01"):
    return {
        "invoices": [{"invoice_id": 1, "invoice_number": "FAT-EPIC-2026-01"},
                     {"invoice_id": 2, "invoice_number": "FAT-EPIC-2026-02"}],
        "invoice_lines": [{"invoice_id": 1, "process_net": "1000", "currency": "EUR"},
                          {"invoice_id": 2, "process_net": "600", "currency": "EUR"}],
        "fundings": [{"reference": reference, "notes": notes, "status": "CONFIRMED",
                      "declared_total": "2000", "tax_lines": [{"amount": "1200"}],
                      "expense_lines": [{"amount": "800"}]}],
    }


def test_operation_year_is_not_an_invoice_reference():
    coverage = analyze(facts("Criado via ingestão Numerário — IR 2026"))
    assert coverage["mentioned_invoice_refs"] == []
    assert coverage["extra_refs"] == []


def test_complete_references_stay_distinct_and_missing_reference_blocks():
    coverage = analyze(facts("Faturas: FAT-EPIC-2026-01/FAT-EPIC-2026-02"))
    assert coverage["mentioned_count"] == 2
    assert coverage["coverage"] == "COMPLETE"
    missing = analyze(facts("INV. FAT-EPIC-2026-010/FAT-EPIC-2026-01 EMBARQUE MARITIMA"))
    assert missing["extra_refs"] == ["FAT-EPIC-2026-010"]
    assert missing["coverage"] == "INCOMPLETE"


def test_matching_funding_total_is_not_a_divergence():
    source = facts()
    coverage = analyze(source)
    args = dict(kind="REVISED", lines=[], components=[], facts=source, freight_choice=None)
    assert not any(p["pair_type"] == "FUNDING_DECLARED" for p in build_pairs(coverage=coverage, **args))
    source["fundings"][0]["declared_total"] = "1999"
    pairs = build_pairs(coverage=analyze(source), **args)
    assert any(p["pair_type"] == "FUNDING_DECLARED" and p["delta"] == "1.00" for p in pairs)
