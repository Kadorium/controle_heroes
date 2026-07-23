"""Normalização de nome de produto — remove # e extrai ano explícito."""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy.orm import Session

from app.models import Product

YEAR_TOKEN_RE = re.compile(r"\b(20[0-9]{2})\b")


def clean_product_description(description: str) -> tuple[str, int | None]:
    """Remove todos os `#` e extrai ano quando há exatamente um ano explícito (20xx)."""
    if not description or not description.strip():
        return description, None

    text = description.replace("#", "")
    text = " ".join(text.split())

    years = YEAR_TOKEN_RE.findall(text)
    if len(set(years)) != 1:
        return text.strip(), None

    year = int(years[0])
    cleaned = YEAR_TOKEN_RE.sub("", text)
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned, year


def launch_date_from_year(year: int) -> date:
    return date(year, 1, 1)


def normalize_existing_products(db: Session) -> dict[str, int]:
    """Limpa descrições já gravadas e preenche launch_date só quando vazio e ano explícito."""
    products = db.query(Product).filter(Product.is_active.is_(True)).all()
    updated = 0
    for product in products:
        cleaned, year = clean_product_description(product.description)
        changed = False
        if cleaned != product.description:
            product.description = cleaned
            changed = True
        if year is not None and product.launch_date is None:
            product.launch_date = launch_date_from_year(year)
            changed = True
        if changed:
            updated += 1
    if updated:
        db.commit()
    return {"updated": updated, "scanned": len(products)}
