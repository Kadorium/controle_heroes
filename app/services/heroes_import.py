import csv
import hashlib
import io
import json
import secrets
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import DEFAULT_IMPORT_CURRENCY, get_settings
from app.core.enums import (
    DEFAULT_HEROES_COLUMN_MAPPING,
    ReviewQueueStatus,
    SourceSystem,
    StagingRowStatus,
)
from app.core.parse import optional_decimal, optional_int
from app.models import (
    HeroesImportMapping,
    ImportationItem,
    ImportationOrder,
    Product,
    RawImportFile,
    ReviewQueueItem,
    StagingImportRow,
    Supplier,
)
from app.services.auth import write_audit_log


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_raw_import_file(content: bytes, filename: str, settings=None) -> tuple[str, str]:
    s = settings or get_settings()
    file_hash = compute_file_hash(content)
    storage_rel = f"raw/{file_hash[:16]}_{secrets.token_hex(4)}_{filename}"
    full_path = s.imports_path / storage_rel
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return file_hash, storage_rel


def _get_cell(row: dict[str, str], mapping: dict[str, str], field: str) -> str | None:
    col = mapping.get(field)
    if not col:
        return None
    val = row.get(col, "")
    if val is None:
        return None
    val = str(val).strip()
    return val if val else None


def _parse_row(row: dict[str, str], mapping: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    po = _get_cell(row, mapping, "po_number")
    sku = _get_cell(row, mapping, "sku")
    desc = _get_cell(row, mapping, "description")
    qty_raw = _get_cell(row, mapping, "quantity")
    price_raw = _get_cell(row, mapping, "unit_price")
    supplier = _get_cell(row, mapping, "supplier")

    if not po:
        reasons.append("po_number vazio")
    if not sku:
        reasons.append("sku vazio ou ambíguo")

    qty = optional_int(qty_raw) if qty_raw is not None else None
    price = optional_decimal(price_raw) if price_raw is not None else None

    if qty_raw == "" or (qty_raw is not None and qty is None and qty_raw != ""):
        reasons.append("quantity inválida ou vazia — não convertida para zero")
    if price_raw == "":
        reasons.append("unit_price vazio — não convertido para zero")

    parsed = {
        "po_number": po,
        "sku": sku,
        "description": desc,
        "quantity": str(qty) if qty is not None else None,
        "unit_price": str(price) if price is not None else None,
        "supplier": supplier,
        "_raw": {k: row.get(v, "") for k, v in mapping.items() if v in row},
    }
    return parsed, reasons


def import_heroes_csv(
    db: Session,
    file: UploadFile,
    content: bytes,
    *,
    user_id: int | None,
    column_mapping: dict[str, str] | None = None,
    mapping_id: int | None = None,
) -> RawImportFile:
    mapping = column_mapping or DEFAULT_HEROES_COLUMN_MAPPING.copy()
    if mapping_id:
        db_mapping = db.query(HeroesImportMapping).filter(HeroesImportMapping.id == mapping_id).first()
        if db_mapping:
            mapping = db_mapping.column_mapping

    file_hash, storage_path = save_raw_import_file(content, file.filename or "heroes.csv")

    raw = RawImportFile(
        file_hash=file_hash,
        storage_path=storage_path,
        original_filename=file.filename or "heroes.csv",
        source_system=SourceSystem.HEROES_SPREADSHEET.value,
        imported_by_id=user_id,
    )
    db.add(raw)
    db.flush()

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    seen_keys: dict[str, int] = {}
    row_count = 0

    for idx, row in enumerate(reader, start=2):
        row_count += 1
        parsed, reasons = _parse_row(row, mapping)

        key = f"{parsed.get('po_number')}|{parsed.get('sku')}"
        if parsed.get("po_number") and parsed.get("sku"):
            if key in seen_keys:
                reasons.append(f"linha duplicada ambígua (também linha {seen_keys[key]})")
            else:
                seen_keys[key] = idx

        status = StagingRowStatus.PENDING_REVIEW.value
        review_reason = "; ".join(reasons) if reasons else None

        staging = StagingImportRow(
            raw_file_id=raw.id,
            row_number=idx,
            parsed_data_json=parsed,
            status=status,
            review_reason=review_reason,
        )
        db.add(staging)
        db.flush()

        if reasons:
            db.add(
                ReviewQueueItem(
                    staging_row_id=staging.id,
                    status=ReviewQueueStatus.OPEN.value,
                    reason=review_reason or "Revisão necessária",
                    priority=10 if "duplicada" in (review_reason or "") else 5,
                )
            )

    raw.row_count = row_count
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="raw_import_file",
        entity_id=str(raw.id),
        action="import",
        new_value=str(row_count),
    )
    db.commit()
    db.refresh(raw)
    return raw


def approve_staging_row(db: Session, staging_id: int, *, user_id: int | None) -> StagingImportRow:
    staging = db.query(StagingImportRow).filter(StagingImportRow.id == staging_id).first()
    if not staging:
        raise ValueError("Linha staging não encontrada")
    if staging.status == StagingRowStatus.MERGED.value:
        raise ValueError("Linha já mergeada")
    if staging.review_reason and staging.status == StagingRowStatus.PENDING_REVIEW.value:
        open_review = (
            db.query(ReviewQueueItem)
            .filter(
                ReviewQueueItem.staging_row_id == staging.id,
                ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
            )
            .first()
        )
        if open_review:
            raise ValueError("Linha possui pendência em review_queue — resolver antes de aprovar")

    data = staging.parsed_data_json
    po = data.get("po_number")
    sku = data.get("sku")
    if not po or not sku:
        raise ValueError("PO e SKU obrigatórios para merge")

    supplier_name = data.get("supplier") or "Heroes Import"
    supplier = db.query(Supplier).filter(Supplier.name == supplier_name).first()
    if not supplier:
        supplier = Supplier(name=supplier_name, country="CN", currency_default=DEFAULT_IMPORT_CURRENCY)
        db.add(supplier)
        db.flush()

    imp = db.query(ImportationOrder).filter(ImportationOrder.po_number == po).first()
    if not imp:
        imp = ImportationOrder(
            po_number=po,
            supplier_id=supplier.id,
            currency=DEFAULT_IMPORT_CURRENCY,
            current_status="PO_CREATED",
            created_by_id=user_id,
        )
        db.add(imp)
        db.flush()

    product = db.query(Product).filter(Product.sku_code == sku).first()
    if not product:
        product = Product(sku_code=sku, description=data.get("description") or sku)
        db.add(product)
        db.flush()

    qty = optional_int(data.get("quantity"))
    price = optional_decimal(data.get("unit_price"))
    db.add(
        ImportationItem(
            importation_id=imp.id,
            product_id=product.id,
            supplier_sku=sku,
            description=data.get("description"),
            quantity_ordered=qty,
            unit_price_foreign=price,
        )
    )

    staging.status = StagingRowStatus.MERGED.value
    staging.merged_entity_type = "importation_order"
    staging.merged_entity_id = str(imp.id)
    staging.reviewed_by_id = user_id
    staging.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="staging_import_row",
        entity_id=str(staging.id),
        action="approve_merge",
        new_value=str(imp.id),
    )
    db.commit()
    db.refresh(staging)
    return staging
