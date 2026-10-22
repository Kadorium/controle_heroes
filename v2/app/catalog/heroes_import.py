"""Idempotent import of the reviewed Heroes batch. Never writes epic_v2 — caller guards the URL."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.catalog import repository as repo
from app.catalog.errors import CatalogValidationError
from app.catalog.models import CatalogImportBatch, Product
from app.catalog.taxonomy import (
    ATTR_KEYS,
    IMPORT_DECISIONS,
    PROV_ABSENT,
    PROV_BATCH,
    PROV_CSV,
    PROV_MANUAL,
    PROV_RULE,
    TAXONOMY_STATUSES,
    category_by_name,
    ensure_taxonomy,
    type_by_name,
)

PROV_ALIASES: dict[str, tuple[str, ...]] = {
    "country_of_origin": ("country_of_origin", "origin"),
    "category_id": ("category", "category_id"),
    "product_type_id": ("product_type", "product_type_id"),
    "import_decision": ("import_decision", "decision"),
}


def preview_heroes_batch(rows: list[dict[str, Any]]) -> dict[str, Any]:
    stats = {
        "create": 0,
        "update": 0,
        "skip": 0,
        "conflicts": [],
        "review": 0,
        "classification_review": 0,
        "ignored": 0,
    }
    skus: list[str] = []
    for row in rows:
        sku = (row.get("sku") or "").strip()
        if not sku:
            stats["conflicts"].append({"sku": "?", "reason": "SKU ausente"})
            continue
        if sku in skus:
            stats["conflicts"].append({"sku": sku, "reason": "SKU duplicado na planilha"})
            continue
        skus.append(sku)
        decision = (row.get("decision") or row.get("import_decision") or "").strip()
        if decision and decision not in IMPORT_DECISIONS:
            stats["conflicts"].append({"sku": sku, "reason": f"decisão inválida ({decision})"})
            continue
        if decision == "IGNORAR":
            stats["ignored"] += 1
            stats["skip"] += 1
            continue
        if decision == "REVISAR":
            stats["review"] += 1
        if row.get("taxonomy_status") == "REVIEW":
            stats["classification_review"] += 1
        stats["create"] += 1
    stats["row_count"] = len(rows)
    stats["unique_skus"] = len(skus)
    return stats


def _empty(value: object | None) -> bool:
    return value is None or (isinstance(value, str) and not str(value).strip())


def _norm(value: object | None) -> object | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _attrs_owned(raw: dict[str, Any] | None) -> dict[str, str]:
    owned: dict[str, str] = {}
    for key in ATTR_KEYS:
        val = _norm((raw or {}).get(key))
        if isinstance(val, str):
            owned[key] = val
    return owned


def _is_manual(product: Product, field: str) -> bool:
    prov = product.provenance or {}
    keys = PROV_ALIASES.get(field, (field,))
    return any(prov.get(key) == PROV_MANUAL for key in keys)


def _mark_batch(product: Product, field: str) -> None:
    prov = dict(product.provenance or {})
    key = PROV_ALIASES.get(field, (field,))[0]
    prov[key] = PROV_BATCH
    product.provenance = prov


def _desired(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    category_name = (payload.get("category") or "").strip()
    type_name = (payload.get("product_type") or "").strip()
    cat = category_by_name(db, category_name) if category_name else None
    ptype = type_by_name(db, type_name) if type_name else None
    name = _norm(payload.get("commercial_name"))
    decision = _norm(payload.get("decision") or payload.get("import_decision"))
    return {
        "commercial_name": name,
        "description": str(name)[:512] if isinstance(name, str) else None,
        "short_description": _norm(payload.get("short_description")),
        "long_description": _norm(payload.get("long_description")),
        "is_active": bool(payload.get("is_active")),
        "lifecycle_status": _norm(payload.get("lifecycle_status")),
        "color": _norm(payload.get("color")),
        "country_of_origin": _norm(payload.get("country_of_origin")),
        "unit": _norm(payload.get("unit")),
        "supplier_sku": _norm(payload.get("supplier_sku")),
        "category_id": cat.id if cat else None,
        "product_type_id": ptype.id if ptype else None,
        "subcategory": _norm(payload.get("subcategory")),
        "taxonomy_status": _norm(payload.get("taxonomy_status")),
        "taxonomy_reason": _norm(payload.get("taxonomy_reason")),
        "import_decision": decision,
        "short_generic": bool(payload.get("short_generic")),
        "attributes": _attrs_owned(payload.get("attributes")),
        "category_name": category_name or None,
        "type_name": type_name or None,
        "cat": cat,
        "ptype": ptype,
    }


COMPARE_FIELDS = (
    "commercial_name",
    "description",
    "short_description",
    "long_description",
    "is_active",
    "lifecycle_status",
    "color",
    "country_of_origin",
    "unit",
    "supplier_sku",
    "category_id",
    "product_type_id",
    "subcategory",
    "taxonomy_status",
    "taxonomy_reason",
    "import_decision",
    "short_generic",
)


def _current(product: Product) -> dict[str, Any]:
    return {
        "commercial_name": _norm(product.commercial_name),
        "description": _norm(product.description),
        "short_description": _norm(product.short_description),
        "long_description": _norm(product.long_description),
        "is_active": bool(product.is_active),
        "lifecycle_status": _norm(product.lifecycle_status),
        "color": _norm(product.color),
        "country_of_origin": _norm(product.country_of_origin),
        "unit": _norm(product.unit),
        "supplier_sku": _norm(product.supplier_sku),
        "category_id": product.category_id,
        "product_type_id": product.product_type_id,
        "subcategory": _norm(product.subcategory),
        "taxonomy_status": _norm(product.taxonomy_status),
        "taxonomy_reason": _norm(product.taxonomy_reason),
        "import_decision": _norm(product.import_decision),
        "short_generic": bool(product.short_generic),
        "attributes": _attrs_owned(product.attributes),
    }


def _equal(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    for field in COMPARE_FIELDS:
        if current[field] != desired[field]:
            return False
    for key, value in desired["attributes"].items():
        if current["attributes"].get(key) != value:
            return False
    return True


def _manual_conflicts(existing: Product, desired: dict[str, Any], sku: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    current = _current(existing)
    for field in COMPARE_FIELDS:
        if current[field] == desired[field]:
            continue
        if _is_manual(existing, field):
            found.append(
                {
                    "sku": sku,
                    "field": field,
                    "reason": "edição manual não sobrescrita pelo lote",
                }
            )
    for key, value in desired["attributes"].items():
        if current["attributes"].get(key) == value:
            continue
        if _is_manual(existing, key):
            found.append(
                {
                    "sku": sku,
                    "field": key,
                    "reason": "edição manual não sobrescrita pelo lote",
                }
            )
    return found


def _apply_existing(existing: Product, desired: dict[str, Any], batch: CatalogImportBatch) -> list[str]:
    current = _current(existing)
    changed: list[str] = []
    for field in COMPARE_FIELDS:
        if current[field] == desired[field]:
            continue
        if field == "description":
            existing.description = desired["description"]
        elif field == "category_id":
            existing.category_id = desired["category_id"]
        elif field == "product_type_id":
            existing.product_type_id = desired["product_type_id"]
        else:
            setattr(existing, field, desired[field])
        _mark_batch(existing, field)
        changed.append(field)
    merged = dict(existing.attributes or {})
    attr_changed = False
    for key, value in desired["attributes"].items():
        if merged.get(key) != value:
            merged[key] = value
            _mark_batch(existing, key)
            changed.append(key)
            attr_changed = True
    if attr_changed:
        existing.attributes = merged
    if changed:
        existing.import_batch_id = batch.id
        existing.source_kind = "heroes_csv"
    return changed


def _validate_payload(sku: str, desired: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    decision = desired["import_decision"]
    if decision and decision not in IMPORT_DECISIONS:
        errors.append({"sku": sku, "reason": f"decisão inválida ({decision})"})
    status = desired["taxonomy_status"]
    if status and status not in TAXONOMY_STATUSES:
        errors.append({"sku": sku, "reason": f"taxonomy_status inválido ({status})"})
    if desired["category_name"] and desired["cat"] is None:
        errors.append({"sku": sku, "reason": f"categoria inválida ({desired['category_name']})"})
    if desired["type_name"] and desired["ptype"] is None:
        errors.append({"sku": sku, "reason": f"tipo inválido ({desired['type_name']})"})
    if not desired["commercial_name"]:
        errors.append({"sku": sku, "reason": "sem nome comercial"})
    return errors


def commit_heroes_batch(
    db: Session,
    payloads: list[dict[str, Any]],
    *,
    filename: str,
    checksum: str,
    actor_id: str | None,
) -> dict[str, Any]:
    ensure_taxonomy(db)
    preview = preview_heroes_batch(payloads)
    empty = {
        "batch_id": None,
        "processed": len(payloads),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "review": 0,
        "classification_review": 0,
        "review_skus": [],
        "conflicts": preview["conflicts"],
    }
    if preview["conflicts"]:
        return empty

    created = 0
    updated = 0
    unchanged = 0
    skipped = 0
    review_skus: list[str] = []
    classification_skus: list[str] = []
    pending: list[tuple[str, dict[str, Any], dict[str, Any], Product | None]] = []
    conflicts: list[dict[str, str]] = []

    for payload in payloads:
        sku = (payload.get("sku") or "").strip()
        desired = _desired(db, payload)
        decision = desired["import_decision"]
        if decision == "IGNORAR":
            skipped += 1
            continue
        conflicts.extend(_validate_payload(sku, desired, payload))
        existing = repo.get_product_by_sku(db, sku)
        if existing and existing.source_kind != "heroes_csv":
            conflicts.append({"sku": sku, "reason": "SKU já existe fora deste lote"})
            continue
        if existing:
            conflicts.extend(_manual_conflicts(existing, desired, sku))
        pending.append((sku, payload, desired, existing))

    if conflicts:
        empty["skipped"] = skipped
        empty["conflicts"] = conflicts
        return empty

    will_write = []
    for sku, payload, desired, existing in pending:
        if existing is None:
            will_write.append((sku, payload, desired, existing, "create"))
            continue
        if _equal(_current(existing), desired):
            unchanged += 1
            if desired["import_decision"] == "REVISAR":
                review_skus.append(sku)
            if desired["taxonomy_status"] == "REVIEW":
                classification_skus.append(sku)
            continue
        will_write.append((sku, payload, desired, existing, "update"))

    batch = None
    if will_write:
        batch = repo.add_import_batch(
            db,
            CatalogImportBatch(
                source_kind="heroes_csv",
                filename=filename,
                checksum=checksum,
                row_count=len(payloads),
                created_by_actor_id=actor_id,
            ),
        )

    for sku, payload, desired, existing, action in will_write:
        if action == "update" and existing is not None and batch is not None:
            changed = _apply_existing(existing, desired, batch)
            updated += 1
            audit_public.record_event(
                db,
                actor_id=actor_id,
                entity_type="product",
                entity_id=str(existing.id),
                action="update",
                reason_code="CATALOG_HEROES_IMPORT",
                details=",".join(changed),
            )
            if desired["import_decision"] == "REVISAR":
                review_skus.append(sku)
            if desired["taxonomy_status"] == "REVIEW":
                classification_skus.append(sku)
            continue

        if batch is None:
            raise CatalogValidationError("lote ausente na criação")
        name = str(desired["commercial_name"])
        prov = dict(payload.get("provenance") or {"commercial_name": PROV_CSV})
        prov.setdefault("ncm", PROV_ABSENT)
        prov.setdefault("ean", PROV_ABSENT)
        prov.setdefault("image", PROV_ABSENT)
        prov.setdefault("category", PROV_RULE)
        prov.setdefault("product_type", PROV_RULE)
        prov["batch"] = PROV_BATCH
        product = Product(
            sku=sku,
            description=name[:512],
            commercial_name=name,
            short_description=desired["short_description"],
            long_description=desired["long_description"],
            fiscal_description=None,
            is_active=bool(desired["is_active"]),
            lifecycle_status=desired["lifecycle_status"]
            or ("ACTIVE" if desired["is_active"] else "DISCONTINUED"),
            ean=None,
            size=None,
            color=desired["color"],
            ncm=None,
            country_of_origin=desired["country_of_origin"],
            unit=desired["unit"],
            supplier_sku=desired["supplier_sku"],
            category_id=desired["category_id"],
            product_type_id=desired["product_type_id"],
            subcategory=desired["subcategory"],
            taxonomy_status=desired["taxonomy_status"],
            taxonomy_reason=desired["taxonomy_reason"],
            import_decision=desired["import_decision"],
            short_generic=bool(desired["short_generic"]),
            attributes=dict(desired["attributes"]),
            provenance=prov,
            source_kind="heroes_csv",
            import_batch_id=batch.id,
        )
        repo.add_product(db, product)
        db.flush()
        created += 1
        audit_public.record_event(
            db,
            actor_id=actor_id,
            entity_type="product",
            entity_id=str(product.id),
            action="create",
            reason_code="CATALOG_HEROES_IMPORT",
            details=sku,
        )
        if desired["import_decision"] == "REVISAR":
            review_skus.append(sku)
        if desired["taxonomy_status"] == "REVIEW":
            classification_skus.append(sku)

    db.flush()
    return {
        "batch_id": batch.id if batch is not None else None,
        "processed": len(payloads),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "review": len(review_skus),
        "classification_review": len(classification_skus),
        "review_skus": review_skus,
        "conflicts": [],
    }
