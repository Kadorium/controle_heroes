"""Cadastro mestre de produtos — catálogo, readiness, ordens vinculadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AuditLog,
    DocumentAttachment,
    ImportationItem,
    ImportationOrder,
    InvoiceItem,
    LandedCostSkuAllocation,
    LandedCostVersion,
    NationalizationItem,
    Product,
    ShipmentItem,
    StockEntry,
    Supplier,
)

LIFECYCLE_ACTIVE = "ACTIVE"
LIFECYCLE_DISCONTINUED = "DISCONTINUED"
LIFECYCLE_ARCHIVED = "ARCHIVED"
LIFECYCLE_DRAFT = "DRAFT"

COMBOBOX_STATUSES = (LIFECYCLE_ACTIVE,)


class ProductReadinessError(Exception):
    def __init__(self, message: str, *, missing: list[str] | None = None, code: str = "not_ready"):
        super().__init__(message)
        self.missing = missing or []
        self.code = code


@dataclass
class BulkActionResult:
    succeeded: list[int] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"succeeded": self.succeeded, "skipped": self.skipped, "failed": self.failed}


def compute_pending_flags(product: Product, *, has_photo: bool = False) -> list[str]:
    flags: list[str] = []
    if not product.ncm:
        flags.append("ncm_pending")
    if not has_photo:
        flags.append("no_photo")
    if not product.default_supplier_id:
        flags.append("no_supplier")
    if product.weight_kg is None and product.volume_m3 is None:
        flags.append("no_weight_volume")
    if product.fiscal_review_required:
        flags.append("fiscal_review")
    return flags


def product_has_photo(db: Session, product_id: int) -> bool:
    return (
        db.query(DocumentAttachment.id)
        .filter(
            DocumentAttachment.entity_type == "product",
            DocumentAttachment.entity_id == str(product_id),
            DocumentAttachment.is_current_version.is_(True),
        )
        .first()
        is not None
    )


def product_used_in_importations(db: Session, product_id: int) -> bool:
    if db.query(ImportationItem.id).filter(ImportationItem.product_id == product_id).first():
        return True
    if db.query(InvoiceItem.id).filter(InvoiceItem.product_id == product_id).first():
        return True
    return False


def compute_product_readiness(product: Product, context: str) -> dict:
    missing: list[str] = []
    if context == "importation":
        if not product.description:
            missing.append("description")
        if not product.product_group or not str(product.product_group).strip():
            missing.append("product_group")
    elif context == "customs":
        if not product.ncm:
            missing.append("ncm")
        if not product.fiscal_description:
            missing.append("fiscal_description")
        if not product.country_of_origin:
            missing.append("country_of_origin")
        if not product.unit_of_measure:
            missing.append("unit_of_measure")
    elif context == "landed_cost":
        if product.weight_kg is None and product.volume_m3 is None:
            missing.append("weight_or_volume")
    return {"ready": len(missing) == 0, "missing_fields": missing, "context": context}


def validate_product_for_usage(
    db: Session,
    product: Product,
    context: str,
    *,
    allow_discontinued_override: bool = False,
    override_reason: str | None = None,
) -> None:
    if not product.is_active:
        raise ProductReadinessError("Produto anulado não pode ser utilizado.", code="cancelled")
    if product.lifecycle_status == LIFECYCLE_ARCHIVED:
        raise ProductReadinessError("Produto arquivado não pode ser utilizado.", code="archived")
    if product.lifecycle_status == LIFECYCLE_DISCONTINUED:
        if not allow_discontinued_override or not override_reason or len(override_reason.strip()) < 3:
            raise ProductReadinessError(
                "Produto descontinuado exige override com motivo.",
                code="discontinued",
            )
    readiness = compute_product_readiness(product, context)
    if not readiness["ready"]:
        raise ProductReadinessError(
            f"Produto incompleto para {context}.",
            missing=readiness["missing_fields"],
            code="incomplete",
        )


def list_product_groups(db: Session, *, visibility: str = "active") -> list[str]:
    rows = (
        _base_catalog_query(db, visibility)
        .with_entities(Product.product_group)
        .distinct()
        .order_by(Product.product_group)
        .all()
    )
    return [r[0] for r in rows if r[0]]


def _aggregate_product_quantities(db: Session, product_ids: list[int]) -> dict[int, dict[str, int]]:
    """Soma quantidades por estágio da cadeia pedido→trânsito→nacionalização→estoque."""
    from app.services.logistics import _shipped_total_for_display
    from app.services.nationalization import _nationalized_total_for_display, _stock_total_for_display

    empty = {"qty_ordered": 0, "qty_in_transit": 0, "qty_nationalization": 0, "qty_stock": 0}
    if not product_ids:
        return {}

    result = {pid: dict(empty) for pid in product_ids}
    items = (
        db.query(ImportationItem)
        .filter(
            ImportationItem.product_id.in_(product_ids),
            ImportationItem.is_active.is_(True),
        )
        .all()
    )
    for item in items:
        pid = item.product_id
        if pid is None:
            continue
        ordered = item.quantity_ordered or 0
        shipped = _shipped_total_for_display(db, item.id)
        nationalized = _nationalized_total_for_display(db, item.id)
        stocked = _stock_total_for_display(db, item.id)

        bucket = result.setdefault(pid, dict(empty))
        bucket["qty_ordered"] += ordered

        if stocked is not None:
            bucket["qty_stock"] += stocked

        if shipped is not None and shipped > 0:
            nat = nationalized if nationalized is not None else 0
            bucket["qty_in_transit"] += max(0, shipped - nat)

        if nationalized is not None:
            stk = stocked if stocked is not None else 0
            bucket["qty_nationalization"] += max(0, nationalized - stk)

    return result


def _base_catalog_query(db: Session, visibility: str = "active"):
    q = db.query(Product).options(joinedload(Product.default_supplier))
    if visibility == "active":
        q = q.filter(
            Product.is_active.is_(True),
            Product.lifecycle_status == LIFECYCLE_ACTIVE,
        )
    elif visibility == "archived":
        q = q.filter(Product.is_active.is_(True), Product.lifecycle_status == LIFECYCLE_ARCHIVED)
    elif visibility == "cancelled":
        q = q.filter(Product.is_active.is_(False))
    # visibility == "all" → sem filtro extra
    return q


def list_product_catalog(
    db: Session,
    *,
    q: str | None = None,
    visibility: str = "active",
    lifecycle_status: str | None = None,
    product_group: str | None = None,
    quick_filter: str | None = None,
    sort: str = "sku_code",
    sort_dir: str = "asc",
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    query = _base_catalog_query(db, visibility)
    if lifecycle_status:
        query = query.filter(Product.lifecycle_status == lifecycle_status)
    if product_group:
        query = query.filter(Product.product_group == product_group)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Product.sku_code.ilike(term),
                Product.description.ilike(term),
                Product.supplier_code.ilike(term),
                Product.ncm.ilike(term),
            )
        )
    if quick_filter == "ncm_pending":
        query = query.filter(or_(Product.ncm.is_(None), Product.ncm == ""))
    elif quick_filter == "no_supplier":
        query = query.filter(Product.default_supplier_id.is_(None))
    elif quick_filter == "no_weight_volume":
        query = query.filter(Product.weight_kg.is_(None), Product.volume_m3.is_(None))
    elif quick_filter == "fiscal_review":
        query = query.filter(Product.fiscal_review_required.is_(True))
    elif quick_filter == "discontinued":
        query = query.filter(Product.lifecycle_status == LIFECYCLE_DISCONTINUED)

    total = query.count()
    sort_col = getattr(Product, sort, Product.sku_code)
    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    products = query.offset(offset).limit(limit).all()

    product_ids = [p.id for p in products]
    photo_set: set[int] = set()
    photo_ids: dict[int, int] = {}
    if product_ids:
        for row in db.query(DocumentAttachment.entity_id, DocumentAttachment.id).filter(
            DocumentAttachment.entity_type == "product",
            DocumentAttachment.entity_id.in_([str(i) for i in product_ids]),
            DocumentAttachment.is_current_version.is_(True),
        ):
            try:
                pid = int(row[0])
                photo_set.add(pid)
                if pid not in photo_ids:
                    photo_ids[pid] = row[1]
            except (TypeError, ValueError):
                pass

    last_imp: dict[int, tuple] = {}
    if product_ids:
        rows = (
            db.query(
                ImportationItem.product_id,
                func.max(ImportationOrder.updated_at),
                func.max(ImportationOrder.po_number),
            )
            .join(ImportationOrder, ImportationOrder.id == ImportationItem.importation_id)
            .filter(ImportationItem.product_id.in_(product_ids))
            .group_by(ImportationItem.product_id)
            .all()
        )
        for pid, dt, po in rows:
            if pid:
                last_imp[pid] = (dt, po)

    last_lc: dict[int, Decimal | None] = {}
    if product_ids:
        lc_rows = (
            db.query(ImportationItem.product_id, LandedCostSkuAllocation.unit_cost)
            .join(LandedCostSkuAllocation, LandedCostSkuAllocation.importation_item_id == ImportationItem.id)
            .join(LandedCostVersion, LandedCostVersion.id == LandedCostSkuAllocation.landed_cost_version_id)
            .filter(ImportationItem.product_id.in_(product_ids))
            .order_by(LandedCostVersion.created_at.desc())
            .all()
        )
        for pid, cost in lc_rows:
            if pid and pid not in last_lc:
                last_lc[pid] = cost

    order_counts: dict[int, int] = {}
    if product_ids:
        for pid, cnt in (
            db.query(ImportationItem.product_id, func.count(func.distinct(ImportationItem.importation_id)))
            .filter(ImportationItem.product_id.in_(product_ids))
            .group_by(ImportationItem.product_id)
            .all()
        ):
            if pid:
                order_counts[pid] = cnt

    qty_by_product = _aggregate_product_quantities(db, product_ids)
    qty_defaults = {"qty_ordered": 0, "qty_in_transit": 0, "qty_nationalization": 0, "qty_stock": 0}

    items: list[dict] = []
    for p in products:
        has_photo = p.id in photo_set
        imp = last_imp.get(p.id)
        items.append(
            {
                "id": p.id,
                "sku_code": p.sku_code,
                "description": p.description,
                "ncm": p.ncm,
                "weight_kg": p.weight_kg,
                "volume_m3": p.volume_m3,
                "category": p.category,
                "lifecycle_status": p.lifecycle_status,
                "product_group": p.product_group,
                "product_subgroup": p.product_subgroup,
                "supplier_code": p.supplier_code,
                "default_supplier_id": p.default_supplier_id,
                "default_supplier_name": p.default_supplier.name if p.default_supplier else None,
                "country_of_origin": p.country_of_origin,
                "unit_of_measure": p.unit_of_measure,
                "fiscal_description": p.fiscal_description,
                "fiscal_review_required": p.fiscal_review_required,
                "launch_date": p.launch_date,
                "commercial_notes": p.commercial_notes,
                "is_active": p.is_active,
                "has_photo": has_photo,
                "photo_attachment_id": photo_ids.get(p.id),
                "pending_flags": compute_pending_flags(p, has_photo=has_photo),
                "last_importation_at": imp[0] if imp else None,
                "last_importation_po": imp[1] if imp else None,
                "last_landed_cost_unit": last_lc.get(p.id),
                "orders_count": order_counts.get(p.id, 0),
                **{**qty_defaults, **qty_by_product.get(p.id, {})},
            }
        )

    if quick_filter == "no_photo":
        items = [i for i in items if "no_photo" in i["pending_flags"]]
        total = len(items)

    return items, total


def list_products_for_combobox(db: Session, *, include_discontinued: bool = False) -> list[Product]:
    statuses = [LIFECYCLE_ACTIVE]
    if include_discontinued:
        statuses.append(LIFECYCLE_DISCONTINUED)
    return (
        db.query(Product)
        .filter(Product.is_active.is_(True), Product.lifecycle_status.in_(statuses))
        .order_by(Product.sku_code)
        .all()
    )


def get_product_detail(db: Session, product_id: int) -> dict | None:
    product = (
        db.query(Product)
        .options(joinedload(Product.default_supplier))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        return None
    has_photo = product_has_photo(db, product_id)
    photo_att = (
        db.query(DocumentAttachment.id)
        .filter(
            DocumentAttachment.entity_type == "product",
            DocumentAttachment.entity_id == str(product_id),
            DocumentAttachment.is_current_version.is_(True),
        )
        .order_by(DocumentAttachment.id.asc())
        .first()
    )
    imp_row = (
        db.query(func.max(ImportationOrder.updated_at), func.max(ImportationOrder.po_number))
        .join(ImportationItem, ImportationItem.importation_id == ImportationOrder.id)
        .filter(ImportationItem.product_id == product_id)
        .first()
    )
    orders_count = (
        db.query(func.count(func.distinct(ImportationItem.importation_id)))
        .filter(ImportationItem.product_id == product_id)
        .scalar()
        or 0
    )
    lc_row = (
        db.query(LandedCostSkuAllocation.unit_cost)
        .join(ImportationItem, ImportationItem.id == LandedCostSkuAllocation.importation_item_id)
        .join(LandedCostVersion, LandedCostVersion.id == LandedCostSkuAllocation.landed_cost_version_id)
        .filter(ImportationItem.product_id == product_id)
        .order_by(LandedCostVersion.created_at.desc())
        .first()
    )
    qty_defaults = {"qty_ordered": 0, "qty_in_transit": 0, "qty_nationalization": 0, "qty_stock": 0}
    return {
        "id": product.id,
        "sku_code": product.sku_code,
        "description": product.description,
        "ncm": product.ncm,
        "weight_kg": product.weight_kg,
        "volume_m3": product.volume_m3,
        "category": product.category,
        "lifecycle_status": product.lifecycle_status,
        "product_group": product.product_group,
        "product_subgroup": product.product_subgroup,
        "supplier_code": product.supplier_code,
        "default_supplier_id": product.default_supplier_id,
        "default_supplier_name": product.default_supplier.name if product.default_supplier else None,
        "country_of_origin": product.country_of_origin,
        "unit_of_measure": product.unit_of_measure,
        "fiscal_description": product.fiscal_description,
        "fiscal_review_required": product.fiscal_review_required,
        "launch_date": product.launch_date,
        "commercial_notes": product.commercial_notes,
        "is_active": product.is_active,
        "has_photo": has_photo,
        "photo_attachment_id": photo_att[0] if photo_att else None,
        "pending_flags": compute_pending_flags(product, has_photo=has_photo),
        "last_importation_at": imp_row[0] if imp_row else None,
        "last_importation_po": imp_row[1] if imp_row else None,
        "last_landed_cost_unit": lc_row[0] if lc_row else None,
        "orders_count": orders_count,
        **{**qty_defaults, **_aggregate_product_quantities(db, [product_id]).get(product_id, {})},
        "archived_at": product.archived_at,
        "archive_reason": product.archive_reason,
        "cancelled_at": product.cancelled_at,
        "cancellation_reason": product.cancellation_reason,
        "used_in_importations": product_used_in_importations(db, product_id),
    }


def list_product_orders(
    db: Session,
    product_id: int,
    *,
    q: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    imp_ids: set[int] = set()
    for (iid,) in db.query(ImportationItem.importation_id).filter(ImportationItem.product_id == product_id):
        imp_ids.add(iid)

    if not imp_ids:
        return [], 0

    query = (
        db.query(ImportationOrder)
        .options(joinedload(ImportationOrder.supplier))
        .filter(ImportationOrder.id.in_(imp_ids))
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(ImportationOrder.po_number.ilike(term), ImportationOrder.supplier.has(Supplier.name.ilike(term)))
        )
    if status:
        query = query.filter(ImportationOrder.current_status == status)

    total = query.count()
    orders = query.order_by(ImportationOrder.updated_at.desc()).offset(offset).limit(limit).all()

    results: list[dict] = []
    for imp in orders:
        qty = (
            db.query(func.coalesce(func.sum(ImportationItem.quantity_ordered), 0))
            .filter(ImportationItem.importation_id == imp.id, ImportationItem.product_id == product_id)
            .scalar()
        )
        lc_unit = (
            db.query(LandedCostSkuAllocation.unit_cost)
            .join(ImportationItem, ImportationItem.id == LandedCostSkuAllocation.importation_item_id)
            .join(LandedCostVersion, LandedCostVersion.id == LandedCostSkuAllocation.landed_cost_version_id)
            .filter(
                LandedCostVersion.importation_id == imp.id,
                ImportationItem.product_id == product_id,
            )
            .order_by(LandedCostVersion.version_number.desc())
            .first()
        )
        results.append(
            {
                "importation_id": imp.id,
                "po_number": imp.po_number,
                "current_status": imp.current_status,
                "supplier_name": imp.supplier.name if imp.supplier else None,
                "currency": imp.currency,
                "qty_ordered": qty,
                "landed_cost_unit": lc_unit[0] if lc_unit else None,
                "updated_at": imp.updated_at,
                "created_at": imp.created_at,
            }
        )
    return results, total


def list_product_audit(db: Session, product_id: int, limit: int = 100) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "product", AuditLog.entity_id == str(product_id))
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


def archive_product(db: Session, product: Product, *, user_id: int, reason: str) -> Product:
    product.lifecycle_status = LIFECYCLE_ARCHIVED
    product.archived_at = datetime.now(timezone.utc)
    product.archived_by_id = user_id
    product.archive_reason = reason
    return product


def restore_product(db: Session, product: Product) -> Product:
    product.lifecycle_status = LIFECYCLE_ACTIVE
    product.archived_at = None
    product.archived_by_id = None
    product.archive_reason = None
    return product


def cancel_product_record(db: Session, product: Product, *, user_id: int, reason: str) -> Product:
    product.is_active = False
    product.cancelled_at = datetime.now(timezone.utc)
    product.cancelled_by_id = user_id
    product.cancellation_reason = reason
    return product


BULK_MAX_IDS = 200


def _load_products_for_bulk(db: Session, product_ids: list[int]) -> dict[int, Product]:
    if len(product_ids) > BULK_MAX_IDS:
        raise ValueError(f"Máximo de {BULK_MAX_IDS} produtos por operação")
    rows = db.query(Product).filter(Product.id.in_(product_ids)).all()
    return {p.id: p for p in rows}


def bulk_archive_products(db: Session, product_ids: list[int], *, user_id: int, reason: str) -> BulkActionResult:
    result = BulkActionResult()
    products = _load_products_for_bulk(db, product_ids)
    for pid in product_ids:
        product = products.get(pid)
        if not product:
            result.skipped.append({"id": pid, "reason": "Produto não encontrado"})
            continue
        if not product.is_active:
            result.skipped.append({"id": pid, "reason": "Produto anulado"})
            continue
        if product.lifecycle_status == LIFECYCLE_ARCHIVED:
            result.skipped.append({"id": pid, "reason": "Já arquivado"})
            continue
        try:
            archive_product(db, product, user_id=user_id, reason=reason)
            result.succeeded.append(pid)
        except Exception as e:
            result.failed.append({"id": pid, "error": str(e)})
    return result


def bulk_restore_products(db: Session, product_ids: list[int]) -> BulkActionResult:
    result = BulkActionResult()
    products = _load_products_for_bulk(db, product_ids)
    for pid in product_ids:
        product = products.get(pid)
        if not product:
            result.skipped.append({"id": pid, "reason": "Produto não encontrado"})
            continue
        if product.lifecycle_status != LIFECYCLE_ARCHIVED:
            result.skipped.append({"id": pid, "reason": "Não está arquivado"})
            continue
        try:
            restore_product(db, product)
            result.succeeded.append(pid)
        except Exception as e:
            result.failed.append({"id": pid, "error": str(e)})
    return result


def bulk_set_lifecycle_status(
    db: Session, product_ids: list[int], status: str, *, user_id: int
) -> BulkActionResult:
    if status not in (LIFECYCLE_ACTIVE, LIFECYCLE_DISCONTINUED):
        raise ValueError("Status inválido para bulk")
    result = BulkActionResult()
    products = _load_products_for_bulk(db, product_ids)
    for pid in product_ids:
        product = products.get(pid)
        if not product:
            result.skipped.append({"id": pid, "reason": "Produto não encontrado"})
            continue
        if not product.is_active:
            result.skipped.append({"id": pid, "reason": "Produto anulado"})
            continue
        if product.lifecycle_status == LIFECYCLE_ARCHIVED:
            result.skipped.append({"id": pid, "reason": "Produto arquivado"})
            continue
        if status == LIFECYCLE_DISCONTINUED and product.lifecycle_status != LIFECYCLE_ACTIVE:
            result.skipped.append({"id": pid, "reason": "Só ativos podem ser descontinuados"})
            continue
        if status == LIFECYCLE_ACTIVE and product.lifecycle_status != LIFECYCLE_DISCONTINUED:
            result.skipped.append({"id": pid, "reason": "Só descontinuados podem ser reativados"})
            continue
        try:
            product.lifecycle_status = status
            result.succeeded.append(pid)
        except Exception as e:
            result.failed.append({"id": pid, "error": str(e)})
    return result


def bulk_cancel_products(db: Session, product_ids: list[int], *, user_id: int, reason: str) -> BulkActionResult:
    result = BulkActionResult()
    products = _load_products_for_bulk(db, product_ids)
    for pid in product_ids:
        product = products.get(pid)
        if not product:
            result.skipped.append({"id": pid, "reason": "Produto não encontrado"})
            continue
        if not product.is_active:
            result.skipped.append({"id": pid, "reason": "Já anulado"})
            continue
        try:
            cancel_product_record(db, product, user_id=user_id, reason=reason)
            result.succeeded.append(pid)
        except Exception as e:
            result.failed.append({"id": pid, "error": str(e)})
    return result


def validate_importation_products_readiness(
    db: Session,
    importation_id: int,
    context: str,
    *,
    allow_discontinued_override: bool = False,
    override_reason: str | None = None,
) -> None:
    """Valida todos os produtos mapeados nos itens de uma importação."""
    items = (
        db.query(ImportationItem)
        .filter(
            ImportationItem.importation_id == importation_id,
            ImportationItem.is_active.is_(True),
            ImportationItem.product_id.isnot(None),
        )
        .all()
    )
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue
        validate_product_for_usage(
            db,
            product,
            context,
            allow_discontinued_override=allow_discontinued_override,
            override_reason=override_reason,
        )


def list_product_cost_history(db: Session, product_id: int, limit: int = 50) -> list[dict]:
    rows = (
        db.query(
            LandedCostVersion.importation_id,
            ImportationOrder.po_number,
            LandedCostVersion.version_number,
            LandedCostVersion.version_type,
            LandedCostSkuAllocation.unit_cost,
            LandedCostVersion.created_at,
        )
        .join(LandedCostSkuAllocation, LandedCostSkuAllocation.landed_cost_version_id == LandedCostVersion.id)
        .join(ImportationItem, ImportationItem.id == LandedCostSkuAllocation.importation_item_id)
        .join(ImportationOrder, ImportationOrder.id == LandedCostVersion.importation_id)
        .filter(ImportationItem.product_id == product_id)
        .order_by(LandedCostVersion.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "importation_id": r[0],
            "po_number": r[1],
            "version_number": r[2],
            "version_type": r[3],
            "unit_cost": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]
