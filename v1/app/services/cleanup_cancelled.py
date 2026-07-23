"""Resumo e exclusão permanente de dados anulados / lixo de teste."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ReviewQueueStatus
from app.models import (
    HeroesImportRun,
    ImportationOrder,
    Product,
    RawImportFile,
    ReviewQueueItem,
    StagingImportRow,
    Supplier,
)
from app.services.catalog_purge import delete_cancelled_products, delete_cancelled_suppliers
from app.services.importation_purge import delete_importations_cascade, purge_orphan_import_artifacts
from app.services.reset_operational_data import RESET_ENV_VAR, assert_reset_allowed


def _purge_hint() -> tuple[bool, str | None]:
    try:
        assert_reset_allowed()
        return True, None
    except RuntimeError as exc:
        return False, str(exc)


def build_cancelled_summary(db: Session) -> dict:
    suppliers = {s.id: s.name for s in db.query(Supplier).all()}
    cancelled_imps = (
        db.query(ImportationOrder)
        .filter(ImportationOrder.is_active.is_(False))
        .order_by(ImportationOrder.cancelled_at.desc().nullslast(), ImportationOrder.id.desc())
        .all()
    )
    cancelled_products = (
        db.query(Product)
        .filter(Product.is_active.is_(False))
        .order_by(Product.cancelled_at.desc().nullslast(), Product.id.desc())
        .all()
    )
    cancelled_suppliers = (
        db.query(Supplier)
        .filter(Supplier.is_active.is_(False))
        .order_by(Supplier.cancelled_at.desc().nullslast(), Supplier.id.desc())
        .all()
    )
    active_imp_ids = select(ImportationOrder.id).where(ImportationOrder.is_active.is_(True))
    orphan_heroes = (
        db.query(HeroesImportRun)
        .filter(
            (HeroesImportRun.importation_id.is_(None))
            | (~HeroesImportRun.importation_id.in_(active_imp_ids))
        )
        .count()
    )
    used_raw_ids = select(HeroesImportRun.raw_file_id).where(HeroesImportRun.raw_file_id.isnot(None))
    orphan_raw = db.query(RawImportFile).filter(~RawImportFile.id.in_(used_raw_ids)).count()
    purge_allowed, purge_block_reason = _purge_hint()

    return {
        "purge_allowed": purge_allowed,
        "purge_block_reason": purge_block_reason,
        "purge_env_var": RESET_ENV_VAR,
        "importations": [
            {
                "id": imp.id,
                "po_number": imp.po_number,
                "supplier_name": suppliers.get(imp.supplier_id),
                "current_status": imp.current_status,
                "cancelled_at": imp.cancelled_at,
                "cancellation_reason": imp.cancellation_reason,
                "created_at": imp.created_at,
            }
            for imp in cancelled_imps
        ],
        "products": [
            {
                "id": p.id,
                "sku_code": p.sku_code,
                "description": p.description,
                "cancelled_at": p.cancelled_at,
                "cancellation_reason": p.cancellation_reason,
            }
            for p in cancelled_products
        ],
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "country": s.country,
                "cancelled_at": s.cancelled_at,
                "cancellation_reason": s.cancellation_reason,
            }
            for s in cancelled_suppliers
        ],
        "counts": {
            "importations_cancelled": len(cancelled_imps),
            "importations_active": db.query(ImportationOrder).filter(ImportationOrder.is_active.is_(True)).count(),
            "products_cancelled": len(cancelled_products),
            "suppliers_cancelled": len(cancelled_suppliers),
            "heroes_runs_orphan": orphan_heroes,
            "staging_rows": db.query(StagingImportRow).count(),
            "review_queue_open": db.query(ReviewQueueItem)
            .filter(ReviewQueueItem.status == ReviewQueueStatus.OPEN.value)
            .count(),
            "raw_files_orphan": orphan_raw,
        },
    }


def purge_cancelled_data(
    db: Session,
    *,
    importation_ids: list[int] | None = None,
    product_ids: list[int] | None = None,
    supplier_ids: list[int] | None = None,
    purge_all_cancelled_importations: bool = False,
    purge_all_cancelled_products: bool = False,
    purge_all_cancelled_suppliers: bool = False,
    purge_orphan_artifacts: bool = False,
) -> dict:
    assert_reset_allowed()

    imp_targets: list[int] = []
    if purge_all_cancelled_importations:
        imp_targets = [
            r[0]
            for r in db.execute(
                select(ImportationOrder.id).where(ImportationOrder.is_active.is_(False))
            ).all()
        ]
    elif importation_ids:
        rows = (
            db.query(ImportationOrder)
            .filter(
                ImportationOrder.id.in_(importation_ids),
                ImportationOrder.is_active.is_(False),
            )
            .all()
        )
        found = {r.id for r in rows}
        missing = [i for i in importation_ids if i not in found]
        if missing:
            raise ValueError(
                f"Só é possível excluir ordens anuladas. IDs inválidos ou ainda ativos: {missing}"
            )
        imp_targets = list(importation_ids)

    product_targets: list[int] = []
    if purge_all_cancelled_products:
        product_targets = [
            r[0]
            for r in db.execute(select(Product.id).where(Product.is_active.is_(False))).all()
        ]
    elif product_ids:
        product_targets = list(product_ids)

    supplier_targets: list[int] = []
    if purge_all_cancelled_suppliers:
        supplier_targets = [
            r[0]
            for r in db.execute(select(Supplier.id).where(Supplier.is_active.is_(False))).all()
        ]
    elif supplier_ids:
        supplier_targets = list(supplier_ids)

    importations_removed = delete_importations_cascade(db, imp_targets)
    products_removed = delete_cancelled_products(db, product_targets)
    suppliers_removed = delete_cancelled_suppliers(db, supplier_targets)

    orphan_stats: dict[str, int] = {}
    if purge_orphan_artifacts:
        orphan_stats = purge_orphan_import_artifacts(db)

    db.commit()
    return {
        "importations_removed": importations_removed,
        "products_removed": products_removed,
        "suppliers_removed": suppliers_removed,
        **orphan_stats,
    }
