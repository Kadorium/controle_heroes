"""Exclusão física em cascata de ordens de importação — apenas ambiente dev/test."""

from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    BrazilCurrentAccount,
    Credit,
    CreditUsage,
    CustomsDocument,
    Discount,
    DocumentAttachment,
    ExchangeRate,
    Expense,
    HeroesDispatchPendingItem,
    HeroesImportRun,
    HeroesLegacySheetSummary,
    ImportationClosure,
    ImportationItem,
    ImportationOrder,
    Invoice,
    InvoiceItem,
    LandedCostComponent,
    LandedCostSkuAllocation,
    LandedCostVariance,
    LandedCostVersion,
    ModalChangeLog,
    Nationalization,
    NationalizationItem,
    Payment,
    QuantityDiscrepancy,
    RawImportFile,
    Reconciliation,
    ReviewQueueItem,
    Shipment,
    ShipmentItem,
    StagingImportRow,
    StatusTransitionLog,
    StockEntry,
    Tax,
)


def delete_importations_cascade(db: Session, imp_ids: list[int]) -> int:
    """Remove ordens e todos os filhos operacionais. Retorna quantidade removida."""
    if not imp_ids:
        return 0

    db.execute(
        delete(StockEntry).where(
            StockEntry.landed_cost_version_id.in_(
                select(LandedCostVersion.id).where(LandedCostVersion.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(
        delete(StockEntry).where(
            StockEntry.nationalization_id.in_(
                select(Nationalization.id).where(Nationalization.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(delete(ImportationClosure).where(ImportationClosure.importation_id.in_(imp_ids)))
    db.execute(delete(Reconciliation).where(Reconciliation.importation_id.in_(imp_ids)))
    db.execute(delete(LandedCostVariance).where(LandedCostVariance.importation_id.in_(imp_ids)))
    db.execute(
        delete(LandedCostSkuAllocation).where(
            LandedCostSkuAllocation.landed_cost_version_id.in_(
                select(LandedCostVersion.id).where(LandedCostVersion.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(
        delete(LandedCostComponent).where(
            LandedCostComponent.landed_cost_version_id.in_(
                select(LandedCostVersion.id).where(LandedCostVersion.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(delete(LandedCostVersion).where(LandedCostVersion.importation_id.in_(imp_ids)))
    db.execute(delete(QuantityDiscrepancy).where(QuantityDiscrepancy.importation_id.in_(imp_ids)))
    db.execute(
        delete(NationalizationItem).where(
            NationalizationItem.nationalization_id.in_(
                select(Nationalization.id).where(Nationalization.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(delete(Nationalization).where(Nationalization.importation_id.in_(imp_ids)))
    db.execute(delete(Tax).where(Tax.importation_id.in_(imp_ids)))
    db.execute(delete(CustomsDocument).where(CustomsDocument.importation_id.in_(imp_ids)))
    db.execute(
        delete(ShipmentItem).where(
            ShipmentItem.shipment_id.in_(
                select(Shipment.id).where(Shipment.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(
        delete(ModalChangeLog).where(
            ModalChangeLog.shipment_id.in_(
                select(Shipment.id).where(Shipment.importation_id.in_(imp_ids))
            )
        )
    )
    db.execute(delete(Shipment).where(Shipment.importation_id.in_(imp_ids)))
    db.execute(delete(Expense).where(Expense.importation_id.in_(imp_ids)))
    db.execute(delete(DocumentAttachment).where(DocumentAttachment.entity_id.in_([str(i) for i in imp_ids])))
    inv_ids_subq = select(Invoice.id).where(Invoice.importation_id.in_(imp_ids))
    pay_ids_subq = select(Payment.id).where(Payment.invoice_id.in_(inv_ids_subq))
    db.execute(
        delete(ExchangeRate).where(
            or_(
                ExchangeRate.importation_id.in_(imp_ids),
                ExchangeRate.invoice_id.in_(inv_ids_subq),
                ExchangeRate.payment_id.in_(pay_ids_subq),
            )
        )
    )
    db.execute(delete(Payment).where(Payment.invoice_id.in_(inv_ids_subq)))
    db.execute(delete(Discount).where(Discount.invoice_id.in_(inv_ids_subq)))
    db.execute(delete(CreditUsage).where(CreditUsage.importation_id.in_(imp_ids)))
    db.execute(
        delete(Credit).where(
            or_(
                Credit.origin_importation_id.in_(imp_ids),
                Credit.used_in_importation_id.in_(imp_ids),
            )
        )
    )
    db.execute(delete(BrazilCurrentAccount).where(BrazilCurrentAccount.origin_importation_id.in_(imp_ids)))
    db.execute(delete(InvoiceItem).where(InvoiceItem.invoice_id.in_(inv_ids_subq)))
    db.execute(delete(Invoice).where(Invoice.importation_id.in_(imp_ids)))
    db.execute(delete(ImportationItem).where(ImportationItem.importation_id.in_(imp_ids)))
    db.execute(
        delete(StatusTransitionLog).where(
            StatusTransitionLog.importation_id.in_([str(i) for i in imp_ids])
        )
    )
    db.execute(delete(HeroesDispatchPendingItem).where(HeroesDispatchPendingItem.importation_id.in_(imp_ids)))
    db.execute(delete(HeroesLegacySheetSummary).where(HeroesLegacySheetSummary.importation_id.in_(imp_ids)))
    db.execute(delete(HeroesImportRun).where(HeroesImportRun.importation_id.in_(imp_ids)))
    db.execute(
        delete(AuditLog).where(
            AuditLog.entity_type == "importation_order",
            AuditLog.entity_id.in_([str(i) for i in imp_ids]),
        )
    )
    db.execute(delete(ImportationOrder).where(ImportationOrder.id.in_(imp_ids)))
    return len(imp_ids)


def purge_orphan_import_artifacts(db: Session) -> dict[str, int]:
    """Remove staging, fila de revisão, runs Heroes órfãos e arquivos raw sem uso."""
    review_count = db.query(ReviewQueueItem).count()
    db.execute(delete(ReviewQueueItem))

    staging_count = db.query(StagingImportRow).count()
    db.execute(delete(StagingImportRow))

    active_imp_ids = select(ImportationOrder.id).where(ImportationOrder.is_active.is_(True))
    heroes_q = db.query(HeroesImportRun).filter(
        or_(
            HeroesImportRun.importation_id.is_(None),
            ~HeroesImportRun.importation_id.in_(active_imp_ids),
        )
    )
    heroes_count = heroes_q.count()
    heroes_q.delete(synchronize_session=False)

    db.execute(
        delete(HeroesDispatchPendingItem).where(
            ~HeroesDispatchPendingItem.importation_id.in_(active_imp_ids)
        )
    )
    db.execute(
        delete(HeroesLegacySheetSummary).where(
            ~HeroesLegacySheetSummary.importation_id.in_(active_imp_ids)
        )
    )

    used_raw_ids = select(HeroesImportRun.raw_file_id).where(HeroesImportRun.raw_file_id.isnot(None))
    raw_count = (
        db.query(RawImportFile)
        .filter(~RawImportFile.id.in_(used_raw_ids))
        .count()
    )
    db.execute(delete(RawImportFile).where(~RawImportFile.id.in_(used_raw_ids)))

    return {
        "review_queue_removed": review_count,
        "staging_rows_removed": staging_count,
        "heroes_runs_removed": heroes_count,
        "raw_files_removed": raw_count,
    }
