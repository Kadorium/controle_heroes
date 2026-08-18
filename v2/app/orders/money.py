from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANT = Decimal("0.0001")
COMMERCIAL_QUANT = Decimal("0.01")


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


def money2(value: Decimal) -> Decimal:
    return value.quantize(COMMERCIAL_QUANT, rounding=ROUND_HALF_UP)


def decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def split_percent_amounts(base: Decimal, percents: list[Decimal]) -> list[Decimal]:
    """Residual na última parcela — mesmo critério comercial da Invoice, sem importar Billing."""
    if not percents:
        return []
    amounts: list[Decimal] = []
    allocated = Decimal("0.00")
    for i, pct in enumerate(percents):
        if i == len(percents) - 1:
            amounts.append(money2(base - allocated))
        else:
            part = money2(base * pct / Decimal("100"))
            amounts.append(part)
            allocated += part
    return amounts


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
