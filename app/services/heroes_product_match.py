"""Match racchetta Heroes → Product cadastrado (sem fuzzy, sem auto-criação)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Product


def match_product(db: Session, product_name_raw: str | None) -> Product | None:
    """Busca case-insensitive: supplier_code → sku_code → description."""
    if not product_name_raw or not str(product_name_raw).strip():
        return None
    term = str(product_name_raw).strip().lower()

    for field in ("supplier_code", "sku_code", "description"):
        col = getattr(Product, field)
        matches = (
            db.query(Product)
            .filter(
                Product.is_active.is_(True),
                col.isnot(None),
                func.lower(col) == term,
            )
            .all()
        )
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return None
    return None
