"""Atributos variáveis validados pelo tipo. JSONB não aparece na UI."""

from __future__ import annotations

from typing import Any

from app.catalog.errors import CatalogValidationError
from app.catalog.taxonomy import ATTR_KEYS, allowed_subcategories


def normalize_attributes(raw: object | None) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise CatalogValidationError("Características inválidas")
    out: dict[str, str] = {}
    unknown = [k for k in raw if k not in ATTR_KEYS]
    if unknown:
        raise CatalogValidationError(f"Característica não suportada: {unknown[0]}")
    for key in ATTR_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if value is None or str(value).strip() == "":
            out[key] = ""
            continue
        text = str(value).strip()
        if key == "consumable_kind" and text not in ("BALL", "OVERGRIP", "OTHER"):
            raise CatalogValidationError("Escolha Bola, Overgrip ou Outro")
        if len(text) > 128:
            raise CatalogValidationError(f"{key} excede 128 caracteres")
        out[key] = text
    return out


def merge_attributes(current: dict[str, Any] | None, incoming: dict[str, str]) -> dict[str, str]:
    """Preserve keys not sent; empty incoming value removes the key."""
    merged = {k: str(v) for k, v in (current or {}).items() if k in ATTR_KEYS and v}
    merged.update(incoming)
    return {k: v for k, v in merged.items() if v}


def validate_subcategory(category_slug: str | None, subcategory: str | None) -> str | None:
    if not subcategory or not subcategory.strip():
        return None
    name = subcategory.strip()
    allowed = allowed_subcategories(category_slug)
    if allowed and name not in allowed:
        raise CatalogValidationError("Subcategoria não se aplica a esta categoria")
    if not allowed:
        raise CatalogValidationError("Esta categoria não usa subcategoria")
    return name
