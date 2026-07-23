from app.core.currency import normalize_import_currency


def test_usd_normalizes_to_eur():
    assert normalize_import_currency("USD") == "EUR"
    assert normalize_import_currency("usd") == "EUR"


def test_brl_preserved():
    assert normalize_import_currency("BRL") == "BRL"


def test_empty_defaults_eur():
    assert normalize_import_currency(None) == "EUR"
    assert normalize_import_currency("") == "EUR"
