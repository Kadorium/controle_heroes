"""Testes unitários de totais e dinheiro Orders."""

from decimal import Decimal

from app.orders.money import line_amount, parse_decimal, require_positive_qty
from app.orders.queries import OrderTotals, compute_totals
from app.orders.models import OrderItem


def test_empty_price_is_null_not_zero():
    assert parse_decimal(None) is None
    assert parse_decimal("") is None
    assert parse_decimal("  ") is None
    assert line_amount(Decimal("2"), None) is None


def test_line_amount_rounding_half_up():
    amt = line_amount(Decimal("3"), Decimal("1.11115"))
    assert amt == Decimal("3.3335")


def test_require_positive_qty():
    assert require_positive_qty("2.5") == Decimal("2.5000")
    try:
        require_positive_qty("0")
        assert False
    except Exception as e:
        assert getattr(e, "code", None) == "validation_error"


def test_commercial_total_null_when_unpriced():
    items = [
        OrderItem(
            id=1,
            order_id=1,
            product_id=1,
            sku_snapshot="A",
            description_snapshot="a",
            quantity=Decimal("2"),
            unit_price=Decimal("10"),
            position=1,
        ),
        OrderItem(
            id=2,
            order_id=1,
            product_id=2,
            sku_snapshot="B",
            description_snapshot="b",
            quantity=Decimal("1"),
            unit_price=None,
            position=2,
        ),
    ]
    t = compute_totals(items)
    assert t.priced_subtotal == Decimal("20.0000")
    assert t.unpriced_item_count == 1
    assert t.commercial_total is None


def test_commercial_total_complete():
    items = [
        OrderItem(
            id=1,
            order_id=1,
            product_id=1,
            sku_snapshot="A",
            description_snapshot="a",
            quantity=Decimal("2"),
            unit_price=Decimal("10"),
            position=1,
        ),
    ]
    t = compute_totals(items)
    assert t.commercial_total == Decimal("20.0000")
    assert t.unpriced_item_count == 0
