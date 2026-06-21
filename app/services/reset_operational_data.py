"""Limpeza segura de dados operacionais demo/teste — apenas ambiente local/dev."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, get_settings
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
    HeroesImportRun,
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
    Supplier,
    Tax,
    User,
)

RESET_ENV_VAR = "RESET_EPIC_TEST_DATA"
ALLOWED_ENVS = ("development", "dev", "local", "test")


def assert_reset_allowed() -> None:
    settings = get_settings()
    if settings.app_env.lower() not in ALLOWED_ENVS:
        raise RuntimeError(
            f"Reset operacional bloqueado em app_env={settings.app_env!r}. "
            f"Permitido apenas: {ALLOWED_ENVS}"
        )
    if os.environ.get(RESET_ENV_VAR) != "1":
        raise RuntimeError(
            f"Confirmação obrigatória: defina {RESET_ENV_VAR}=1 para executar o reset."
        )


def _run_backup_if_available() -> str | None:
    script = ROOT_DIR / "scripts" / "backup-db.ps1"
    if not script.exists():
        return None
    try:
        subprocess.run(
            ["powershell", "-File", str(script)],
            cwd=str(ROOT_DIR),
            check=False,
            capture_output=True,
            timeout=120,
        )
        return "backup attempted via backup-db.ps1"
    except Exception as e:
        return f"backup skipped: {e}"


def reset_operational_test_data(db: Session, *, skip_backup: bool = False) -> dict:
    assert_reset_allowed()
    backup_note = None if skip_backup else _run_backup_if_available()

    users_before = db.scalar(select(User.id).limit(1))
    heroes_supplier = db.scalar(
        select(Supplier.id).where(Supplier.name.ilike("%heroes%")).limit(1)
    )

    imp_ids = [r[0] for r in db.execute(select(ImportationOrder.id)).all()]

    if imp_ids:
        # Filhos profundos primeiro — stock_entries referencia landed_cost_version
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
        db.execute(
            delete(Payment).where(Payment.invoice_id.in_(inv_ids_subq))
        )
        db.execute(
            delete(Discount).where(Discount.invoice_id.in_(inv_ids_subq))
        )
        db.execute(delete(CreditUsage))
        db.execute(
            delete(InvoiceItem).where(InvoiceItem.invoice_id.in_(inv_ids_subq))
        )
        db.execute(delete(Invoice).where(Invoice.importation_id.in_(imp_ids)))
        db.execute(delete(ImportationItem).where(ImportationItem.importation_id.in_(imp_ids)))
        db.execute(
            delete(StatusTransitionLog).where(
                StatusTransitionLog.importation_id.in_([str(i) for i in imp_ids])
            )
        )
        db.execute(delete(Credit))
        db.execute(delete(BrazilCurrentAccount))
        db.execute(delete(HeroesImportRun).where(HeroesImportRun.importation_id.in_(imp_ids)))
        db.execute(delete(ImportationOrder).where(ImportationOrder.id.in_(imp_ids)))

    # Import staging (sem vínculo FK com importations)
    db.execute(delete(ReviewQueueItem))
    db.execute(delete(StagingImportRow))
    db.execute(delete(HeroesImportRun))
    db.execute(delete(RawImportFile))

    # Audit de importações removidas (dev/test)
    db.execute(delete(AuditLog).where(AuditLog.entity_type.in_((
        "importation_order", "invoice", "payment", "heroes_import_run", "raw_import_file", "staging_import_row"
    ))))

    db.commit()

    users_after = db.scalar(select(User.id).limit(1))
    heroes_after = db.scalar(select(Supplier.id).where(Supplier.name.ilike("%heroes%")).limit(1))
    imps_remaining = db.scalar(select(ImportationOrder.id).limit(1))

    return {
        "importations_removed": len(imp_ids),
        "users_preserved": users_before is not None and users_after is not None,
        "heroes_supplier_preserved": heroes_supplier is not None and heroes_after is not None,
        "importations_remaining": imps_remaining is not None,
        "backup": backup_note,
    }
