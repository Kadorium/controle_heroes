from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANT = Decimal("0.0001")


def parse_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if s == "":
        return None
    return Decimal(s)


def require_positive_qty(value: str | Decimal) -> Decimal:
    qty = parse_decimal(value if not isinstance(value, str) else value)
    if qty is None or qty <= 0:
        from app.orders.errors import OrderValidationError

        raise OrderValidationError("Quantidade deve ser > 0")
    return qty.quantize(MONEY_QUANT)


def line_amount(quantity: Decimal, unit_price: Decimal | None) -> Decimal | None:
    if unit_price is None:
        return None
    return (quantity * unit_price).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def normalize_unit(value: str | None) -> str | None:
    """Optional documentary unit snapshot (PZ, SET, CTNS, UN, …). Not a full UoM module."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if len(s) > 16:
        from app.orders.errors import OrderValidationError

        raise OrderValidationError("unit máximo 16 caracteres")
    return s.upper()
