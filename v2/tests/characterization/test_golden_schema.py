"""Schema/presence + V1 characterization equivalence + V2 contract goldens (no V1 imports)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.billing.money import compute_line, split_scadenze_percent
from app.ingestion.public import parse_it_date, parse_it_number
from app.treasury.fx_money import canonical_scenario_numbers

GOLDENS = Path(__file__).parent / "goldens"
REQUIRED_KEYS_V1 = {
    "schema_version",
    "scenario",
    "v1_function",
    "currency_context",
    "rounding",
    "origin",
    "generator_commit",
    "input_hash",
    "cases",
}
REQUIRED_KEYS_V2_CONTRACT = {
    "schema_version",
    "scenario",
    "v2_function",
    "origin",
    "rule_ref",
    "rounding",
    "null_policy",
    "cases",
}


def _golden_files() -> list[Path]:
    return sorted(GOLDENS.glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", _golden_files(), ids=lambda p: p.name)
def test_golden_schema(path: Path):
    data = _load(path)
    if path.name.endswith(".v1.json"):
        missing = REQUIRED_KEYS_V1 - set(data)
        assert not missing, f"{path.name} missing keys: {sorted(missing)}"
        assert data["origin"] == "v1 characterization export"
    elif path.name.endswith(".v2.json"):
        missing = REQUIRED_KEYS_V2_CONTRACT - set(data)
        assert not missing, f"{path.name} missing keys: {sorted(missing)}"
        assert data["origin"] == "v2-contract"
        assert data.get("rule_ref")
    else:
        pytest.fail(f"Unexpected golden suffix: {path.name}")

    assert isinstance(data["schema_version"], int)
    assert data["schema_version"] >= 1
    assert isinstance(data["cases"], list) and len(data["cases"]) >= 1
    for case in data["cases"]:
        assert "input" in case
        assert "output" in case


def test_expected_scenarios_present():
    names = {p.name for p in _golden_files()}
    assert "parse_it_number.v1.json" in names
    assert "parse_it_date.v1.json" in names
    assert "billing_line.v2.json" in names
    assert "scadenze_split.v2.json" in names
    assert "fx_canonical.v2.json" in names


def test_v2_parse_it_number_matches_v1_golden():
    data = _load(GOLDENS / "parse_it_number.v1.json")
    for case in data["cases"]:
        raw = case["input"]
        expected = case["output"]
        got = parse_it_number(raw)
        got_out = str(got) if got is not None else None
        assert got_out == expected, f"input={raw!r}: got={got_out!r} expected={expected!r}"
        if got is None:
            assert expected is None
        else:
            assert got != 0 or expected == "0"  # empty/null never coerced to zero in golden


def test_v2_parse_it_date_matches_v1_golden():
    data = _load(GOLDENS / "parse_it_date.v1.json")
    for case in data["cases"]:
        raw = case["input"]
        expected = case["output"]
        iso, needs_review = parse_it_date(raw)
        assert {"iso_date": iso, "needs_review": needs_review} == expected, f"input={raw!r}"


def test_contract_billing_line():
    data = _load(GOLDENS / "billing_line.v2.json")
    assert data["origin"] == "v2-contract"
    for case in data["cases"]:
        inp = case["input"]
        exp = case["output"]
        g, d, n = compute_line(
            quantity=Decimal(inp["quantity"]),
            unit_price_gross=Decimal(inp["unit_price_gross"]),
            discount_type=inp["discount_type"],
            discount_unit_amount=(
                Decimal(inp["discount_unit_amount"])
                if inp["discount_unit_amount"] is not None
                else None
            ),
            discount_percent=(
                Decimal(inp["discount_percent"]) if inp["discount_percent"] is not None else None
            ),
        )
        assert str(g) == exp["gross"]
        assert (str(d) if d is not None else None) == exp["discount"]
        assert (str(n) if n is not None else None) == exp["net"]


def test_contract_scadenze_split():
    data = _load(GOLDENS / "scadenze_split.v2.json")
    for case in data["cases"]:
        inp = case["input"]
        amounts = split_scadenze_percent(
            Decimal(inp["net"]), [Decimal(p) for p in inp["percents"]]
        )
        assert [str(a) for a in amounts] == case["output"]["amounts"]
        assert sum(amounts) == Decimal(inp["net"])


def test_contract_fx_canonical():
    data = _load(GOLDENS / "fx_canonical.v2.json")
    c = canonical_scenario_numbers()
    mapping = {
        "realized_brl": c.realized_brl,
        "realized_vs_reference": c.realized_vs_reference,
        "realized_vs_initial": c.realized_vs_initial,
        "projected_open_brl": c.projected_open_brl,
        "market_open_brl": c.market_open_brl,
        "online_vs_current": c.online_vs_current,
        "online_vs_initial": c.online_vs_initial,
        "total_vs_current": c.total_vs_current,
        "total_vs_initial": c.total_vs_initial,
    }
    for case in data["cases"]:
        key = case["input"]
        assert str(mapping[key]) == case["output"], f"{key}"
