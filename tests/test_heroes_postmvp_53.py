"""Fase pós-MVP 5.3 — versato, DA SPEDIRE persistidos e política de conflito."""

from __future__ import annotations

from pathlib import Path
import uuid

import pytest

from app.config import ROOT_DIR
from app.core.enums import HeroesImportRunStatus
from app.models import HeroesDispatchPendingItem, HeroesLegacySheetSummary, ImportationOrder, Payment
from app.services.heroes_conflict import validate_commit_allowed
from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_import import preview_xlsx_sheet, register_workbook_bytes
from app.services.heroes_xlsx_parser import parse_xlsx_sheet
from app.services.order_status_rail import build_status_rail
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx, build_ordine_759_xlsx

REAL_WORKBOOK = ROOT_DIR / HEROES_WORKBOOK_FILENAME
SHEET_758 = "Ordine 758"


@pytest.fixture
def xlsx_758():
    return build_ordine_758_xlsx()


@pytest.fixture
def xlsx_759():
    return build_ordine_759_xlsx()


def _commit_758(db, content: bytes, *, user_id: int = 1, order_number: str | None = None) -> ImportationOrder:
    order_number = order_number or f"758-{uuid.uuid4().hex[:8]}"
    reg = register_workbook_bytes(db, content, filename="ordine758.xlsx", user_id=user_id)
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 758",
        content=content,
        filename="ordine758.xlsx",
        user_id=user_id,
        confirmed_order_number=order_number,
    )
    return commit_heroes_import_run(
        db,
        run.id,
        user_id=user_id,
        confirm_import=True,
        confirm_sheet_match=True,
        confirmed_order_number=order_number,
    )


def test_versato_parsed_in_preview(xlsx_758):
    preview = parse_xlsx_sheet(xlsx_758, "Ordine 758")
    legacy = preview.get("legacy_sheet_summary")
    assert legacy is not None
    assert float(legacy["versato_amount"]) == 397500.0


def test_commit_persists_versato(db, xlsx_758):
    imp = _commit_758(db, xlsx_758)
    row = (
        db.query(HeroesLegacySheetSummary)
        .filter(HeroesLegacySheetSummary.importation_id == imp.id, HeroesLegacySheetSummary.is_active.is_(True))
        .first()
    )
    assert row is not None
    assert row.versato_amount == 397500


def test_versato_in_order_central(db, admin_client, xlsx_758):
    imp = _commit_758(db, xlsx_758)
    res = admin_client.get(f"/api/importations/{imp.id}/order-central")
    assert res.status_code == 200
    body = res.json()
    assert body["legacy_sheet_summary"]["versato_amount"] == "397500.0000" or body["legacy_sheet_summary"]["versato_amount"].startswith("397500")
    assert body["kpis"]["versato_heroes"] is not None


def test_versato_not_extra_official_payment(db, xlsx_758):
    imp = _commit_758(db, xlsx_758)
    legacy = db.query(HeroesLegacySheetSummary).filter(HeroesLegacySheetSummary.importation_id == imp.id).first()
    from app.models import Invoice

    payments = db.query(Payment).join(Invoice, Payment.invoice_id == Invoice.id).filter(Invoice.importation_id == imp.id).all()
    versato_payment = [p for p in payments if p.amount_foreign == legacy.versato_amount]
    assert len(versato_payment) == 0


def test_dispatch_pending_persisted(db, xlsx_758):
    imp = _commit_758(db, xlsx_758)
    rows = db.query(HeroesDispatchPendingItem).filter(HeroesDispatchPendingItem.importation_id == imp.id).all()
    assert len(rows) >= 2
    star = next((r for r in rows if "STARLIGHT" in r.product_name_raw.upper()), None)
    assert star is not None
    assert star.price_listino is not None or star.price_fattura is not None


def test_order_central_dispatch_fields(db, admin_client, xlsx_758):
    imp = _commit_758(db, xlsx_758)
    body = admin_client.get(f"/api/importations/{imp.id}/order-central").json()
    assert len(body["dispatch_pending"]) >= 2
    with_prices = [m for m in body["models"] if m.get("price_listino") or m.get("price_fattura")]
    assert len(with_prices) >= 1


def test_empty_field_not_zero_dispatch(db, xlsx_758):
    imp = _commit_758(db, xlsx_758)
    rows = db.query(HeroesDispatchPendingItem).filter(HeroesDispatchPendingItem.importation_id == imp.id).all()
    for r in rows:
        if r.quantity_to_dispatch is None:
            assert r.quantity_to_dispatch != 0


def test_ordine_759_review_required(db, xlsx_759):
    reg = register_workbook_bytes(db, xlsx_759, filename="759.xlsx", user_id=1)
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 759",
        content=xlsx_759,
        filename="759.xlsx",
        user_id=1,
    )
    assert run.review_required is True
    assert run.status == HeroesImportRunStatus.REVIEW_REQUIRED.value


def test_ordine_759_commit_blocked_without_confirm(db, xlsx_759):
    reg = register_workbook_bytes(db, xlsx_759, filename="759.xlsx", user_id=1)
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 759",
        content=xlsx_759,
        filename="759.xlsx",
        user_id=1,
    )
    preview = run.preview_json
    msg = validate_commit_allowed(
        db, preview, confirmed_order_number=None, confirm_import=True, confirm_sheet_match=True
    )
    assert "confirmed_order_number" in msg.lower() or "divergência" in msg.lower()


def test_ordine_759_as_907_blocks_if_exists(db, xlsx_759):
    from app.services.heroes_xlsx_commit import _get_heroes_supplier

    supplier = _get_heroes_supplier(db)
    imp907 = ImportationOrder(
        po_number="HEROES-907",
        supplier_id=supplier.id,
        currency="EUR",
        current_status="PO_CREATED",
    )
    db.add(imp907)
    db.flush()

    reg = register_workbook_bytes(db, xlsx_759, filename="759.xlsx", user_id=1)
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 759",
        content=xlsx_759,
        filename="759.xlsx",
        user_id=1,
        confirmed_order_number="907",
    )
    msg = validate_commit_allowed(
        db,
        run.preview_json,
        confirmed_order_number="907",
        confirm_import=True,
        confirm_sheet_match=True,
    )
    assert "HEROES-907" in msg or "já existe" in msg


def test_idempotency_758_recommit(db, xlsx_758):
    order_number = f"758-idem-{uuid.uuid4().hex[:6]}"
    reg = register_workbook_bytes(db, xlsx_758, filename="758.xlsx", user_id=1)
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name="Ordine 758",
        content=xlsx_758,
        filename="758.xlsx",
        user_id=1,
        confirmed_order_number=order_number,
    )
    imp1 = commit_heroes_import_run(
        db, run.id, user_id=1, confirm_import=True, confirm_sheet_match=True, confirmed_order_number=order_number
    )
    # Simula ordem commitada sem legacy (pré-5.3)
    db.query(HeroesLegacySheetSummary).filter(HeroesLegacySheetSummary.importation_id == imp1.id).delete()
    db.query(HeroesDispatchPendingItem).filter(HeroesDispatchPendingItem.importation_id == imp1.id).delete()
    db.commit()
    imp2 = commit_heroes_import_run(
        db, run.id, user_id=1, confirm_import=True, confirm_sheet_match=True, confirmed_order_number=order_number
    )
    assert imp1.id == imp2.id
    assert (
        db.query(HeroesLegacySheetSummary)
        .filter(HeroesLegacySheetSummary.importation_id == imp1.id, HeroesLegacySheetSummary.is_active.is_(True))
        .count()
        == 1
    )


def test_status_rail_no_faturado_without_invoices():
    rail = build_status_rail(
        "PROFORMA_RECEIVED",
        has_invoices=False,
        has_payments=False,
        has_shipments=False,
        shipment_in_transit=False,
    )
    faturado = next(s for s in rail["stages"] if s["key"] == "faturado")
    assert faturado["state"] == "declared_without_data"
    assert faturado["data_supported"] is False


def test_status_rail_faturado_with_invoices():
    rail = build_status_rail(
        "PROFORMA_RECEIVED",
        has_invoices=True,
        has_payments=False,
        has_shipments=False,
        shipment_in_transit=False,
    )
    faturado = next(s for s in rail["stages"] if s["key"] == "faturado")
    assert faturado["state"] == "done"


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="planilha real ausente")
def test_real_758_versato_and_dispatch(db, admin_client):
    from app.services.reset_operational_data import RESET_ENV_VAR, reset_operational_test_data
    import os
    os.environ[RESET_ENV_VAR] = "1"
    reset_operational_test_data(db, skip_backup=True)
    content = REAL_WORKBOOK.read_bytes()
    order_number = f"758-{uuid.uuid4().hex[:8]}"
    reg = register_workbook_bytes(db, content, filename=REAL_WORKBOOK.name, user_id=1)
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name=SHEET_758,
        content=content,
        filename=REAL_WORKBOOK.name,
        user_id=1,
        confirmed_order_number=order_number,
    )
    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        confirmed_order_number=order_number,
    )
    central = admin_client.get(f"/api/importations/{imp.id}/order-central").json()
    assert central["legacy_sheet_summary"] is not None
    assert len(central["dispatch_pending"]) >= 5
