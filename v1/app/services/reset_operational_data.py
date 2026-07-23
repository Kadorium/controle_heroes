"""Limpeza segura de dados operacionais demo/teste — apenas ambiente local/dev."""

from __future__ import annotations

import os
import subprocess

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, get_settings
from app.models import (
    AuditLog,
    BrazilCurrentAccount,
    Credit,
    CreditUsage,
    HeroesDispatchPendingItem,
    HeroesImportRun,
    HeroesLegacySheetSummary,
    ImportationOrder,
    RawImportFile,
    ReviewQueueItem,
    StagingImportRow,
    Supplier,
    User,
)
from app.services.importation_purge import delete_importations_cascade, purge_orphan_import_artifacts

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
    delete_importations_cascade(db, imp_ids)

    orphan = purge_orphan_import_artifacts(db)
    db.execute(delete(CreditUsage))
    db.execute(delete(Credit))
    db.execute(delete(BrazilCurrentAccount))

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
        **orphan,
    }
