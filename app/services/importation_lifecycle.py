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


def release_heroes_runs_on_cancel(db: Session, importation_id: int) -> int:
    """Encerra vínculos Heroes abertos para liberar a planilha bruta."""
    runs = (
        db.query(HeroesImportRun)
        .filter(
            HeroesImportRun.importation_id == importation_id,
            HeroesImportRun.idempotency_key.like(f"attached:{importation_id}:%"),
            HeroesImportRun.status.in_(
                [
                    HeroesImportRunStatus.ATTACHED.value,
                    HeroesImportRunStatus.PREVIEW.value,
                    HeroesImportRunStatus.REVIEW_REQUIRED.value,
                ]
            ),
        )
        .all()
    )
    for run in runs:
        run.status = HeroesImportRunStatus.SUPERSEDED.value
    return len(runs)
