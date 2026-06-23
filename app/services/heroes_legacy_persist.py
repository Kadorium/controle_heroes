"""Persistência de dados legados Heroes no commit."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.core.enums import HEROES_XLSX_PARSER_VERSION
from app.core.parse import optional_decimal, optional_int
from app.models import HeroesDispatchPendingItem, HeroesLegacySheetSummary, ImportationItem


def persist_legacy_sheet_summary(
    db: Session,
    *,
    importation_id: int,
    run_id: int,
    sheet_name: str,
    preview: dict,
) -> HeroesLegacySheetSummary | None:
    legacy = preview.get("legacy_sheet_summary") or {}
    amount = optional_decimal(legacy.get("versato_amount"))
    if amount is None:
        return None
    row = HeroesLegacySheetSummary(
        importation_id=importation_id,
        heroes_import_run_id=run_id,
        sheet_name=sheet_name,
        versato_amount=amount,
        versato_currency=legacy.get("versato_currency") or preview.get("currency") or "EUR",
        versato_source_row=legacy.get("versato_source_row"),
        versato_source_cell=legacy.get("versato_source_cell"),
        versato_raw_value=legacy.get("versato_raw_value"),
        versato_confidence=legacy.get("versato_confidence"),
        parser_version=preview.get("parser_version") or HEROES_XLSX_PARSER_VERSION,
        is_active=True,
    )
    db.add(row)
    return row


def persist_dispatch_pending_items(
    db: Session,
    *,
    importation_id: int,
    run_id: int,
    sheet_name: str,
    preview: dict,
    product_id_by_name: dict[str, int],
) -> list[HeroesDispatchPendingItem]:
    currency = preview.get("currency") or "EUR"
    rows: list[HeroesDispatchPendingItem] = []
    for da in preview.get("da_spedire") or []:
        name = da.get("product_name_raw")
        if not name:
            continue
        item = HeroesDispatchPendingItem(
            importation_id=importation_id,
            heroes_import_run_id=run_id,
            product_name_raw=name,
            product_id=product_id_by_name.get(name),
            product_category_suggested=da.get("suggested_category"),
            quantity_to_dispatch=optional_int(da.get("quantity_to_dispatch")),
            price_listino=optional_decimal(da.get("price_listino")),
            price_fattura=optional_decimal(da.get("invoice_price")),
            discount_unit=optional_decimal(da.get("discount")),
            acconto_amount=optional_decimal(da.get("acconto")),
            credit_remaining=optional_decimal(da.get("credit_remaining")),
            currency=currency,
            source_sheet=sheet_name,
            source_row=da.get("row_number"),
            parser_confidence=da.get("category_confidence"),
            needs_review=bool(da.get("category_review")),
            raw_values=da.get("raw_values"),
            is_active=True,
        )
        db.add(item)
        rows.append(item)
    return rows


def _product_id_by_name_for_importation(db: Session, importation_id: int) -> dict[str, int]:
    items = (
        db.query(ImportationItem)
        .options(joinedload(ImportationItem.product))
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    out: dict[str, int] = {}
    for it in items:
        if not it.product_id:
            continue
        for key in (it.description, it.product.description if it.product else None, it.product.sku_code if it.product else None):
            if key:
                out[key] = it.product_id
    return out


def ensure_heroes_legacy_persisted(
    db: Session,
    *,
    importation_id: int,
    run_id: int,
    sheet_name: str,
    preview: dict,
) -> None:
    """Preenche versato/DA SPEDIRE se ausentes — recommit idempotente pós-5.3."""
    has_legacy = (
        db.query(HeroesLegacySheetSummary.id)
        .filter(
            HeroesLegacySheetSummary.importation_id == importation_id,
            HeroesLegacySheetSummary.is_active.is_(True),
        )
        .first()
    )
    if not has_legacy:
        persist_legacy_sheet_summary(
            db,
            importation_id=importation_id,
            run_id=run_id,
            sheet_name=sheet_name,
            preview=preview,
        )

    dispatch_count = (
        db.query(HeroesDispatchPendingItem.id)
        .filter(
            HeroesDispatchPendingItem.importation_id == importation_id,
            HeroesDispatchPendingItem.is_active.is_(True),
        )
        .count()
    )
    if dispatch_count == 0 and preview.get("da_spedire"):
        persist_dispatch_pending_items(
            db,
            importation_id=importation_id,
            run_id=run_id,
            sheet_name=sheet_name,
            preview=preview,
            product_id_by_name=_product_id_by_name_for_importation(db, importation_id),
        )
