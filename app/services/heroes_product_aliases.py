"""Aliases Heroes gravados no produto (de-para manual persistente)."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import Product

HEROES_ALIASES_MARKER = "HEROES_ALIASES:"
_ALIASES_LINE_RE = re.compile(
    rf"^{re.escape(HEROES_ALIASES_MARKER)}\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_heroes_aliases(commercial_notes: str | None) -> set[str]:
    if not commercial_notes:
        return set()
    match = _ALIASES_LINE_RE.search(commercial_notes)
    if not match:
        return set()
    raw = match.group(1)
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def format_heroes_aliases_line(aliases: set[str]) -> str:
    ordered = sorted(aliases, key=str.lower)
    return f"{HEROES_ALIASES_MARKER} {', '.join(ordered)}"


def merge_heroes_aliases_into_notes(
    commercial_notes: str | None,
    new_aliases: list[str],
) -> str:
    existing = parse_heroes_aliases(commercial_notes)
    for alias in new_aliases:
        if alias and str(alias).strip():
            existing.add(str(alias).strip().lower())
    line = format_heroes_aliases_line(existing)
    if not commercial_notes or not commercial_notes.strip():
        return line
    if _ALIASES_LINE_RE.search(commercial_notes):
        return _ALIASES_LINE_RE.sub(line, commercial_notes, count=1)
    return commercial_notes.rstrip() + "\n" + line


def save_heroes_aliases_on_product(
    product: Product,
    aliases: list[str],
    *,
    extra_aliases: list[str] | None = None,
) -> None:
    all_names = list(aliases) + list(extra_aliases or [])
    product.commercial_notes = merge_heroes_aliases_into_notes(
        product.commercial_notes,
        all_names,
    )


def match_product_by_stored_aliases(db: Session, product_name_raw: str) -> Product | None:
    term = str(product_name_raw).strip().lower()
    if not term:
        return None
    products = (
        db.query(Product)
        .filter(
            Product.is_active.is_(True),
            Product.commercial_notes.isnot(None),
        )
        .all()
    )
    matches = [p for p in products if term in parse_heroes_aliases(p.commercial_notes)]
    if len(matches) == 1:
        return matches[0]
    return None
