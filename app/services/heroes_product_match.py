"""Match racchetta Heroes → Product cadastrado (chave canônica + match exato)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import ProductCategory
from app.models import Product
from app.services.heroes_product_aliases import match_product_by_stored_aliases, parse_heroes_aliases
from app.services.heroes_racchetta_key import RacchettaKey, canonical_key_for_matching, parse_racchetta_key


@dataclass
class ProductMatchCandidate:
    product: Product
    score: int
    reason: str


def parse_racchetta_key_from_name(product_name_raw: str | None) -> RacchettaKey | None:
    return parse_racchetta_key(product_name_raw)


def match_product(db: Session, product_name_raw: str | None) -> Product | None:
    """Match exato: aliases gravados → supplier_code → sku_code → description."""
    if not product_name_raw or not str(product_name_raw).strip():
        return None

    alias_hit = match_product_by_stored_aliases(db, product_name_raw)
    if alias_hit:
        return alias_hit

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


def _product_keys(product: Product) -> list[RacchettaKey]:
    keys: list[RacchettaKey] = []
    for field in ("description", "supplier_code", "sku_code"):
        val = getattr(product, field, None)
        if val:
            parsed = parse_racchetta_key(str(val))
            if parsed:
                keys.append(parsed)
    for alias in parse_heroes_aliases(product.commercial_notes):
        parsed = parse_racchetta_key(alias)
        if parsed:
            keys.append(parsed)
    return keys


def _category_penalty(product: Product, category_hint: str | None) -> int:
    if not category_hint or category_hint != ProductCategory.RACKET.value:
        return 0
    if product.category in (
        ProductCategory.BAG_ACCESSORY.value,
        ProductCategory.APPAREL.value,
        ProductCategory.BALL.value,
    ):
        return 40
    return 0


def find_product_candidates(
    db: Session,
    product_name_raw: str | None,
    *,
    category_hint: str | None = None,
    limit: int = 5,
) -> list[ProductMatchCandidate]:
    """Candidatos ordenados por score — sugestão para revisão, sem auto-vínculo."""
    sheet_canonical = canonical_key_for_matching(product_name_raw)
    if not sheet_canonical:
        return []

    products = db.query(Product).filter(Product.is_active.is_(True)).all()
    scored: dict[int, ProductMatchCandidate] = {}

    for product in products:
        penalty = _category_penalty(product, category_hint)
        best_score = 0
        best_reason = ""

        for pkey in _product_keys(product):
            if pkey.canonical_key == sheet_canonical:
                score = 100 - penalty
                reason = "chave canônica idêntica"
                if score > best_score:
                    best_score = score
                    best_reason = reason
                continue

            parsed_sheet = parse_racchetta_key(product_name_raw)
            if parsed_sheet and pkey.base_name == parsed_sheet.base_name:
                launch_year = product.launch_date.year if product.launch_date else None
                if parsed_sheet.year and launch_year == parsed_sheet.year:
                    score = 90 - penalty
                    reason = "base + launch_date"
                elif parsed_sheet.year is None and launch_year:
                    score = 85 - penalty
                    reason = "base sem ano (ano corrente/cadastro)"
                else:
                    continue
                if score > best_score:
                    best_score = score
                    best_reason = reason

        if best_score > 0:
            existing = scored.get(product.id)
            if existing is None or best_score > existing.score:
                scored[product.id] = ProductMatchCandidate(
                    product=product,
                    score=best_score,
                    reason=best_reason,
                )

    ordered = sorted(scored.values(), key=lambda c: (-c.score, c.product.sku_code))
    return ordered[:limit]
