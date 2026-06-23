"""Fase pós-MVP 5.2 — teste real controlado Ordine 758."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import ROOT_DIR
from app.core.enums import HeroesSheetType
from app.models import ImportationOrder, Invoice, InvoiceItem
from app.services.heroes_order_format_v1 import export_normalized_xlsx, export_normalized_zip, preview_to_canonical
from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME, resolve_heroes_workbook_path
from app.services.heroes_workbook_profiler import profile_workbook_file
from app.services.heroes_xlsx_commit import commit_heroes_import_run
from app.services.heroes_xlsx_import import preview_xlsx_sheet, register_workbook_bytes
from app.services.heroes_xlsx_parser import parse_xlsx_sheet
from app.services.reset_operational_data import RESET_ENV_VAR, reset_operational_test_data

REAL_WORKBOOK = ROOT_DIR / HEROES_WORKBOOK_FILENAME
SHEET = "Ordine 758"
ORDER_NUMBER = "758"
SNAPSHOT_PATH = ROOT_DIR / "tests" / "fixtures" / "ordine_758_import_snapshot.json"
REFERENCE_PATH = ROOT_DIR / "tests" / "fixtures" / "ordine_758_planilha_reference.json"

EXPECTED_INVOICE_PRODUCTS = {"starlight", "aura", "fierce", "bull", "show", "arion"}


@pytest.fixture
def reset_env(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv(RESET_ENV_VAR, "1")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def real_workbook_bytes():
    if not REAL_WORKBOOK.is_file():
        pytest.skip(f"Planilha real ausente: {REAL_WORKBOOK}")
    return REAL_WORKBOOK.read_bytes()


@pytest.fixture
def planilha_reference(real_workbook_bytes):
    """Referência extraída da planilha real (versato, produtos)."""
    preview = parse_xlsx_sheet(real_workbook_bytes, SHEET)
    ref = {
        "sheet": SHEET,
        "order_number": preview["order_number"],
        "versato_sheet": 397500.0,
        "invoice_item_count_min": 20,
        "da_spedire_count_min": 5,
        "invoice_products": sorted({i["product_name_raw"].lower() for i in preview["invoice_items"]}),
        "da_spedire_products": sorted({d["product_name_raw"].lower() for d in preview["da_spedire"]}),
    }
    REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_PATH.write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
    return ref


def test_workbook_found_at_root():
    path = resolve_heroes_workbook_path()
    assert path is not None
    assert path.name == HEROES_WORKBOOK_FILENAME


def test_profiling_real_14_sheets():
    if not REAL_WORKBOOK.is_file():
        pytest.skip(f"Planilha real ausente: {REAL_WORKBOOK}")
    report = profile_workbook_file(REAL_WORKBOOK)
    assert report["sheet_count"] == 14
    assert report["database_writes"] is False


def test_profiling_ordine_758_importar():
    if not REAL_WORKBOOK.is_file():
        pytest.skip(f"Planilha real ausente: {REAL_WORKBOOK}")
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == SHEET)
    assert sh["sheet_type"] == HeroesSheetType.ORDER.value
    assert sh["order_number_from_content"] == ORDER_NUMBER
    assert sh["recommendation"] == "importar"
    assert sh["parser_confidence"] >= 0.75


def test_profiling_ordine_759_divergence():
    if not REAL_WORKBOOK.is_file():
        pytest.skip(f"Planilha real ausente: {REAL_WORKBOOK}")
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == "Ordine 759")
    assert sh["order_number_divergence"] is True
    assert sh["order_number_from_content"] == "907"
    assert sh["recommendation"] == "revisão manual"


def test_profiling_ritiri_hk_logistics():
    if not REAL_WORKBOOK.is_file():
        pytest.skip(f"Planilha real ausente: {REAL_WORKBOOK}")
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == "RITIRI HK")
    assert sh["sheet_type"] == HeroesSheetType.LOGISTICS.value


def test_profiling_2025_2026_financial():
    if not REAL_WORKBOOK.is_file():
        pytest.skip(f"Planilha real ausente: {REAL_WORKBOOK}")
    report = profile_workbook_file(REAL_WORKBOOK)
    by_name = {s["sheet_name"]: s for s in report["sheets"]}
    assert by_name["2025"]["sheet_type"] == HeroesSheetType.FINANCIAL_ANNUAL.value
    assert by_name["2026"]["sheet_type"] == HeroesSheetType.FINANCIAL_ANNUAL.value


def test_preview_ordine_758_no_db_write(db, real_workbook_bytes, planilha_reference):
    before = db.query(ImportationOrder).count()
    preview = parse_xlsx_sheet(real_workbook_bytes, SHEET)
    assert db.query(ImportationOrder).count() == before
    assert preview["order_number"] == ORDER_NUMBER
    assert len(preview["invoice_items"]) >= planilha_reference["invoice_item_count_min"]
    assert len(preview["da_spedire"]) >= planilha_reference["da_spedire_count_min"]
    for exp in EXPECTED_INVOICE_PRODUCTS:
        assert any(exp in p for p in planilha_reference["invoice_products"])


def test_export_v1_ordine_758(real_workbook_bytes):
    preview = parse_xlsx_sheet(real_workbook_bytes, SHEET)
    canonical = preview_to_canonical(preview, source_file=str(REAL_WORKBOOK))
    xlsx = export_normalized_xlsx(canonical)
    z = export_normalized_zip(canonical)
    assert len(xlsx) > 2000
    assert len(z) > 500


def test_auxiliary_sheets_preview_only(real_workbook_bytes):
    for sn in ("RITIRI HK", "Ordine 759", "2026"):
        p = parse_xlsx_sheet(real_workbook_bytes, sn)
        assert p["sheet_type"] in (
            HeroesSheetType.LOGISTICS.value,
            HeroesSheetType.ORDER.value,
            HeroesSheetType.FINANCIAL_ANNUAL.value,
        )
    p759 = parse_xlsx_sheet(real_workbook_bytes, "Ordine 759")
    assert p759["order_number_divergence"] is True


def test_real_import_ordine_758_flow(db, admin_client, reset_env, real_workbook_bytes, planilha_reference):
    reset_operational_test_data(db, skip_backup=True)

    reg = register_workbook_bytes(
        db,
        real_workbook_bytes,
        filename=REAL_WORKBOOK.name,
        user_id=1,
        source_label=str(REAL_WORKBOOK),
    )
    run = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name=SHEET,
        content=real_workbook_bytes,
        filename=REAL_WORKBOOK.name,
        user_id=1,
        confirmed_order_number=ORDER_NUMBER,
    )
    assert run.status == "PREVIEW"

    imp = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        confirmed_order_number=ORDER_NUMBER,
    )
    assert imp.po_number == f"HEROES-{ORDER_NUMBER}"
    assert imp.currency == "EUR"

    inv_count = db.query(Invoice).filter(Invoice.importation_id == imp.id).count()
    item_count = (
        db.query(InvoiceItem)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .filter(Invoice.importation_id == imp.id)
        .count()
    )
    assert inv_count >= 1
    assert item_count >= planilha_reference["invoice_item_count_min"]

    imp2 = commit_heroes_import_run(
        db,
        run.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        confirmed_order_number=ORDER_NUMBER,
    )
    assert imp2.id == imp.id

    run2 = preview_xlsx_sheet(
        db,
        raw_file_id=reg["raw_file_id"],
        sheet_name=SHEET,
        content=real_workbook_bytes,
        filename=REAL_WORKBOOK.name,
        user_id=1,
        confirmed_order_number=ORDER_NUMBER,
    )
    assert run2.id == run.id
    imp3 = commit_heroes_import_run(
        db,
        run2.id,
        user_id=1,
        confirm_import=True,
        confirm_sheet_match=True,
        confirmed_order_number=ORDER_NUMBER,
    )
    assert imp3.id == imp.id

    central = admin_client.get(f"/api/importations/{imp.id}/order-central")
    assert central.status_code == 200
    body = central.json()
    assert body["order"]["po_number"] == f"HEROES-{ORDER_NUMBER}"
    assert body.get("legacy_sheet_summary") is not None
    assert len(body["invoices"]) >= 1
    assert len(body["models"]) >= 1

    names = {
        (m.get("model_label") or m.get("supplier_sku") or "").lower()
        for m in body["models"]
        if m.get("model_label") or m.get("supplier_sku")
    }
    inv_names = {
        (i.get("product_sku") or i.get("description") or "").lower()
        for inv in body["invoices"]
        for i in inv["items"]
    }
    all_names = names | inv_names
    for exp in ("starlight", "aura", "fierce"):
        assert any(exp in n for n in all_names), f"{exp} ausente em {all_names}"

    snapshot = {
        "po_number": imp.po_number,
        "importation_id": imp.id,
        "currency": imp.currency,
        "invoice_count": inv_count,
        "invoice_item_count": item_count,
        "order_central": body,
        "preview_products": planilha_reference["invoice_products"],
        "da_spedire_products": planilha_reference["da_spedire_products"],
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    assert SNAPSHOT_PATH.is_file()


def test_reset_leaves_routes_navigable(db, admin_client, reset_env):
    reset_operational_test_data(db, skip_backup=True)
    for path in ("/api/importations", "/api/dashboard/summary", "/api/imports/heroes/xlsx/locate"):
        res = admin_client.get(path)
        assert res.status_code == 200
