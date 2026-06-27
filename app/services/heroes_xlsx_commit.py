"""Commit de preview Heroes XLSX para dados oficiais."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.config import DEFAULT_IMPORT_CURRENCY
from app.core.enums import HeroesImportRunStatus, InvoiceType, ReviewQueueStatus, StagingRowStatus
from app.core.parse import optional_decimal, optional_int
from app.models import (
    HeroesImportRun,
    ImportationItem,
    ImportationOrder,
    Invoice,
    InvoiceItem,
    Payment,
    Product,
    ReviewQueueItem,
    StagingImportRow,
    Supplier,
)
from app.services.auth import write_audit_log
from app.services.heroes_conflict import validate_commit_allowed
from app.services.heroes_invoice_blocks import get_invoice_blocks_for_preview
from app.services.heroes_legacy_persist import (
    ensure_heroes_legacy_persisted,
    persist_dispatch_pending_items,
    persist_legacy_sheet_summary,
)
from app.services.heroes_order_format_v1 import preview_to_canonical
from app.services.heroes_product_match import match_product
from app.services.heroes_xlsx_staging import find_staging_for_alias
from app.services.heroes_xlsx_guard import assert_heroes_commit_allowed
from app.services.heroes_xlsx_staging import count_open_sku_reviews_for_run
from app.services.product_category import suggest_product_category


def _parse_date(val: str | None):
    if not val:
        return None
    from datetime import date as date_cls
    try:
        return date_cls.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def _slug_sku(name: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.upper()).strip("-")
    return (base[:60] or "PROD-UNK")


def _get_heroes_supplier(db: Session) -> Supplier:
    for name in ("Heroes Itália", "Heroes Italia", "Heroes Demo CN", "Heroes Import"):
        s = db.query(Supplier).filter(Supplier.name == name, Supplier.is_active.is_(True)).first()
        if s:
            return s
    s = db.query(Supplier).filter(Supplier.is_active.is_(True)).first()
    if not s:
        s = Supplier(name="Heroes Itália", country="IT", currency_default=DEFAULT_IMPORT_CURRENCY)
        db.add(s)
        db.flush()
    return s


def _resolve_category(name: str, overrides: dict[str, str] | None) -> str:
    if overrides and name in overrides:
        return overrides[name]
    cat, _, _ = suggest_product_category(name)
    return cat


def _find_staging_for_row(
    db: Session,
    *,
    raw_file_id: int,
    run_id: int,
    product_name_raw: str,
    sheet_row: int | None,
) -> StagingImportRow | None:
    return find_staging_for_alias(
        db,
        raw_file_id=raw_file_id,
        run_id=run_id,
        product_name_raw=product_name_raw,
        sheet_row=sheet_row,
    )


def _enqueue_merge_conflict(
    db: Session,
    *,
    raw_file_id: int,
    run_id: int,
    product_name_raw: str,
    sheet_row: int | None,
    reason: str,
) -> None:
    row_number = sheet_row or 0
    parsed = {
        "issue_type": "MERGE_CONFLICT",
        "product_name_raw": product_name_raw,
        "sheet_row": sheet_row,
        "heroes_run_id": run_id,
        "source": "heroes_xlsx",
        "conflict_reason": reason,
    }
    staging = StagingImportRow(
        raw_file_id=raw_file_id,
        row_number=row_number,
        parsed_data_json=parsed,
        status=StagingRowStatus.PENDING_REVIEW.value,
        review_reason=reason,
    )
    db.add(staging)
    db.flush()
    existing = (
        db.query(ReviewQueueItem)
        .filter(
            ReviewQueueItem.staging_row_id == staging.id,
            ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
        )
        .first()
    )
    if not existing:
        db.add(
            ReviewQueueItem(
                staging_row_id=staging.id,
                status=ReviewQueueStatus.OPEN.value,
                reason=reason,
                priority=9,
            )
        )


def _merge_preview_into_importation(
    db: Session,
    *,
    imp: ImportationOrder,
    run: HeroesImportRun,
    preview: dict,
    user_id: int | None,
    category_overrides: dict[str, str] | None,
    merge_mode: bool,
    resolve_product: Callable[[str, int | None], Product],
) -> list[str]:
    """Aplica invoice_blocks à ordem — retorna warnings (ex.: fatura já existente)."""
    warnings: list[str] = []
    invoice_blocks = get_invoice_blocks_for_preview(preview)
    invoice_cache: dict[str, Invoice] = {}
    item_by_product_id: dict[int, ImportationItem] = {}
    product_id_by_name: dict[str, int] = {}

    for existing in (
        db.query(ImportationItem)
        .filter(
            ImportationItem.importation_id == imp.id,
            ImportationItem.is_active.is_(True),
        )
        .all()
    ):
        if existing.product_id:
            item_by_product_id[existing.product_id] = existing

    def get_invoice(inv_num: str, invoice_date: str | None, *, pre_existed: bool) -> Invoice:
        if inv_num in invoice_cache:
            return invoice_cache[inv_num]
        existing = (
            db.query(Invoice)
            .filter(
                Invoice.importation_id == imp.id,
                Invoice.invoice_number == str(inv_num),
                Invoice.is_active.is_(True),
            )
            .first()
        )
        if existing:
            if merge_mode and pre_existed:
                warnings.append(
                    f"Fatura {inv_num} já existe na ordem — reutilizando (id={existing.id})."
                )
            inv = existing
        else:
            inv = Invoice(
                importation_id=imp.id,
                invoice_type=InvoiceType.PROFORMA.value,
                invoice_number=str(inv_num),
                invoice_date=_parse_date(invoice_date),
                currency=DEFAULT_IMPORT_CURRENCY,
                amount=None,
            )
            db.add(inv)
            db.flush()
        invoice_cache[inv_num] = inv
        return inv

    # Loop 1 — financeiro
    for block in invoice_blocks:
        inv_num = block.get("invoice_number") or "SEM-NUMERO"
        pre_existed = (
            db.query(Invoice)
            .filter(
                Invoice.importation_id == imp.id,
                Invoice.invoice_number == str(inv_num),
                Invoice.is_active.is_(True),
            )
            .first()
            is not None
        )
        inv = get_invoice(inv_num, block.get("invoice_date"), pre_existed=pre_existed)
        pay_date = _parse_date(block.get("invoice_date"))
        for pay in block.get("acconto_payments") or []:
            acconto = optional_decimal(pay.get("amount"))
            if acconto is None or acconto <= 0:
                continue
            ref = pay.get("receipt_reference") or f"ACCONTO-{inv_num}"
            dup = (
                db.query(Payment)
                .filter(
                    Payment.invoice_id == inv.id,
                    Payment.receipt_reference == ref,
                    Payment.is_active.is_(True),
                )
                .first()
            )
            if dup:
                continue
            db.add(
                Payment(
                    invoice_id=inv.id,
                    payment_type="ADVANCE",
                    amount_foreign=acconto,
                    currency_foreign=DEFAULT_IMPORT_CURRENCY,
                    payment_date=pay_date,
                    receipt_reference=ref,
                )
            )

    # Loop 2 — itens (sem Payment)
    raw_file_id = run.raw_file_id
    for block in invoice_blocks:
        inv_num = block.get("invoice_number") or "SEM-NUMERO"
        inv = invoice_cache.get(inv_num) or get_invoice(
            inv_num, block.get("invoice_date"), pre_existed=False
        )
        for row in block.get("items") or []:
            name = row.get("product_name_raw")
            if not name:
                continue
            sheet_row = row.get("row_number")
            prod = resolve_product(name, sheet_row)
            product_id_by_name[name] = prod.id
            qty = optional_int(row.get("item_quantity"))
            db.add(
                InvoiceItem(
                    invoice_id=inv.id,
                    product_id=prod.id,
                    quantity=qty,
                    unit_price=None,
                    amount=None,
                )
            )
            existing_item = item_by_product_id.get(prod.id)
            if existing_item is None:
                new_item = ImportationItem(
                    importation_id=imp.id,
                    product_id=prod.id,
                    supplier_sku=prod.sku_code,
                    description=name,
                    quantity_ordered=qty,
                )
                db.add(new_item)
                item_by_product_id[prod.id] = new_item
            elif qty is not None:
                desc = (existing_item.description or "").strip().lower()
                if desc and desc != name.strip().lower() and merge_mode and raw_file_id:
                    _enqueue_merge_conflict(
                        db,
                        raw_file_id=raw_file_id,
                        run_id=run.id,
                        product_name_raw=name,
                        sheet_row=sheet_row,
                        reason=(
                            f"Descrição divergente para product_id={prod.id}: "
                            f"«{existing_item.description}» vs «{name}»"
                        ),
                    )
                cur = existing_item.quantity_ordered
                existing_item.quantity_ordered = (cur or 0) + qty

    for da in preview.get("da_spedire") or []:
        name = da.get("product_name_raw")
        if not name:
            continue
        prod = resolve_product(name, da.get("row_number"))
        product_id_by_name[name] = prod.id
        qty = optional_int(da.get("quantity_to_dispatch"))
        existing_item = item_by_product_id.get(prod.id)
        if existing_item is None:
            new_item = ImportationItem(
                importation_id=imp.id,
                product_id=prod.id,
                supplier_sku=prod.sku_code,
                description=name,
                quantity_ordered=qty,
            )
            db.add(new_item)
            item_by_product_id[prod.id] = new_item
        elif qty is not None:
            cur = existing_item.quantity_ordered
            existing_item.quantity_ordered = max(cur or 0, qty)

    persist_legacy_sheet_summary(
        db,
        importation_id=imp.id,
        run_id=run.id,
        sheet_name=run.sheet_name,
        preview=preview,
    )
    persist_dispatch_pending_items(
        db,
        importation_id=imp.id,
        run_id=run.id,
        sheet_name=run.sheet_name,
        preview=preview,
        product_id_by_name=product_id_by_name,
    )
    preview["merge_warnings"] = warnings
    return warnings


def commit_merge_heroes_run(
    db: Session,
    run_id: int,
    *,
    user_id: int | None,
    category_overrides: dict[str, str] | None = None,
    confirm_import: bool = False,
    confirm_sheet_match: bool = False,
) -> ImportationOrder:
    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == run_id).first()
    if not run:
        raise ValueError("Import run não encontrado")
    if not run.importation_id:
        raise ValueError("Run não vinculado a ordem manual")
    if run.status == HeroesImportRunStatus.COMMITTED.value:
        imp = db.query(ImportationOrder).filter(ImportationOrder.id == run.importation_id).first()
        if not imp:
            raise ValueError("Run já commitado mas ordem não encontrada")
        return imp
    if not confirm_import or not confirm_sheet_match:
        raise ValueError("Confirme importação e sheet (confirm_import + confirm_sheet_match)")

    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == run.importation_id,
        ImportationOrder.is_active.is_(True),
    ).first()
    if not imp:
        raise ValueError("Ordem vinculada não encontrada")

    preview = run.preview_json or {}
    if preview.get("errors"):
        raise ValueError("Preview contém erros — corrija antes de importar")
    if run.status not in (
        HeroesImportRunStatus.PREVIEW.value,
        HeroesImportRunStatus.REVIEW_REQUIRED.value,
    ):
        raise ValueError("Execute o preview da planilha antes do commit.")

    guard = assert_heroes_commit_allowed(db, run, preview)
    if guard:
        raise ValueError(guard)

    def resolve_merge_product(name: str, sheet_row: int | None) -> Product:
        matched = match_product(db, name)
        if matched:
            return matched
        if not run.raw_file_id:
            raise ValueError(f"SKU não resolvido: {name}. Vincule os SKUs antes de importar.")
        staging = _find_staging_for_row(
            db,
            raw_file_id=run.raw_file_id,
            run_id=run.id,
            product_name_raw=name,
            sheet_row=sheet_row,
        )
        resolved_id = (staging.parsed_data_json or {}).get("resolved_product_id") if staging else None
        if staging and staging.status == StagingRowStatus.APPROVED.value and resolved_id:
            prod = db.query(Product).filter(Product.id == resolved_id).first()
            if prod:
                return prod
        raise ValueError(f"SKU não resolvido: {name}. Vincule os SKUs antes de importar.")

    _merge_preview_into_importation(
        db,
        imp=imp,
        run=run,
        preview=preview,
        user_id=user_id,
        category_overrides=category_overrides,
        merge_mode=True,
        resolve_product=resolve_merge_product,
    )
    run.preview_json = preview
    flag_modified(run, "preview_json")

    canonical = preview_to_canonical(preview, source_file=run.original_filename)
    run.status = HeroesImportRunStatus.COMMITTED.value
    run.committed_at = datetime.now(timezone.utc)
    run.review_required = False
    run.normalized_json = canonical

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="heroes_import_run",
        entity_id=str(run.id),
        action="commit_merge",
        new_value=str(imp.id),
    )
    db.commit()
    db.refresh(imp)
    return imp


def commit_heroes_import_run(
    db: Session,
    run_id: int,
    *,
    user_id: int | None,
    category_overrides: dict[str, str] | None = None,
    confirmed_order_number: str | None = None,
    confirm_sheet_match: bool = False,
    confirm_import: bool = False,
) -> ImportationOrder:
    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == run_id).first()
    if not run:
        raise ValueError("Import run não encontrado")

    preview = run.preview_json or {}

    if run.importation_id and run.idempotency_key.startswith("attached:"):
        return commit_merge_heroes_run(
            db,
            run_id,
            user_id=user_id,
            category_overrides=category_overrides,
            confirm_import=confirm_import,
            confirm_sheet_match=confirm_sheet_match,
        )

    if run.status == HeroesImportRunStatus.COMMITTED.value:
        existing = db.query(ImportationOrder).filter(ImportationOrder.id == run.importation_id).first()
        if existing:
            ensure_heroes_legacy_persisted(
                db,
                importation_id=existing.id,
                run_id=run.id,
                sheet_name=run.sheet_name,
                preview=preview,
            )
            db.commit()
            db.refresh(existing)
            return existing
        raise ValueError("Run já commitado mas ordem não encontrada")

    if preview.get("errors"):
        raise ValueError("Preview contém erros — corrija antes de importar")

    guard = assert_heroes_commit_allowed(db, run, preview)
    if guard:
        raise ValueError(guard)

    block = validate_commit_allowed(
        db,
        preview,
        confirmed_order_number=confirmed_order_number,
        confirm_import=confirm_import,
        confirm_sheet_match=confirm_sheet_match,
    )
    if block:
        raise ValueError(block)

    order_number = (
        confirmed_order_number
        or preview.get("confirmed_order_number")
        or preview.get("order_number")
        or run.order_number
    )

    supplier = _get_heroes_supplier(db)
    imp = ImportationOrder(
        po_number=f"HEROES-{order_number}",
        supplier_id=supplier.id,
        currency=DEFAULT_IMPORT_CURRENCY,
        incoterm="FOB",
        current_status="PROFORMA_RECEIVED",
        created_by_id=user_id,
    )
    db.add(imp)
    db.flush()

    product_cache: dict[str, Product] = {}

    def get_or_create_product(name: str) -> Product:
        if name in product_cache:
            return product_cache[name]
        sku = _slug_sku(name)
        prod = db.query(Product).filter(Product.sku_code == sku).first()
        cat = _resolve_category(name, category_overrides)
        if not prod:
            prod = Product(sku_code=sku, description=name, category=cat)
            db.add(prod)
            db.flush()
        elif category_overrides and name in category_overrides:
            prod.category = category_overrides[name]
        product_cache[name] = prod
        return prod

    _merge_preview_into_importation(
        db,
        imp=imp,
        run=run,
        preview=preview,
        user_id=user_id,
        category_overrides=category_overrides,
        merge_mode=False,
        resolve_product=lambda name, _row: get_or_create_product(name),
    )

    canonical = preview_to_canonical(preview, source_file=run.original_filename)
    run.status = HeroesImportRunStatus.COMMITTED.value
    run.importation_id = imp.id
    run.committed_at = datetime.now(timezone.utc)
    run.confirmed_order_number = order_number
    run.review_required = False
    run.normalized_json = canonical

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="heroes_import_run",
        entity_id=str(run.id),
        action="commit",
        new_value=str(imp.id),
    )
    db.commit()
    db.refresh(imp)
    return imp
