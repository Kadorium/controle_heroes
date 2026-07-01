"""Testes heroes_financial_preview — overrides e validação."""

from app.services.heroes_financial_preview import apply_financial_overrides, build_financial_review
from app.services.heroes_xlsx_parser import parse_xlsx_sheet
from tests.fixtures.heroes_xlsx_builder import build_ordine_132_xlsx


def test_apply_financial_overrides_updates_acconto_and_versato():
    preview = parse_xlsx_sheet(build_ordine_132_xlsx(), "ordine 132")
    apply_financial_overrides(
        preview,
        versato_override="200000",
        acconto_overrides={"72": "6000"},
    )
    review = preview["financial_review"]
    assert review["versato_amount"] == "200000"
    blocks = preview["invoice_blocks"]
    b72 = next(b for b in blocks if str(b.get("invoice_number")) == "72")
    assert b72["acconto_payments"][0]["amount"] == "6000"


def test_financial_review_delta_rimasto_warning():
    preview = parse_xlsx_sheet(build_ordine_132_xlsx(), "ordine 132")
    preview["invoice_items"][-1]["acconto_remaining"] = "2250"
    review = build_financial_review(preview)
    assert review["requires_manual_review"] is True
    assert any("rimasto" in w.lower() for w in review["warnings"])
