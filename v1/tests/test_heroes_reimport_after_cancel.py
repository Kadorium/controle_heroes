"""Reimportação Heroes após anulação da ordem — libera preview e fila operacional."""

from __future__ import annotations

import uuid

from app.core.enums import HeroesImportRunStatus
from app.models import HeroesImportRun, ImportationOrder
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_import import preview_xlsx_sheet, register_workbook_bytes
from app.services.importation_lifecycle import (
    heroes_run_targets_active_importation,
    is_terminal_heroes_import_run,
    release_heroes_runs_on_cancel,
    release_po_number_on_cancel,
)
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx


def _preview_758(db, content: bytes, *, order_number: str | None = None):
    reg = register_workbook_bytes(db, content, filename="ordine758.xlsx", user_id=1)
    return preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 758",
        content=content,
        filename="ordine758.xlsx",
        user_id=1,
        confirmed_order_number=order_number,
    )


def test_cancel_supersedes_committed_heroes_run(db):
    content = build_ordine_758_xlsx()
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    run = _preview_758(db, content, order_number=order_number)
    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    db.refresh(run)
    assert run.status == HeroesImportRunStatus.COMMITTED.value
    assert run.importation_id == imp.id

    release_po_number_on_cancel(imp)
    released = release_heroes_runs_on_cancel(db, imp.id)
    imp.is_active = False
    db.commit()
    db.refresh(run)

    assert released == 1
    assert run.status == HeroesImportRunStatus.SUPERSEDED.value
    assert "~superseded-" in run.idempotency_key


def test_preview_after_cancel_allows_intermediate_screen(db):
    content = build_ordine_758_xlsx()
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    run = _preview_758(db, content, order_number=order_number)
    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    release_po_number_on_cancel(imp)
    release_heroes_runs_on_cancel(db, imp.id)
    imp.is_active = False
    db.commit()

    # Simula dados legados: run COMMITTED sem supersede (antes do fix de cancel)
    run.status = HeroesImportRunStatus.COMMITTED.value
    run.importation_id = imp.id
    from app.services.heroes_xlsx_parser import make_idempotency_key
    from app.services.heroes_import import compute_file_hash

    run.idempotency_key = make_idempotency_key(compute_file_hash(content), "Ordine 758")
    db.commit()

    assert not is_terminal_heroes_import_run(db, run)
    assert not heroes_run_targets_active_importation(db, run)

    rerun = _preview_758(db, content)
    assert rerun.id == run.id
    assert rerun.status in (
        HeroesImportRunStatus.PREVIEW.value,
        HeroesImportRunStatus.REVIEW_REQUIRED.value,
    )
    assert rerun.importation_id is None
    assert rerun.committed_at is None


def test_reimport_758_after_cancel_appears_in_queue(db, admin_client):
    content = build_ordine_758_xlsx()
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    run = _preview_758(db, content, order_number=order_number)
    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    po = imp.po_number

    cancel = admin_client.post(f"/api/importations/{imp.id}/cancel", json={"reason": "teste reimport"})
    assert cancel.status_code == 200

    rerun = _preview_758(db, content, order_number="758")
    new_imp = commit_heroes_import_run(
        db,
        rerun.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number="758",
    )
    assert new_imp.is_active
    assert new_imp.po_number == "HEROES-758"
    assert new_imp.id != imp.id

    queue = admin_client.get("/api/importations/order-queue").json()
    assert any(i["id"] == new_imp.id for i in queue["items"])

    preview_api = admin_client.post(
        "/api/imports/heroes/xlsx/preview",
        json={
            "raw_file_id": rerun.raw_file_id,
            "sheet_name": "Ordine 758",
        },
    )
    assert preview_api.status_code == 200
    body = preview_api.json()
    assert body["already_committed"] is False
    assert body["status"] in ("PREVIEW", "REVIEW_REQUIRED")


def test_commit_stale_run_does_not_return_cancelled_order(db):
    """Commit com run COMMITTED apontando para ordem anulada deve criar ordem nova."""
    content = build_ordine_758_xlsx()
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    run = _preview_758(db, content, order_number=order_number)
    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    release_po_number_on_cancel(imp)
    imp.is_active = False
    db.commit()
    db.refresh(run)
    assert run.status == HeroesImportRunStatus.COMMITTED.value
    assert run.importation_id == imp.id

    new_imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    assert new_imp.is_active
    assert new_imp.po_number == f"HEROES-{order_number}"
    assert new_imp.id != imp.id
    assert not new_imp.po_number.endswith(f"~anulado-{imp.id}")


def test_preview_finds_run_with_different_sheet_casing(db):
    content = build_ordine_758_xlsx()
    reg = register_workbook_bytes(db, content, filename="ordine758.xlsx", user_id=1)
    run_a = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 758",
        content=content,
        filename="ordine758.xlsx",
        user_id=1,
    )
    run_b = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="ordine 758",
        content=content,
        filename="ordine758.xlsx",
        user_id=1,
    )
    assert run_a.id == run_b.id


def test_preview_always_shows_for_active_committed(db):
    content = build_ordine_758_xlsx()
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    run = _preview_758(db, content, order_number=order_number)
    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        opening_exchange_rate="5.00",
        confirmed_order_number=order_number,
    )
    assert imp.is_active
    rerun = _preview_758(db, content)
    assert rerun.status in (
        HeroesImportRunStatus.PREVIEW.value,
        HeroesImportRunStatus.REVIEW_REQUIRED.value,
    )
    assert rerun.importation_id is None
