"""Política de conflito Heroes — sheet name vs conteúdo interno."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import HeroesImportRunStatus
from app.models import HeroesImportRun, ImportationOrder


def heroes_po_number(order_number: str) -> str:
    return f"HEROES-{order_number}"


def order_exists_for_heroes(db: Session, order_number: str) -> ImportationOrder | None:
    return (
        db.query(ImportationOrder)
        .filter(ImportationOrder.po_number == heroes_po_number(order_number), ImportationOrder.is_active.is_(True))
        .first()
    )


def evaluate_preview_review(preview: dict, *, confirmed_order_number: str | None) -> tuple[bool, str | None]:
    """Retorna (review_required, block_reason)."""
    if not preview.get("order_number_divergence"):
        return False, None
    if not confirmed_order_number:
        return True, (
            f"Divergência: sheet sugere {preview.get('order_number_from_sheet_name')}, "
            f"conteúdo indica {preview.get('order_number_from_content')}. "
            "Informe confirmed_order_number antes do commit."
        )
    return False, None


def validate_commit_allowed(
    db: Session,
    preview: dict,
    *,
    confirmed_order_number: str | None,
    confirm_import: bool,
    confirm_sheet_match: bool,
) -> str:
    if not confirm_import:
        return "Confirme a importação explicitamente (confirm_import=true)"
    if not confirm_sheet_match:
        return "Confirme que a sheet selecionada está correta (confirm_sheet_match=true)"

    order_number = (
        confirmed_order_number
        or preview.get("confirmed_order_number")
        or preview.get("order_number")
    )
    if not order_number:
        return "Número da ordem não detectado — informe confirmed_order_number"

    if preview.get("order_number_divergence") and not confirmed_order_number:
        return (
            "Divergência entre nome da sheet e conteúdo — informe confirmed_order_number antes do commit"
        )

    existing = order_exists_for_heroes(db, order_number)
    if existing:
        return (
            f"Ordem {heroes_po_number(order_number)} já existe (id={existing.id}). "
            "Compare diferenças, importe como staging ou cancele."
        )

    if preview.get("order_number_divergence"):
        content = preview.get("order_number_from_content")
        sheet = preview.get("order_number_from_sheet_name")
        if content and confirmed_order_number == content and sheet and sheet != content:
            alt = order_exists_for_heroes(db, sheet)
            if alt:
                return (
                    f"Risco de duplicação: conteúdo {content} confirmado mas sheet {sheet} "
                    f"já tem ordem {heroes_po_number(sheet)} (id={alt.id})."
                )

    return ""


def apply_run_review_state(
    run: HeroesImportRun,
    preview: dict,
    *,
    confirmed_order_number: str | None,
) -> None:
    review, _ = evaluate_preview_review(preview, confirmed_order_number=confirmed_order_number)
    run.review_required = review
    run.confirmed_order_number = confirmed_order_number
    if review:
        run.status = HeroesImportRunStatus.REVIEW_REQUIRED.value
    elif run.status == HeroesImportRunStatus.REVIEW_REQUIRED.value:
        run.status = HeroesImportRunStatus.PREVIEW.value
