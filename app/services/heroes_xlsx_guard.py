"""Guards preview/commit Heroes XLSX — raw ATTACHED e revisão pendente."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import HeroesImportRunStatus
from app.models import HeroesImportRun
from app.services.heroes_xlsx_staging import count_open_sku_reviews_for_run


class AttachedRawFileError(ValueError):
    """Arquivo raw vinculado a ordem manual — fluxo standalone bloqueado."""


def find_attached_run_for_raw_file(
    db: Session,
    raw_file_id: int,
) -> HeroesImportRun | None:
    return (
        db.query(HeroesImportRun)
        .filter(
            HeroesImportRun.raw_file_id == raw_file_id,
            HeroesImportRun.importation_id.isnot(None),
            HeroesImportRun.idempotency_key.like("attached:%"),
            HeroesImportRun.status.in_(
                [
                    HeroesImportRunStatus.ATTACHED.value,
                    HeroesImportRunStatus.PREVIEW.value,
                    HeroesImportRunStatus.REVIEW_REQUIRED.value,
                ]
            ),
        )
        .first()
    )


def assert_raw_file_not_attached_elsewhere(
    db: Session,
    raw_file_id: int,
    *,
    allow_importation_id: int | None = None,
) -> None:
    run = find_attached_run_for_raw_file(db, raw_file_id)
    if not run:
        return
    if allow_importation_id is not None and run.importation_id == allow_importation_id:
        return
    raise AttachedRawFileError(
        f"Planilha vinculada à ordem #{run.importation_id}. "
        "Use o preview na Central da ordem."
    )


def assert_heroes_commit_allowed(
    db: Session,
    run: HeroesImportRun,
    preview: dict,
) -> str | None:
    """Bloqueia commit merge enquanto houver SKU pendente na fila."""
    if not run.raw_file_id:
        return None
    open_count = count_open_sku_reviews_for_run(db, run.id, run.raw_file_id)
    if open_count > 0:
        return "Vincule os SKUs antes de importar."
    if preview.get("sku_review_pending"):
        return "Vincule os SKUs antes de importar."
    return None
