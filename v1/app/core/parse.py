from decimal import Decimal, InvalidOperation
from typing import Any


def optional_decimal(value: Any) -> Decimal | None:
    """Campo vazio nunca vira zero."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return int(value)
