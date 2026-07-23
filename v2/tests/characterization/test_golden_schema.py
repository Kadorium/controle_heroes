"""Schema/presence tests for V1 characterization goldens (no V1 imports)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDENS = Path(__file__).parent / "goldens"
REQUIRED_KEYS = {
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


def _golden_files() -> list[Path]:
    return sorted(GOLDENS.glob("*.json"))


@pytest.mark.parametrize("path", _golden_files(), ids=lambda p: p.name)
def test_golden_schema(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_KEYS - set(data)
    assert not missing, f"{path.name} missing keys: {sorted(missing)}"
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


@pytest.mark.xfail(reason="Equivalência de cálculo V2 só após portar parse_it (Order-to-Pay+)", strict=False)
def test_v2_parse_equivalence_placeholder():
    """Placeholder: quando V2 portar parse_it, comparar output com golden."""
    assert False, "not implemented in V2 yet"
