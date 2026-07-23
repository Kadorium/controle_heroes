from decimal import Decimal

import pytest

from app.billing.money import compute_line, money2, split_scadenze_percent, validate_amount_terms
from app.billing.errors import InvoiceValidationError


def test_line_none_percent_unit():
    g, d, n = compute_line(
        quantity=Decimal("10"),
        unit_price_gross=Decimal("100"),
        discount_type="NONE",
        discount_unit_amount=None,
        discount_percent=None,
    )
    assert g == Decimal("1000.00")
    assert d == Decimal("0.00")
    assert n == Decimal("1000.00")

    g, d, n = compute_line(
        quantity=Decimal("10"),
        unit_price_gross=Decimal("100"),
        discount_type="PERCENT",
        discount_unit_amount=None,
        discount_percent=Decimal("10"),
    )
    assert d == Decimal("100.00")
    assert n == Decimal("900.00")

    g, d, n = compute_line(
        quantity=Decimal("10"),
        unit_price_gross=Decimal("100"),
        discount_type="UNIT_AMOUNT",
        discount_unit_amount=Decimal("5"),
        discount_percent=None,
    )
    assert d == Decimal("50.00")
    assert n == Decimal("950.00")


def test_line_undefined_discount():
    g, d, n = compute_line(
        quantity=Decimal("1"),
        unit_price_gross=Decimal("10"),
        discount_type=None,
        discount_unit_amount=None,
        discount_percent=None,
    )
    assert g == Decimal("10.00")
    assert d is None and n is None


def test_rounding_half_up():
    g, d, n = compute_line(
        quantity=Decimal("3"),
        unit_price_gross=Decimal("10.005"),
        discount_type="NONE",
        discount_unit_amount=None,
        discount_percent=None,
    )
    assert g == money2(Decimal("3") * Decimal("10.005"))


def test_scadenze_residual_last():
    amounts = split_scadenze_percent(Decimal("100.00"), [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")])
    assert sum(amounts) == Decimal("100.00")
    assert amounts[-1] == Decimal("100.00") - amounts[0] - amounts[1]


def test_scadenze_must_sum_100():
    with pytest.raises(InvoiceValidationError):
        split_scadenze_percent(Decimal("10"), [Decimal("50"), Decimal("40")])


def test_amount_terms_must_match_net():
    with pytest.raises(InvoiceValidationError):
        validate_amount_terms(Decimal("100.00"), [Decimal("40"), Decimal("50")])
    assert validate_amount_terms(Decimal("100.00"), [Decimal("40"), Decimal("60")]) == [
        Decimal("40.00"),
        Decimal("60.00"),
    ]
