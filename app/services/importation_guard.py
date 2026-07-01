from sqlalchemy.orm import Session

from app.core.enums import HeroesImportRunStatus
from app.models import HeroesImportRun, HeroesLegacySheetSummary, ImportationOrder

HEROES_LOCKED_ITEM_FIELDS = frozenset({
    "quantity_ordered",
    "unit_price_foreign",
    "discount_amount_foreign",
})


class ImportationLockedError(Exception):
    pass


def is_importation_locked(imp: ImportationOrder) -> bool:
    return imp.current_status == "CLOSED"


def assert_importation_editable(imp: ImportationOrder) -> None:
    if is_importation_locked(imp):
        raise ImportationLockedError("Importação fechada — reabra antes de editar")


def assert_manual_item_fields_allowed(
    db: Session,
    importation_id: int,
    changes: dict,
) -> None:
    """Bloqueia edição direta de qty/preço em ordens Heroes (use override Itália)."""
    if not HEROES_LOCKED_ITEM_FIELDS.intersection(changes):
        return
    legacy = (
        db.query(HeroesLegacySheetSummary)
        .filter(
            HeroesLegacySheetSummary.importation_id == importation_id,
            HeroesLegacySheetSummary.is_active.is_(True),
        )
        .first()
    )
    if legacy:
        raise ValueError(
            "Ordem importada via Heroes — ajuste quantidade/preço via override Itália ou revisão da planilha."
        )
    run = (
        db.query(HeroesImportRun)
        .filter(
            HeroesImportRun.importation_id == importation_id,
            HeroesImportRun.status == HeroesImportRunStatus.COMMITTED.value,
        )
        .first()
    )
    if run:
        raise ValueError(
            "Ordem vinculada a import Heroes commitado — use override Itália para qty/preço."
        )
