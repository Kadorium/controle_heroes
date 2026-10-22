"""Serialização HTTP de Product — qualidade e nomes de classificação."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.catalog.models import Product
from app.catalog.quality import quality_payload
from app.catalog.taxonomy import PROVENANCE_LABELS


def _dec(value: Decimal | None) -> Decimal | None:
    return value


def provenance_entries(product: Product) -> list[dict[str, str]]:
    raw = product.provenance or {}
    entries: list[dict[str, str]] = []
    labels = {
        "commercial_name": "Nome comercial",
        "short_description": "Descrição curta",
        "category": "Categoria",
        "subcategory": "Subcategoria",
        "product_type": "Tipo",
        "sport": "Esporte",
        "line": "Linha",
        "model": "Modelo",
        "collection_year": "Coleção",
        "color": "Cor",
        "ncm": "NCM",
        "ean": "EAN",
        "fiscal_description": "Descrição fiscal",
        "image": "Imagem",
        "supplier_sku": "Código do fornecedor",
    }
    for key, title in labels.items():
        source = raw.get(key)
        if not source:
            continue
        entries.append(
            {
                "field": key,
                "label": title,
                "source": str(source),
                "source_label": PROVENANCE_LABELS.get(str(source), "Origem registrada"),
            }
        )
    if product.import_batch_id:
        entries.append(
            {
                "field": "batch",
                "label": "Lote de importação",
                "source": "import_batch",
                "source_label": f"Lote #{product.import_batch_id}",
            }
        )
    return entries


def product_dict(product: Product, *, notices: list[str] | None = None) -> dict[str, Any]:
    quality = quality_payload(product)
    attrs = dict(product.attributes or {})
    derived_note = None
    if product.category_id and (product.provenance or {}).get("category") == "deterministic_rule":
        derived_note = "Classificação proposta a partir do histórico."
    return {
        "id": product.id,
        "sku": product.sku,
        "description": product.description,
        "commercial_name": product.commercial_name or product.description,
        "short_description": product.short_description,
        "long_description": product.long_description,
        "fiscal_description": product.fiscal_description,
        "is_active": product.is_active,
        "lifecycle_status": product.lifecycle_status,
        "ean": product.ean,
        "size": product.size,
        "color": product.color,
        "ncm": product.ncm,
        "country_of_origin": product.country_of_origin,
        "unit": product.unit,
        "net_weight_kg": _dec(product.net_weight_kg),
        "supplier_sku": product.supplier_sku,
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else None,
        "category_slug": product.category.slug if product.category else None,
        "subcategory": product.subcategory,
        "product_type_id": product.product_type_id,
        "product_type_name": product.product_type.name if product.product_type else None,
        "product_type_slug": product.product_type.slug if product.product_type else None,
        "taxonomy_status": product.taxonomy_status,
        "taxonomy_reason": product.taxonomy_reason,
        "import_decision": product.import_decision,
        "short_generic": bool(product.short_generic),
        "needs_review": quality["needs_review"],
        "needs_product_review": quality["needs_product_review"],
        "needs_classification_review": quality["needs_classification_review"],
        "classification_note": derived_note,
        "attributes": attrs,
        "sport": attrs.get("sport"),
        "line": attrs.get("line"),
        "model": attrs.get("model"),
        "collection_year": attrs.get("collection_year"),
        "garment_kind": attrs.get("garment_kind"),
        "gender": attrs.get("gender"),
        "pack_qty": attrs.get("pack_qty"),
        "source_kind": product.source_kind,
        "import_batch_id": product.import_batch_id,
        "has_image": False,
        "quality": quality,
        "provenance": provenance_entries(product),
        "notices": notices or [],
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
