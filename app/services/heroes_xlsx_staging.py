"""Staging + review_queue para preview Heroes XLSX (racchetta → SKU, agrupado por chave canônica)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.enums import ReviewQueueStatus, StagingRowStatus
from app.models import ReviewQueueItem, StagingImportRow
from app.services.heroes_product_match import find_product_candidates, match_product
from app.services.heroes_racchetta_key import (
    canonical_key_for_matching,
    parse_racchetta_key,
    year_from_canonical_key,
)
from app.services.product_category import suggest_product_category


@dataclass
class _RacchettaOccurrence:
    product_name_raw: str
    sheet_row: int
    invoice_number: str | None = None
    invoice_date: str | None = None
    context: str | None = None
    suggested_category: str | None = None


@dataclass
class _RacchettaGroup:
    canonical_key: str
    occurrences: list[_RacchettaOccurrence] = field(default_factory=list)


def _staging_group_key(parsed: dict) -> tuple:
    return (
        parsed.get("heroes_run_id"),
        parsed.get("canonical_key"),
        parsed.get("source"),
    )


def _collect_groups(preview: dict, *, run_id: int) -> dict[str, _RacchettaGroup]:
    from app.services.heroes_invoice_blocks import get_invoice_blocks_for_preview

    groups: dict[str, _RacchettaGroup] = {}

    def add(name: str, *, sheet_row: int, invoice_number, invoice_date, context=None):
        parsed_key = parse_racchetta_key(name)
        if not parsed_key:
            return
        canonical = parsed_key.canonical_key
        cat, _, _ = suggest_product_category(name)
        if canonical not in groups:
            groups[canonical] = _RacchettaGroup(canonical_key=canonical)
        groups[canonical].occurrences.append(
            _RacchettaOccurrence(
                product_name_raw=name,
                sheet_row=sheet_row,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                context=context,
                suggested_category=cat,
            )
        )

    for block in get_invoice_blocks_for_preview(preview):
        inv_num = block.get("invoice_number")
        inv_date = block.get("invoice_date")
        for item in block.get("items") or []:
            name = item.get("product_name_raw")
            if not name:
                continue
            add(
                name,
                sheet_row=item.get("row_number") or 0,
                invoice_number=inv_num,
                invoice_date=inv_date,
            )

    for da in preview.get("da_spedire") or []:
        name = da.get("product_name_raw")
        if not name:
            continue
        add(
            name,
            sheet_row=da.get("row_number") or 0,
            invoice_number=None,
            invoice_date=None,
            context="da_spedire",
        )

    return groups


def _merge_groups_by_base(groups: dict[str, _RacchettaGroup]) -> dict[str, _RacchettaGroup]:
    """Funde base igual: show + show 26 → mesma chave (ano explícito ou corrente)."""
    from datetime import date

    by_base: dict[str, list[_RacchettaGroup]] = {}
    for grp in groups.values():
        base = grp.canonical_key.split("|", 1)[0]
        by_base.setdefault(base, []).append(grp)

    merged: dict[str, _RacchettaGroup] = {}
    default_year = date.today().year
    for base, grps in by_base.items():
        explicit_years = [
            y for g in grps if (y := year_from_canonical_key(g.canonical_key)) is not None
        ]
        target_year = max(explicit_years) if explicit_years else default_year
        target_key = f"{base}|{target_year}"
        combined = _RacchettaGroup(canonical_key=target_key)
        for g in grps:
            combined.occurrences.extend(g.occurrences)
        merged[target_key] = combined
    return merged


def _group_exactly_resolved(db: Session, group: _RacchettaGroup) -> bool:
    product_ids: set[int] = set()
    for occ in group.occurrences:
        matched = match_product(db, occ.product_name_raw)
        if matched is None:
            return False
        product_ids.add(matched.id)
    return len(product_ids) == 1


def _build_group_parsed(
    db: Session,
    *,
    group: _RacchettaGroup,
    run_id: int,
) -> dict:
    aliases = sorted({o.product_name_raw for o in group.occurrences}, key=str.lower)
    sheet_rows = sorted({o.sheet_row for o in group.occurrences if o.sheet_row})
    invoice_numbers = sorted(
        {str(o.invoice_number) for o in group.occurrences if o.invoice_number},
        key=str,
    )
    primary = aliases[0]
    first_inv = next((o for o in group.occurrences if o.invoice_number), None)
    category_hint = next(
        (o.suggested_category for o in group.occurrences if o.suggested_category),
        None,
    )
    candidates = find_product_candidates(
        db,
        primary,
        category_hint=category_hint,
    )
    parsed: dict = {
        "issue_type": "SKU_UNRESOLVED",
        "canonical_key": group.canonical_key,
        "product_name_raw": primary,
        "aliases": aliases,
        "sheet_rows": sheet_rows,
        "sheet_row": sheet_rows[0] if sheet_rows else 0,
        "invoice_numbers": invoice_numbers,
        "invoice_number": invoice_numbers[0] if invoice_numbers else None,
        "invoice_date": first_inv.invoice_date if first_inv else None,
        "heroes_run_id": run_id,
        "source": "heroes_xlsx",
        "alias_count": len(aliases),
        "line_count": len(group.occurrences),
    }
    if candidates:
        top = candidates[0]
        parsed["suggested_product_id"] = top.product.id
        parsed["suggested_product_sku"] = top.product.sku_code
        parsed["suggested_product_description"] = top.product.description
        parsed["match_confidence"] = top.score
        parsed["match_reason"] = top.reason
    return parsed


def sync_heroes_xlsx_staging(
    db: Session,
    *,
    run_id: int,
    raw_file_id: int,
    preview: dict,
) -> dict:
    """Cria/atualiza staging + review_queue agrupados por canonical_key."""
    groups = _merge_groups_by_base(_collect_groups(preview, run_id=run_id))
    seen_group_keys: set[tuple] = set()
    open_count = 0
    pending_line_count = 0

    for group in groups.values():
        if _group_exactly_resolved(db, group):
            continue

        parsed = _build_group_parsed(db, group=group, run_id=run_id)
        group_key = _staging_group_key(parsed)
        seen_group_keys.add(group_key)
        pending_line_count += len(group.occurrences)

        existing_rows = (
            db.query(StagingImportRow)
            .filter(StagingImportRow.raw_file_id == raw_file_id)
            .all()
        )
        staging = None
        for row in existing_rows:
            data = row.parsed_data_json or {}
            if _staging_group_key(data) == group_key:
                staging = row
                break

        aliases_label = ", ".join(parsed["aliases"][:5])
        if len(parsed["aliases"]) > 5:
            aliases_label += "…"
        inv_label = ", ".join(parsed.get("invoice_numbers") or []) or "—"
        reason = (
            f"Vincular «{parsed['product_name_raw']}» — "
            f"variantes: {aliases_label} (faturas {inv_label})"
        )

        if staging is None:
            staging = StagingImportRow(
                raw_file_id=raw_file_id,
                row_number=parsed["sheet_row"],
                parsed_data_json=parsed,
                status=StagingRowStatus.PENDING_REVIEW.value,
                review_reason=reason,
            )
            db.add(staging)
            db.flush()
            db.add(
                ReviewQueueItem(
                    staging_row_id=staging.id,
                    status=ReviewQueueStatus.OPEN.value,
                    reason=reason,
                    priority=8,
                )
            )
            open_count += 1
        else:
            prev_data = staging.parsed_data_json or {}
            if prev_data.get("resolved_product_id"):
                parsed["resolved_product_id"] = prev_data["resolved_product_id"]
                parsed["resolved_sku_code"] = prev_data.get("resolved_sku_code")
            staging.parsed_data_json = parsed
            staging.row_number = parsed["sheet_row"]
            staging.review_reason = reason
            flag_modified(staging, "parsed_data_json")
            for rq in db.query(ReviewQueueItem).filter(
                ReviewQueueItem.staging_row_id == staging.id,
                ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
            ):
                rq.reason = reason
            if staging.status == StagingRowStatus.PENDING_REVIEW.value:
                if not (staging.parsed_data_json or {}).get("resolved_product_id"):
                    open_count += 1

    all_staging = (
        db.query(StagingImportRow)
        .filter(StagingImportRow.raw_file_id == raw_file_id)
        .all()
    )
    for staging in all_staging:
        data = staging.parsed_data_json or {}
        if data.get("heroes_run_id") != run_id or data.get("source") != "heroes_xlsx":
            continue
        if _staging_group_key(data) not in seen_group_keys and data.get("issue_type") == "SKU_UNRESOLVED":
            staging.status = StagingRowStatus.MERGED.value
            for rq in db.query(ReviewQueueItem).filter(
                ReviewQueueItem.staging_row_id == staging.id,
                ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
            ):
                rq.status = ReviewQueueStatus.RESOLVED.value
                rq.resolution_notes = "Grupo removido no re-preview"

    preview["sku_review_pending"] = open_count > 0
    preview["sku_review_open_count"] = open_count
    preview["sku_review_line_count"] = pending_line_count if open_count > 0 else 0
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


def find_staging_for_alias(
    db: Session,
    *,
    raw_file_id: int,
    run_id: int,
    product_name_raw: str,
    sheet_row: int | None = None,
) -> StagingImportRow | None:
    """Localiza staging por alias ou chave canônica (pendente ou aprovado)."""
    rows = (
        db.query(StagingImportRow)
        .filter(StagingImportRow.raw_file_id == raw_file_id)
        .all()
    )
    for staging in rows:
        data = staging.parsed_data_json or {}
        if data.get("heroes_run_id") != run_id:
            continue
        if data.get("issue_type") != "SKU_UNRESOLVED":
            continue
        aliases = data.get("aliases") or [data.get("product_name_raw")]
        if product_name_raw in aliases:
            return staging
        group_canonical = data.get("canonical_key")
        if group_canonical:
            ref_year = year_from_canonical_key(str(group_canonical))
            sheet_canonical = canonical_key_for_matching(product_name_raw, reference_year=ref_year)
            if sheet_canonical == group_canonical:
                return staging
        if data.get("product_name_raw") == product_name_raw:
            if sheet_row is None or data.get("sheet_row") == sheet_row:
                return staging
    return None


def resolve_staging_sku(
    db: Session,
    staging_id: int,
    *,
    product_id: int,
    user_id: int | None,
    save_aliases: bool = True,
    extra_aliases: list[str] | None = None,
) -> StagingImportRow:
    from datetime import datetime, timezone

    from app.models import Product
    from app.services.heroes_product_aliases import save_heroes_aliases_on_product

    staging = db.query(StagingImportRow).filter(StagingImportRow.id == staging_id).first()
    if not staging:
        raise ValueError("Linha staging não encontrada")
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise ValueError("Produto não encontrado")

    data = staging.parsed_data_json or {}
    canonical_key = data.get("canonical_key")
    run_id = data.get("heroes_run_id")
    raw_file_id = staging.raw_file_id

    targets = [staging]
    if canonical_key and run_id is not None:
        for row in db.query(StagingImportRow).filter(StagingImportRow.raw_file_id == raw_file_id).all():
            row_data = row.parsed_data_json or {}
            if (
                row_data.get("heroes_run_id") == run_id
                and row_data.get("canonical_key") == canonical_key
                and row_data.get("source") == "heroes_xlsx"
                and row.id != staging.id
            ):
                targets.append(row)

    now = datetime.now(timezone.utc)
    for target in targets:
        target_data = dict(target.parsed_data_json or {})
        target_data["resolved_product_id"] = product_id
        target_data["resolved_sku_code"] = product.sku_code
        target.parsed_data_json = target_data
        target.status = StagingRowStatus.APPROVED.value
        target.reviewed_by_id = user_id
        target.reviewed_at = now
        flag_modified(target, "parsed_data_json")
        for rq in db.query(ReviewQueueItem).filter(
            ReviewQueueItem.staging_row_id == target.id,
            ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
        ):
            rq.status = ReviewQueueStatus.RESOLVED.value
            rq.resolved_by_id = user_id
            rq.resolved_at = now
            rq.resolution_notes = f"Vinculado a SKU {product.sku_code}"

    if save_aliases:
        aliases = list(data.get("aliases") or [])
        if data.get("product_name_raw") and data.get("product_name_raw") not in aliases:
            aliases.append(data["product_name_raw"])
        save_heroes_aliases_on_product(product, aliases, extra_aliases=extra_aliases)

    db.flush()
    return staging
