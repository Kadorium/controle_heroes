"""Testes da chave canônica racchetta Heroes."""

from datetime import date

from app.services.heroes_racchetta_key import (
    canonical_key_for_matching,
    parse_racchetta_key,
)


def test_show_variants_same_key():
    keys = [parse_racchetta_key(n) for n in ("show 26", "show26", "show-26", "SHOW-26")]
    assert all(k is not None for k in keys)
    canonical = {k.canonical_key for k in keys if k}
    assert canonical == {"show|2026"}


def test_show_plain_uses_current_year_for_matching():
    plain = canonical_key_for_matching("show", default_year=2026)
    with_year = canonical_key_for_matching("show 26", default_year=2026)
    assert plain == "show|2026"
    assert with_year == "show|2026"


def test_bull_vs_bull_26_same_when_merged_by_base():
    """Parse bruto difere; matching com ano corrente unifica."""
    plain = canonical_key_for_matching("bull", default_year=date.today().year)
    year = canonical_key_for_matching("bull 26", default_year=date.today().year)
    assert plain == year


def test_catalog_show_2026_matches_sheet():
    catalog = parse_racchetta_key("#SHOW 2026")
    sheet = parse_racchetta_key("show 26")
    assert catalog and sheet
    assert catalog.canonical_key == sheet.canonical_key


def test_thunder_show_not_same_as_show_2026():
    bag = canonical_key_for_matching("Thunder SHOW", default_year=2026)
    racket = canonical_key_for_matching("show 26", default_year=2026)
    assert bag == "thunder show|2026"
    assert racket == "show|2026"


def test_starlight_ruby_distinct_from_starlight_26():
    ruby = canonical_key_for_matching("starlight ruby", default_year=2026)
    s26 = canonical_key_for_matching("starlight 26", default_year=2026)
    assert ruby == "starlight ruby|2026"
    assert s26 == "starlight|2026"
