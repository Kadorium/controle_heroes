"""Staging + review_queue para preview Heroes XLSX (racchetta → SKU)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ReviewQueueStatus, StagingRowStatus
from app.models import ReviewQueueItem, StagingImportRow
from app.services.heroes_product_match import match_product


def _staging_key(parsed: dict) -> tuple:
    return (
        parsed.get("heroes_run_id"),
        parsed.get("sheet_row"),
        parsed.get("product_name_raw"),
        parsed.get("source"),
    )


def sync_heroes_xlsx_staging(
    db: Session,
    *,
    run_id: int,
    raw_file_id: int,
    preview: dict,
) -> dict:
    """Cria/atualiza staging + review_queue para SKUs não resolvidos."""
    from app.services.heroes_invoice_blocks import get_invoice_blocks_for_preview

    seen_keys: set[tuple] = set()
    rows_to_index: list[tuple[dict, int]] = []

    for block in get_invoice_blocks_for_preview(preview):
        inv_num = block.get("invoice_number")
        inv_date = block.get("invoice_date")
        for item in block.get("items") or []:
            name = item.get("product_name_raw")
            if not name:
                continue
            parsed = {
                "issue_type": "SKU_UNRESOLVED",
                "product_name_raw": name,
                "invoice_number": inv_num,
                "invoice_date": inv_date,
                "sheet_row": item.get("row_number"),
                "heroes_run_id": run_id,
                "source": "heroes_xlsx",
            }
            rows_to_index.append((parsed, item.get("row_number") or 0))

    for da in preview.get("da_spedire") or []:
        name = da.get("product_name_raw")
        if not name:
            continue
        parsed = {
            "issue_type": "SKU_UNRESOLVED",
            "product_name_raw": name,
            "invoice_number": None,
            "invoice_date": None,
            "sheet_row": da.get("row_number"),
            "heroes_run_id": run_id,
            "source": "heroes_xlsx",
            "context": "da_spedire",
        }
        rows_to_index.append((parsed, da.get("row_number") or 0))

    open_count = 0
    for parsed, row_number in rows_to_index:
        if match_product(db, parsed["product_name_raw"]) is not None:
            continue
        key = _staging_key(parsed)
        seen_keys.add(key)
        existing = (
            db.query(StagingImportRow)
            .filter(
                StagingImportRow.raw_file_id == raw_file_id,
                StagingImportRow.row_number == row_number,
            )
            .all()
        )
        staging = None
        for row in existing:
            data = row.parsed_data_json or {}
            if _staging_key(data) == key:
                staging = row
                break
        if staging is None:
            staging = StagingImportRow(
                raw_file_id=raw_file_id,
                row_number=row_number,
                parsed_data_json=parsed,
                status=StagingRowStatus.PENDING_REVIEW.value,
                review_reason=f"SKU não resolvido: {parsed['product_name_raw']}",
            )
            db.add(staging)
            db.flush()
            db.add(
                ReviewQueueItem(
                    staging_row_id=staging.id,
                    status=ReviewQueueStatus.OPEN.value,
                    reason=(
                        f"Vincular racchetta «{parsed['product_name_raw']}» "
                        f"na fatura {parsed.get('invoice_number') or '—'}"
                    ),
                    priority=8,
                )
            )
            open_count += 1
        elif staging.status == StagingRowStatus.PENDING_REVIEW.value:
            if not (staging.parsed_data_json or {}).get("resolved_product_id"):
                open_count += 1

    # Fechar staging obsoleto deste run (re-preview)
    all_staging = (
        db.query(StagingImportRow)
        .filter(StagingImportRow.raw_file_id == raw_file_id)
        .all()
    )
    for staging in all_staging:
        data = staging.parsed_data_json or {}
        if data.get("heroes_run_id") != run_id or data.get("source") != "heroes_xlsx":
            continue
        if _staging_key(data) not in seen_keys and data.get("issue_type") == "SKU_UNRESOLVED":
            staging.status = StagingRowStatus.MERGED.value
            for rq in db.query(ReviewQueueItem).filter(
                ReviewQueueItem.staging_row_id == staging.id,
                ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
            ):
                rq.status = ReviewQueueStatus.RESOLVED.value
                rq.resolution_notes = "Linha removida no re-preview"

    preview["sku_review_pending"] = open_count > 0
    preview["sku_review_open_count"] = open_count
    return preview


def count_open_sku_reviews_for_run(db: Session, run_id: int, raw_file_id: int) -> int:
    rows = (
        db.query(StagingImportRow)
        .filter(StagingImportRow.raw_file_id == raw_file_id)
        .all()
    )
    count = 0
    for staging in rows:
        data = staging.parsed_data_json or {}
        if data.get("heroes_run_id") != run_id:
            continue
        if data.get("resolved_product_id"):
            continue
        open_rq = (
            db.query(ReviewQueueItem)
            .filter(
                ReviewQueueItem.staging_row_id == staging.id,
                ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
            )
            .first()
        )
        if open_rq:
            count += 1
    return count


def resolve_staging_sku(
    db: Session,
    staging_id: int,
    *,
    product_id: int,
    user_id: int | None,
) -> StagingImportRow:
    from app.models import Product

    staging = db.query(StagingImportRow).filter(StagingImportRow.id == staging_id).first()
    if not staging:
        raise ValueError("Linha staging não encontrada")
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise ValueError("Produto não encontrado")
    data = dict(staging.parsed_data_json or {})
    data["resolved_product_id"] = product_id
    data["resolved_sku_code"] = product.sku_code
    staging.parsed_data_json = data
    staging.status = StagingRowStatus.APPROVED.value
    staging.reviewed_by_id = user_id
    from datetime import datetime, timezone

    staging.reviewed_at = datetime.now(timezone.utc)
    for rq in db.query(ReviewQueueItem).filter(
        ReviewQueueItem.staging_row_id == staging.id,
        ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
    ):
        rq.status = ReviewQueueStatus.RESOLVED.value
        rq.resolved_by_id = user_id
        rq.resolved_at = datetime.now(timezone.utc)
        rq.resolution_notes = f"Vinculado a SKU {product.sku_code}"
    db.flush()
    return staging
