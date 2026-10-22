"""Qualidade do cadastro — três camadas humanas. Sem % opaco. NCM não é blocker."""

from __future__ import annotations

from typing import Any

from app.catalog.models import Product


def _filled(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _attr(product: Product, key: str) -> str:
    raw = (product.attributes or {}).get(key)
    return str(raw).strip() if raw else ""


def type_traits(product: Product) -> list[str]:
    ptype = product.product_type.name if product.product_type else ""
    bits: list[str] = []
    if ptype == "Raquete":
        bits = [_attr(product, "sport"), _attr(product, "model"), _attr(product, "collection_year")]
    elif ptype in ("Bolsa", "Mochila", "Mala"):
        bits = [_attr(product, "line") or _attr(product, "model"), _attr(product, "collection_year"), product.color or ""]
    elif ptype == "Consumível":
        bits = [_attr(product, "sport"), _attr(product, "pack_qty"), product.color or ""]
    elif ptype == "Equipamento":
        bits = [_attr(product, "sport")]
    elif ptype == "Acessório de vestuário":
        bits = [_attr(product, "line") or _attr(product, "model"), _attr(product, "sport")]
    elif ptype == "Vestuário":
        bits = [_attr(product, "garment_kind"), _attr(product, "gender"), product.color or ""]
    return [b for b in bits if b]


def quality_payload(product: Product) -> dict[str, Any]:
    name = (product.commercial_name or product.description or "").strip()
    has_category = product.category_id is not None
    has_type = product.product_type_id is not None
    essential_items = [
        _item("name", "essencial", bool(name), "Nome comercial", "Sem nome comercial o produto não se reconhece na lista."),
        _item("category", "essencial", has_category, "Categoria", "Sem categoria o produto não entra na navegação comercial."),
        _item("type", "essencial", has_type, "Tipo de produto", "Sem tipo não dá para saber quais características se aplicam."),
    ]
    operation_items = [
        _item(
            "ncm",
            "operacao",
            _filled(product.ncm),
            "NCM",
            "NCM não informado — informação fiscal pendente",
        ),
        _item(
            "origin",
            "operacao",
            _filled(product.country_of_origin),
            "Origem",
            "Origem não informada — informação fiscal pendente",
        ),
        _item(
            "unit",
            "operacao",
            _filled(product.unit),
            "Unidade",
            "Unidade não informada — informação operacional pendente",
        ),
    ]
    short_ok = _filled(product.short_description)
    commercial_items = [
        _item(
            "short_description",
            "comercial",
            short_ok,
            "Descrição curta",
            "Descrição curta não informada — a ficha fica pobre para indicar o produto.",
        ),
        _item(
            "image",
            "comercial",
            False,
            "Imagem",
            "Imagem não informada — mais difícil reconhecer na lista",
        ),
    ]
    ptype = product.product_type.name if product.product_type else ""
    if ptype == "Vestuário" and not _filled(product.color):
        commercial_items.append(
            _item("color", "comercial", False, "Cor", "Cor não informada para este tipo de peça.")
        )

    items = essential_items + operation_items + commercial_items
    essential_ok = all(i["ok"] for i in essential_items)
    operation_ok = all(i["ok"] for i in operation_items)
    commercial_ok = all(i["ok"] for i in commercial_items)
    pending = [i for i in items if not i["ok"]]
    summary = (
        f"{'Essencial completo' if essential_ok else 'Essencial incompleto'}"
        f" · {len(pending)} pendência{'s' if len(pending) != 1 else ''}"
    )
    return {
        "essential_ok": essential_ok,
        "operation_ok": operation_ok,
        "commercial_ok": commercial_ok,
        "pending_count": len(pending),
        "summary": summary,
        "items": items,
        "traits": type_traits(product),
        "quality_incomplete": (not essential_ok) or (not short_ok),
        "needs_review": product.import_decision == "REVISAR",
        "needs_product_review": product.import_decision == "REVISAR",
        "needs_classification_review": product.taxonomy_status == "REVIEW",
        "short_generic": bool(product.short_generic),
        "missing_image": True,
        "missing_ncm": not _filled(product.ncm),
        "incomplete_mdm": (not _filled(product.ncm)) or (not _filled(product.ean)),
    }


def _item(code: str, layer: str, ok: bool, label: str, consequence: str) -> dict[str, Any]:
    return {"code": code, "layer": layer, "ok": ok, "label": label, "consequence": consequence}
