"""Ciclo de vida da ordem de importação — anulação e liberação de PO."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import HeroesImportRunStatus
from app.models import HeroesImportRun, ImportationOrder


def release_po_number_on_cancel(imp: ImportationOrder) -> str:
    """Renomeia po_number para liberar UNIQUE e permitir nova ordem com o mesmo PO."""
    suffix = f"~anulado-{imp.id}"
    if imp.po_number.endswith(suffix):
        return imp.po_number
    base = imp.po_number
    max_base_len = 64 - len(suffix)
    if len(base) > max_base_len:
        base = base[:max_base_len]
    imp.po_number = f"{base}{suffix}"
    return imp.po_number


def supersede_heroes_run(run: HeroesImportRun) -> None:
    """Marca run como substituído e libera idempotency_key para reimportação."""
    if run.status == HeroesImportRunStatus.SUPERSEDED.value:
        return
    run.status = HeroesImportRunStatus.SUPERSEDED.value
    suffix = f"~superseded-{run.id}"
    max_base = 128 - len(suffix)
    key = run.idempotency_key
    if len(key) > max_base:
        key = key[:max_base]
    if not key.endswith(suffix):
        run.idempotency_key = f"{key}{suffix}"


def heroes_run_targets_active_importation(db: Session, run: HeroesImportRun) -> bool:
    if not run.importation_id:
        return False
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == run.importation_id).first()
    return imp is not None and imp.is_active


def is_terminal_heroes_import_run(db: Session, run: HeroesImportRun) -> bool:
    """Run encerrado com ordem ativa — usado só para idempotência de commit, não para pular preview."""
    if run.status == HeroesImportRunStatus.SUPERSEDED.value:
        return False
    if run.status == HeroesImportRunStatus.ATTACHED.value:
        return False
    if run.status == HeroesImportRunStatus.COMMITTED.value:
        return heroes_run_targets_active_importation(db, run)
    if run.importation_id:
        return heroes_run_targets_active_importation(db, run)
    return False


def reopen_stale_heroes_run(run: HeroesImportRun) -> bool:
    """Desfaz vínculo de commit com ordem inativa — permite nova importação da mesma sheet."""
    if run.status != HeroesImportRunStatus.COMMITTED.value:
        return False
    run.status = HeroesImportRunStatus.PREVIEW.value
    run.importation_id = None
    run.committed_at = None
    run.normalized_json = None
    return True


def release_heroes_runs_on_cancel(db: Session, importation_id: int) -> int:
    """Encerra vínculos Heroes (abertos ou commitados) para liberar reimportação da sheet."""
    runs = (
        db.query(HeroesImportRun)
        .filter(
            HeroesImportRun.importation_id == importation_id,
            HeroesImportRun.status != HeroesImportRunStatus.SUPERSEDED.value,
        )
        .all()
    )
    for run in runs:
        supersede_heroes_run(run)
    return len(runs)
