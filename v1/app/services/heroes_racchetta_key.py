"""Chave canônica de racchetta Heroes — unifica variantes de grafia (show, show 26, show26)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

YEAR_FULL_RE = re.compile(r"\b(20[0-9]{2})\b")
GLUED_NAME_YEAR_RE = re.compile(r"^([a-z]+)(\d{2})$")


@dataclass(frozen=True)
class RacchettaKey:
    raw: str
    base_name: str
    year: int | None
    canonical_key: str


def _expand_short_year(token: str) -> int | None:
    if len(token) == 2 and token.isdigit():
        n = int(token)
        if 20 <= n <= 39:
            return 2000 + n
    return None


def parse_racchetta_key(product_name_raw: str | None) -> RacchettaKey | None:
    """Normaliza racchetta da planilha ou cadastro em base + ano (explícito ou ausente)."""
    if not product_name_raw or not str(product_name_raw).strip():
        return None

    raw = str(product_name_raw).strip()
    text = raw.lower().lstrip("#").replace("-", " ").replace("_", " ")
    text = " ".join(text.split())
    if text.startswith("the "):
        text = text[4:].strip()

    year: int | None = None
    full_years = YEAR_FULL_RE.findall(text)
    if len(set(full_years)) == 1:
        year = int(full_years[0])
        text = YEAR_FULL_RE.sub("", text)
        text = " ".join(text.split())

    tokens = text.split() if text else []

    if tokens:
        last = tokens[-1]
        glued = GLUED_NAME_YEAR_RE.match(last)
        if glued:
            yr = _expand_short_year(glued.group(2))
            if yr is not None:
                tokens = tokens[:-1] + [glued.group(1)]
                if year is None:
                    year = yr
        elif year is None:
            yr = _expand_short_year(last)
            if yr is not None and len(tokens) > 1:
                year = yr
                tokens = tokens[:-1]

    base_name = " ".join(tokens).strip()
    canonical_key = f"{base_name}|{year or ''}"
    return RacchettaKey(raw=raw, base_name=base_name, year=year, canonical_key=canonical_key)


def year_from_canonical_key(canonical_key: str) -> int | None:
    if "|" not in canonical_key:
        return None
    part = canonical_key.rsplit("|", 1)[-1]
    return int(part) if part.isdigit() else None


def canonical_key_for_matching(
    product_name_raw: str | None,
    *,
    reference_year: int | None = None,
    default_year: int | None = None,
) -> str | None:
    """Chave para agrupar/match: sem ano → ano de referência ou ano corrente."""
    parsed = parse_racchetta_key(product_name_raw)
    if not parsed:
        return None
    if parsed.year is not None:
        return parsed.canonical_key
    year = reference_year or default_year or date.today().year
    return f"{parsed.base_name}|{year}"
