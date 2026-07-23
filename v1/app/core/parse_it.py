"""Parsing de números e datas no formato italiano (it-IT)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.parse import optional_decimal

_EURO_RE = re.compile(r"[€]|EUR\b", re.IGNORECASE)
_BRL_RE = re.compile(r"R\$|BRL\b", re.IGNORECASE)
_IT_NUMBER_RE = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d+$|^-?\d+,\d+$")
_EN_NUMBER_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})*\.\d+$|^-?\d+\.\d+$")


def strip_currency_symbols(raw: str) -> tuple[str, list[str]]:
    currencies: list[str] = []
    if _EURO_RE.search(raw):
        currencies.append("EUR")
    if _BRL_RE.search(raw):
        currencies.append("BRL")
    cleaned = _EURO_RE.sub("", raw)
    cleaned = _BRL_RE.sub("", cleaned)
    return cleaned.strip(), currencies


def parse_it_number(value: Any) -> Decimal | None:
    """Interpreta números it-IT: 1.234,56 → 1234.56; 10.000,00 € → 10000.00."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))

    raw = str(value).strip()
    if not raw or raw in ("—", "-", "–"):
        return None

    cleaned, _ = strip_currency_symbols(raw)
    cleaned = cleaned.replace("\u00a0", " ").strip()
    if not cleaned:
        return None

    negative = cleaned.startswith("-") or cleaned.startswith("(")
    cleaned = cleaned.strip("-() ").strip()

    if _IT_NUMBER_RE.match(cleaned):
        normalized = cleaned.replace(".", "").replace(",", ".")
    elif _EN_NUMBER_RE.match(cleaned):
        normalized = cleaned.replace(",", "")
    elif re.fullmatch(r"-?\d+", cleaned):
        normalized = cleaned
    elif re.fullmatch(r"-?\d+,\d+", cleaned):
        normalized = cleaned.replace(",", ".")
    else:
        normalized = cleaned.replace(".", "").replace(",", ".") if "," in cleaned else cleaned

    try:
        dec = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return optional_decimal(cleaned)

    return -dec if negative and dec > 0 else dec


def parse_it_date(value: Any) -> tuple[str | None, bool]:
    """Retorna (iso_date, needs_review). Assume dd/mm/aaaa para strings ambíguas."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, False
    if isinstance(value, datetime):
        return value.date().isoformat(), False
    if isinstance(value, date):
        return value.isoformat(), False
    if isinstance(value, (int, float)):
        base = datetime(1899, 12, 30)
        return (base + __import__("datetime").timedelta(days=float(value))).date().isoformat(), False

    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat(), False
        except ValueError:
            continue

    m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", s)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), m.group(3)
        needs_review = day <= 12 and month <= 12 and day != month
        if year:
            y = int(year)
            if y < 100:
                y += 2000
        else:
            y = datetime.now().year
        try:
            return date(y, month, day).isoformat(), needs_review
        except ValueError:
            return None, True

    return None, True


def detect_currencies_in_values(values: list[Any]) -> list[str]:
    found: set[str] = set()
    for v in values:
        if v is None:
            continue
        s = str(v)
        if _EURO_RE.search(s):
            found.add("EUR")
        if _BRL_RE.search(s):
            found.add("BRL")
    return sorted(found)


def format_parse_example(raw: Any, parsed: Decimal | None) -> dict[str, str | None]:
    return {
        "raw": str(raw) if raw is not None else None,
        "parsed": str(parsed) if parsed is not None else None,
    }
