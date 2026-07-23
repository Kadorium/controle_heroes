"""Sugestão automática de categoria de produto Heroes."""

from __future__ import annotations

import re

from app.core.enums import ProductCategory

RACKET_KEYWORDS = (
    "starlight", "aura", "fierce", "bull", "show", "arion", "rebel", "ison", "senna",
    "racchetta", "racket",
)
BALL_KEYWORDS = ("palline", "ball", "bola", "pallina")
BAG_KEYWORDS = ("washbag", "bag", "mochila", "bolsa", "accessory", "acessório")
APPAREL_KEYWORDS = ("shirt", "short", "skirt", "roupa", "apparel", "maglia", "t-shirt")
PICKLEBALL_KEYWORDS = ("pickleball",)


def suggest_product_category(name: str | None) -> tuple[str, float, str | None]:
    """
    Retorna (category, confidence 0-1, review_reason).
    confidence < 0.7 => revisão recomendada.
    """
    if not name or not str(name).strip():
        return ProductCategory.OTHER.value, 0.0, "nome vazio"

    text = str(name).lower().strip()

    if any(k in text for k in PICKLEBALL_KEYWORDS):
        if any(k in text for k in BALL_KEYWORDS):
            return ProductCategory.PICKLEBALL.value, 0.85, None
        return ProductCategory.PICKLEBALL.value, 0.75, None

    if any(k in text for k in BALL_KEYWORDS):
        return ProductCategory.BALL.value, 0.9, None

    if any(k in text for k in BAG_KEYWORDS):
        return ProductCategory.BAG_ACCESSORY.value, 0.9, None

    if any(k in text for k in APPAREL_KEYWORDS):
        return ProductCategory.APPAREL.value, 0.85, None

    if any(k in text for k in RACKET_KEYWORDS):
        return ProductCategory.RACKET.value, 0.85, None

    # Heurística: código modelo típico (letras+números curtos)
    if re.match(r"^[a-z0-9\-]{2,20}$", text.replace(" ", "")) and not any(
        k in text for k in ("wash", "bag", "ball", "pallin")
    ):
        return ProductCategory.RACKET.value, 0.55, "possível raquete — confirmar categoria"

    return ProductCategory.OTHER.value, 0.4, "categoria incerta — revisar"


def product_category_label(category: str | None) -> str:
    labels = {
        ProductCategory.RACKET.value: "Raquete",
        ProductCategory.BALL.value: "Bola",
        ProductCategory.BAG_ACCESSORY.value: "Bolsa/Acessório",
        ProductCategory.APPAREL.value: "Roupa",
        ProductCategory.PICKLEBALL.value: "Pickleball",
        ProductCategory.OTHER.value: "Outro",
    }
    return labels.get(category or ProductCategory.OTHER.value, "Outro")
