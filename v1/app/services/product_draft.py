"""Produtos rascunho (DRAFT) — pré-cadastro Heroes e fila de completar."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ImportationItem, InvoiceItem, Product
from app.services.heroes_product_aliases import merge_heroes_aliases_into_notes, save_heroes_aliases_on_product
from app.services.product_catalog import LIFECYCLE_ACTIVE, LIFECYCLE_DRAFT

HEROES_DRAFT_MARKER = "HEROES_DRAFT:"
_DRAFT_META_RE = re.compile(
    rf"^{re.escape(HEROES_DRAFT_MARKER)}\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def format_draft_meta_line(*, origin_run_id: int | None, origin_importation_id: int | None) -> str:
    parts: list[str] = []
    if origin_run_id is not None:
        parts.append(f"run={origin_run_id}")
    if origin_importation_id is not None:
        parts.append(f"importation={origin_importation_id}")
    return f"{HEROES_DRAFT_MARKER} {' '.join(parts)}".strip()


def parse_draft_meta(commercial_notes: str | None) -> dict:
    if not commercial_notes:
        return {}
    match = _DRAFT_META_RE.search(commercial_notes)
    if not match:
        return {}
    meta: dict = {}
    for token in match.group(1).split():
        if "=" in token:
            key, val = token.split("=", 1)
            if key == "run":
                meta["origin_run_id"] = int(val)
            elif key == "importation":
                meta["origin_importation_id"] = int(val)
    return meta


def merge_draft_meta_into_notes(
    commercial_notes: str | None,
    *,
    origin_run_id: int | None,
    origin_importation_id: int | None,
) -> str:
    line = format_draft_meta_line(
        origin_run_id=origin_run_id,
        origin_importation_id=origin_importation_id,
    )
    if not commercial_notes or not commercial_notes.strip():
        return line
    if _DRAFT_META_RE.search(commercial_notes):
        return _DRAFT_META_RE.sub(line, commercial_notes, count=1)
    return commercial_notes.rstrip() + "\n" + line


def _next_draft_sku(db: Session, *, origin_run_id: int) -> str:
    prefix = f"DRAFT-{origin_run_id}-"
    existing = (
        db.query(Product.sku_code)
        .filter(Product.sku_code.like(f"{prefix}%"))
        .all()
    )
    seq = 1
    used = {row[0] for row in existing}
    while f"{prefix}{seq}" in used:
        seq += 1
    return f"{prefix}{seq}"


def create_draft_product(
    db: Session,
    *,
    name_raw: str,
    category: str,
    origin_run_id: int | None = None,
    origin_importation_id: int | None = None,
    aliases: list[str] | None = None,
    user_id: int | None = None,
) -> Product:
    run_id = origin_run_id or 0
    sku = _next_draft_sku(db, origin_run_id=run_id)
    prod = Product(
        sku_code=sku,
        description=name_raw.strip(),
        category=category or "OTHER",
        lifecycle_status=LIFECYCLE_DRAFT,
        product_group="Sem grupo",
        commercial_notes=merge_draft_meta_into_notes(
            None,
            origin_run_id=origin_run_id,
            origin_importation_id=origin_importation_id,
        ),
    )
    db.add(prod)
    db.flush()
    alias_list = list(aliases or [name_raw])
    save_heroes_aliases_on_product(prod, alias_list)
    return prod


def list_draft_products(db: Session) -> list[dict]:
    rows = (
        db.query(Product)
        .filter(Product.is_active.is_(True), Product.lifecycle_status == LIFECYCLE_DRAFT)
        .order_by(Product.created_at.desc())
        .all()
    )
    result: list[dict] = []
    for p in rows:
        meta = parse_draft_meta(p.commercial_notes)
        orders_count = (
            db.query(func.count(func.distinct(ImportationItem.importation_id)))
            .filter(ImportationItem.product_id == p.id, ImportationItem.is_active.is_(True))
            .scalar()
            or 0
        )
        result.append(
            {
                "id": p.id,
                "sku_code": p.sku_code,
                "description": p.description,
                "category": p.category,
                "product_group": p.product_group,
                "origin_run_id": meta.get("origin_run_id"),
                "origin_importation_id": meta.get("origin_importation_id"),
                "referencing_importation_count": int(orders_count),
                "created_at": p.created_at,
            }
        )
    return result


def importation_has_draft_products(db: Session, importation_id: int) -> bool:
    return (
        db.query(ImportationItem.id)
        .join(Product, Product.id == ImportationItem.product_id)
        .filter(
            ImportationItem.importation_id == importation_id,
            ImportationItem.is_active.is_(True),
            Product.lifecycle_status == LIFECYCLE_DRAFT,
            Product.is_active.is_(True),
        )
        .first()
        is not None
    )


def complete_draft_product(
    db: Session,
    product_id: int,
    *,
    sku_code: str,
    description: str,
    category: str,
    product_group: str,
    user_id: int | None = None,
) -> Product:
    prod = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not prod:
        raise ValueError("Produto não encontrado")
    if prod.lifecycle_status != LIFECYCLE_DRAFT:
        raise ValueError("Somente produtos rascunho podem ser completados por este fluxo")

    sku = sku_code.strip()
    if not sku:
        raise ValueError("SKU obrigatório")
    dup = (
        db.query(Product)
        .filter(Product.sku_code == sku, Product.id != product_id)
        .first()
    )
    if dup:
        raise ValueError(f"SKU já cadastrado: {sku}")

    prod.sku_code = sku
    prod.description = description.strip()
    prod.category = category
    prod.product_group = product_group.strip() or "Sem grupo"
    prod.lifecycle_status = LIFECYCLE_ACTIVE

    for item in db.query(ImportationItem).filter(
        ImportationItem.product_id == product_id,
        ImportationItem.is_active.is_(True),
    ):
        item.description = prod.description
        item.supplier_sku = prod.supplier_code or item.supplier_sku

    for inv_item in db.query(InvoiceItem).filter(InvoiceItem.product_id == product_id):
        inv_item.description = prod.description

    return prod


def link_draft_to_product(
    db: Session,
    draft_id: int,
    target_product_id: int,
    *,
    user_id: int | None = None,
) -> Product:
    """Reatribui itens do rascunho ao produto existente e anula o rascunho."""
    draft = db.query(Product).filter(Product.id == draft_id, Product.is_active.is_(True)).first()
    if not draft or draft.lifecycle_status != LIFECYCLE_DRAFT:
        raise ValueError("Rascunho não encontrado")
    target = db.query(Product).filter(
        Product.id == target_product_id,
        Product.is_active.is_(True),
        Product.lifecycle_status != LIFECYCLE_DRAFT,
    ).first()
    if not target:
        raise ValueError("Produto destino não encontrado")

    for item in db.query(ImportationItem).filter(
        ImportationItem.product_id == draft_id,
        ImportationItem.is_active.is_(True),
    ):
        item.product_id = target.id
        item.description = target.description

    for inv_item in db.query(InvoiceItem).filter(InvoiceItem.product_id == draft_id):
        inv_item.product_id = target.id
        inv_item.description = target.description

    target.commercial_notes = merge_heroes_aliases_into_notes(
        target.commercial_notes,
        [draft.description],
    )

    draft.is_active = False
    draft.archived_at = datetime.now(timezone.utc)
    draft.archived_by_id = user_id
    draft.archive_reason = f"Vinculado ao produto {target.sku_code} (#{target.id})"
    return target


def create_draft_from_staging(
    db: Session,
    staging_id: int,
    *,
    user_id: int | None = None,
) -> Product:
    from app.core.enums import StagingRowStatus
    from app.models import StagingImportRow
    from app.services.heroes_xlsx_staging import resolve_staging_sku

    staging = db.query(StagingImportRow).filter(StagingImportRow.id == staging_id).first()
    if not staging:
        raise ValueError("Linha staging não encontrada")
    data = staging.parsed_data_json or {}
    name_raw = str(data.get("product_name_raw") or "").strip()
    if not name_raw:
        raise ValueError("Nome bruto ausente no staging")

    category = str(data.get("suggested_category") or "OTHER")
    run_id = data.get("heroes_run_id")
    draft = create_draft_product(
        db,
        name_raw=name_raw,
        category=category,
        origin_run_id=int(run_id) if run_id is not None else None,
        aliases=data.get("aliases") or [name_raw],
        user_id=user_id,
    )
    resolve_staging_sku(
        db,
        staging_id,
        product_id=draft.id,
        user_id=user_id,
        save_aliases=False,
    )
    staging.status = StagingRowStatus.APPROVED.value
    return draft
