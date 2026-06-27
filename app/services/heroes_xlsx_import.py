"""Orquestração upload/preview Heroes XLSX."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import HeroesImportRunStatus, HeroesSheetType
from app.models import HeroesImportRun, ImportationOrder, RawImportFile
from app.services.auth import write_audit_log
from app.services.heroes_conflict import apply_run_review_state
from app.services.heroes_import import compute_file_hash, save_raw_import_file
from app.services.heroes_xlsx_staging import sync_heroes_xlsx_staging
from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME, resolve_heroes_workbook_path
from app.services.heroes_workbook_profiler import profile_workbook_bytes, profile_workbook_file
from app.services.heroes_xlsx_parser import (
    list_xlsx_sheets,
    make_idempotency_key,
    parse_xlsx_sheet,
)


def _is_terminal_import_run(run: HeroesImportRun) -> bool:
    if run.status == HeroesImportRunStatus.COMMITTED.value:
        return True
    if run.status == HeroesImportRunStatus.ATTACHED.value:
        return False
    return bool(run.importation_id)


def link_raw_file_to_importation(
    db: Session,
    *,
    importation_id: int,
    raw_file_id: int,
    user_id: int | None,
) -> HeroesImportRun:
    """Associa arquivo bruto Heroes a ordem manual — sem preview/commit."""
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id,
        ImportationOrder.is_active.is_(True),
    ).first()
    if not imp:
        raise ValueError("Ordem não encontrada")

    raw = db.query(RawImportFile).filter(RawImportFile.id == raw_file_id).first()
    if not raw:
        raise ValueError("Arquivo raw não encontrado")

    idem = f"attached:{importation_id}:{raw_file_id}"
    existing = db.query(HeroesImportRun).filter(HeroesImportRun.idempotency_key == idem).first()
    if existing:
        return existing

    run = HeroesImportRun(
        raw_file_id=raw_file_id,
        importation_id=importation_id,
        file_checksum=raw.file_hash,
        original_filename=raw.original_filename,
        sheet_name="_pending_",
        sheet_type="UNKNOWN",
        parser_version="0",
        idempotency_key=idem,
        status=HeroesImportRunStatus.ATTACHED.value,
        preview_json={"linked_from": "nova_ordem", "raw_file_id": raw_file_id},
        uploaded_by_id=user_id,
    )
    db.add(run)
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="importation_order",
        entity_id=str(importation_id),
        action="link_heroes_raw",
        new_value=str(raw_file_id),
    )
    db.commit()
    db.refresh(run)
    return run


def load_local_workbook_bytes() -> tuple[bytes, str]:
    path = resolve_heroes_workbook_path()
    if path is None:
        raise FileNotFoundError(
            f"Planilha {HEROES_WORKBOOK_FILENAME} não encontrada na raiz do projeto nem em data/raw/"
        )
    return path.read_bytes(), str(path)


def profile_local_workbook() -> dict:
    return profile_workbook_file()


def profile_uploaded_workbook(content: bytes, *, source_path: str | None = None) -> dict:
    return profile_workbook_bytes(content, source_path=source_path)


def register_workbook_bytes(
    db: Session,
    content: bytes,
    *,
    filename: str,
    user_id: int | None,
    source_label: str | None = None,
) -> dict:
    """Registra arquivo raw para preview/commit — não importa ordem automaticamente."""
    file_hash = compute_file_hash(content)
    existing = db.query(RawImportFile).filter(RawImportFile.file_hash == file_hash).first()
    if existing:
        sheets = list_xlsx_sheets(content)
        profile = profile_workbook_bytes(content, source_path=source_label or filename)
        return {
            "raw_file_id": existing.id,
            "file_checksum": file_hash,
            "sheets": sheets,
            "workbook_profile": profile,
            "source_path": source_label,
            "reused": True,
        }

    _, storage_path = save_raw_import_file(content, filename)
    raw = RawImportFile(
        file_hash=file_hash,
        storage_path=storage_path,
        original_filename=filename,
        source_system="HEROES_XLSX",
        imported_by_id=user_id,
    )
    db.add(raw)
    db.flush()
    sheets = list_xlsx_sheets(content)
    profile = profile_workbook_bytes(content, source_path=source_label or filename)
    raw.row_count = len(sheets)
    db.commit()
    db.refresh(raw)
    return {
        "raw_file_id": raw.id,
        "file_checksum": file_hash,
        "sheets": sheets,
        "workbook_profile": profile,
        "source_path": source_label,
        "reused": False,
    }


def upload_xlsx_file(db: Session, file: UploadFile, content: bytes, *, user_id: int | None) -> dict:
    result = register_workbook_bytes(
        db,
        content,
        filename=file.filename or "heroes.xlsx",
        user_id=user_id,
    )
    return {
        "raw_file_id": result["raw_file_id"],
        "file_checksum": result["file_checksum"],
        "sheets": result["sheets"],
        "workbook_profile": result["workbook_profile"],
        "source_path": result.get("source_path"),
    }


def load_local_workbook(db: Session, *, user_id: int | None) -> dict:
    content, path = load_local_workbook_bytes()
    return register_workbook_bytes(
        db,
        content,
        filename=Path(path).name,
        user_id=user_id,
        source_label=path,
    )


def find_attached_run_for_importation(
    db: Session,
    importation_id: int,
) -> HeroesImportRun | None:
    return (
        db.query(HeroesImportRun)
        .filter(
            HeroesImportRun.importation_id == importation_id,
            HeroesImportRun.idempotency_key.like(f"attached:{importation_id}:%"),
        )
        .order_by(HeroesImportRun.id.desc())
        .first()
    )


def _read_raw_bytes(raw: RawImportFile) -> bytes:
    settings = get_settings()
    path = settings.imports_path / raw.storage_path
    if not path.is_file():
        raise ValueError(f"Arquivo raw não encontrado: {raw.storage_path}")
    return path.read_bytes()


def _resolve_ordine_sheet_name(content: bytes, imp: ImportationOrder, sheet_name: str | None) -> str:
    sheets = list_xlsx_sheets(content)
    names = [s["sheet_name"] for s in sheets]
    if sheet_name and sheet_name in names:
        return sheet_name
    po = imp.po_number or ""
    m = re.search(r"(\d+)", po)
    if m:
        candidate = f"Ordine {m.group(1)}"
        if candidate in names:
            return candidate
    for meta in sheets:
        if meta.get("sheet_type") == HeroesSheetType.ORDER.value:
            return meta["sheet_name"]
    raise ValueError("Nenhuma sheet Ordine encontrada na planilha vinculada")


def preview_attached_run(
    db: Session,
    *,
    importation_id: int,
    user_id: int | None,
    sheet_name: str | None = None,
) -> HeroesImportRun:
    """Parser completo no run ATTACHED da ordem manual — mesmo run_id."""
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id,
        ImportationOrder.is_active.is_(True),
    ).first()
    if not imp:
        raise ValueError("Ordem não encontrada")

    run = find_attached_run_for_importation(db, importation_id)
    if not run or not run.raw_file_id:
        raise ValueError("Nenhum vínculo Heroes ATTACHED encontrado para esta ordem")
    if run.status == HeroesImportRunStatus.COMMITTED.value:
        raise ValueError("Import Heroes já commitado para esta ordem")

    raw = db.query(RawImportFile).filter(RawImportFile.id == run.raw_file_id).first()
    if not raw:
        raise ValueError("Arquivo raw não encontrado")

    content = _read_raw_bytes(raw)
    resolved_sheet = _resolve_ordine_sheet_name(content, imp, sheet_name)
    preview = parse_xlsx_sheet(content, resolved_sheet, file_checksum=raw.file_hash)
    preview["source_file"] = raw.original_filename
    sync_heroes_xlsx_staging(
        db,
        run_id=run.id,
        raw_file_id=raw.id,
        preview=preview,
    )

    run.sheet_name = resolved_sheet
    run.sheet_type = preview.get("sheet_type", "UNKNOWN")
    run.parser_version = preview.get("parser_version", "1.1.0")
    run.order_number = preview.get("order_number")
    run.preview_json = preview
    run.warnings_json = preview.get("warnings")
    run.errors_json = preview.get("errors")
    run.status = HeroesImportRunStatus.PREVIEW.value
    apply_run_review_state(run, preview, confirmed_order_number=None)

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="heroes_import_run",
        entity_id=str(run.id),
        action="preview_attached",
        new_value=str(importation_id),
    )
    db.commit()
    db.refresh(run)
    return run


def preview_xlsx_sheet(
    db: Session,
    *,
    raw_file_id: int,
    sheet_name: str,
    content: bytes,
    filename: str,
    user_id: int | None,
    confirmed_order_number: str | None = None,
) -> HeroesImportRun:
    file_hash = compute_file_hash(content)
    idem = make_idempotency_key(file_hash, sheet_name)

    preview = parse_xlsx_sheet(content, sheet_name, file_checksum=file_hash)
    preview["source_file"] = filename
    if confirmed_order_number:
        preview["confirmed_order_number"] = confirmed_order_number
        preview["order_number"] = confirmed_order_number

    existing = db.query(HeroesImportRun).filter(HeroesImportRun.idempotency_key == idem).first()
    if existing and confirmed_order_number is None:
        if _is_terminal_import_run(existing):
            if existing.importation_id and existing.status != HeroesImportRunStatus.COMMITTED.value:
                existing.status = HeroesImportRunStatus.COMMITTED.value
                db.commit()
                db.refresh(existing)
            return existing
        apply_run_review_state(existing, preview, confirmed_order_number=None)
        existing.preview_json = preview
        existing.warnings_json = preview.get("warnings")
        db.commit()
        db.refresh(existing)
        return existing

    run = HeroesImportRun(
        raw_file_id=raw_file_id,
        file_checksum=file_hash,
        original_filename=filename,
        sheet_name=sheet_name,
        sheet_type=preview.get("sheet_type", "UNKNOWN"),
        parser_version=preview.get("parser_version", "1.1.0"),
        order_number=preview.get("order_number"),
        idempotency_key=idem,
        status=HeroesImportRunStatus.PREVIEW.value,
        preview_json=preview,
        warnings_json=preview.get("warnings"),
        errors_json=preview.get("errors"),
        uploaded_by_id=user_id,
        confirmed_order_number=confirmed_order_number,
    )
    apply_run_review_state(run, preview, confirmed_order_number=confirmed_order_number)

    if existing:
        if _is_terminal_import_run(existing):
            if existing.importation_id and existing.status != HeroesImportRunStatus.COMMITTED.value:
                existing.status = HeroesImportRunStatus.COMMITTED.value
                db.commit()
                db.refresh(existing)
            return existing
        for attr in (
            "sheet_type",
            "parser_version",
            "order_number",
            "status",
            "preview_json",
            "warnings_json",
            "errors_json",
            "confirmed_order_number",
            "review_required",
        ):
            setattr(existing, attr, getattr(run, attr))
        apply_run_review_state(existing, preview, confirmed_order_number=confirmed_order_number)
        db.commit()
        db.refresh(existing)
        return existing

    db.add(run)
    db.commit()
    db.refresh(run)
    return run
