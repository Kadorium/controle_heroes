"""Money helpers for Costing — HALF_UP 2 (display) and ≥6 dp (allocations)."""

from decimal import ROUND_HALF_UP, Decimal

QTY_QUANT = Decimal("0.0001")
MONEY2 = Decimal("0.01")
ALLOC6 = Decimal("0.000001")


def parse_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if s == "":
        return None
    return Decimal(s)


def money2(value: Decimal) -> Decimal:
    return value.quantize(MONEY2, rounding=ROUND_HALF_UP)


def alloc6(value: Decimal) -> Decimal:
    return value.quantize(ALLOC6, rounding=ROUND_HALF_UP)


def decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")
