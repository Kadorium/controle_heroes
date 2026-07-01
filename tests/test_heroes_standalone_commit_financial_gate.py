"""Commit standalone Heroes — gate de revisão financeira."""

import uuid

import pytest

from app.models import RawImportFile
from app.services.heroes_financial_preview import attach_financial_review_to_preview
from app.services.heroes_import import save_raw_import_file
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_import import preview_xlsx_sheet
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx


def _preview_run(db):
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    content = build_ordine_758_xlsx()
    fh, path = save_raw_import_file(content, f"fin-{order_number}.xlsx")
    raw = RawImportFile(
        file_hash=fh,
        storage_path=path,
        original_filename=f"fin-{order_number}.xlsx",
        source_system="HEROES_XLSX",
    )
    db.add(raw)
    db.commit()
    run = preview_xlsx_sheet(
        db,
        raw_file_id=raw.id,
        sheet_name="Ordine 758",
        content=content,
        filename=f"fin-{order_number}.xlsx",
        user_id=1,
        confirmed_order_number=order_number,
    )
    preview = dict(run.preview_json or {})
    preview["legacy_sheet_summary"] = {"versato_amount": "100", "versato_currency": "EUR"}
    attach_financial_review_to_preview(preview)
    run.preview_json = preview
    db.commit()
    return run, order_number


def test_standalone_commit_rejects_financial_review_without_confirm(db):
    run, order_number = _preview_run(db)
    assert (run.preview_json or {}).get("financial_review", {}).get("requires_manual_review")

    with pytest.raises(ValueError, match="Revisão financeira pendente"):
        commit_heroes_import_run(
            db,
            run.id,
            user_id=1,
            confirm_import=True,
            confirm_sheet_match=True,
            confirm_financial_review=False,
            opening_exchange_rate="5.00",
            confirmed_order_number=order_number,
        )


def test_standalone_commit_accepts_financial_review_with_confirm(db):
    run, order_number = _preview_run(db)

    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        confirm_financial_review=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    assert imp.po_number == f"HEROES-{order_number}"
