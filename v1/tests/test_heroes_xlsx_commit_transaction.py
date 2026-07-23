"""Transação no commit Heroes standalone — rollback sem orphans."""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from app.models import ImportationOrder, Invoice, RawImportFile
from app.services.heroes_import import save_raw_import_file
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_import import preview_xlsx_sheet
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx


def _make_run(db):
    order_suffix = uuid.uuid4().hex[:8]
    content = build_ordine_758_xlsx()
    fh, path = save_raw_import_file(content, f"tx-{order_suffix}.xlsx")
    raw = RawImportFile(
        file_hash=fh,
        storage_path=path,
        original_filename=f"tx-{order_suffix}.xlsx",
        source_system="HEROES_XLSX",
    )
    db.add(raw)
    db.commit()
    run = preview_xlsx_sheet(
        db,
        raw_file_id=raw.id,
        sheet_name="Ordine 758",
        content=content,
        filename=f"tx-{order_suffix}.xlsx",
        user_id=1,
        confirmed_order_number=f"758-{order_suffix}",
    )
    return run, f"758-{order_suffix}"


def test_standalone_commit_rollback_on_mid_merge_failure(db, engine):
    run, order_number = _make_run(db)
    po = f"HEROES-{order_number}"

    VerifySession = sessionmaker(bind=engine)
    verify = VerifySession()
    try:
        before_imps = verify.query(ImportationOrder).filter(ImportationOrder.po_number == po).count()
        before_invoices = verify.query(Invoice).count()
    finally:
        verify.close()

    with patch(
        "app.services.heroes_xlsx_commit._merge_preview_into_importation",
        side_effect=RuntimeError("simulated failure at item 40"),
    ) as mock_merge:
        with pytest.raises(RuntimeError, match="simulated failure"):
            commit_heroes_import_run(
                db,
                run.id,
                user_id=1,
                confirm_import=True,
                confirm_sheet_match=True,
                opening_exchange_rate="5.00",
                confirmed_order_number=order_number,
            )
        assert mock_merge.called

    db.rollback()
    verify = VerifySession()
    try:
        assert verify.query(ImportationOrder).filter(ImportationOrder.po_number == po).count() == before_imps
        assert verify.query(Invoice).count() == before_invoices
    finally:
        verify.close()
