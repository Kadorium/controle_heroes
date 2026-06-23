"""Testes parser Heroes XLSX e categorias."""

from datetime import datetime
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.core.enums import HeroesSheetType, ProductCategory
from app.services.heroes_xlsx_parser import (
    detect_sheet_type,
    excel_date_to_iso,
    list_xlsx_sheets,
    parse_xlsx_sheet,
)
from app.services.product_category import suggest_product_category
from app.services.reset_operational_data import RESET_ENV_VAR, reset_operational_test_data
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx, build_ordine_759_xlsx


@pytest.fixture
def reset_env(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv(RESET_ENV_VAR, "1")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_detect_order_sheets():
    sheets = list_xlsx_sheets(build_ordine_758_xlsx())
    names = {s["sheet_name"]: s["sheet_type"] for s in sheets}
    assert names["Ordine 758"] == HeroesSheetType.ORDER.value
    assert names["RITIRI HK"] == HeroesSheetType.LOGISTICS.value
    assert names["2025"] == HeroesSheetType.FINANCIAL_ANNUAL.value


def test_parse_ordine_758_order_number():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    assert preview["order_number"] == "758"
    assert len(preview["invoice_items"]) >= 3


def test_invoice_inheritance():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    aura = next(i for i in preview["invoice_items"] if i["product_name_raw"] == "AURA POWER")
    assert aura["invoice_number"] == "F-100"
    assert aura["invoice_date"] is not None


def test_empty_not_zero():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    wash = next(i for i in preview["invoice_items"] if "WASHBAG" in i["product_name_raw"])
    assert wash["acconto_amount"] is None


def test_da_spedire_block():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    assert len(preview["da_spedire"]) >= 2
    star = next(d for d in preview["da_spedire"] if "STARLIGHT" in d["product_name_raw"])
    assert star["quantity_to_dispatch"] == 8
    assert star["invoice_price"] == "100"


def test_articolo_column_ordine_759():
    preview = parse_xlsx_sheet(build_ordine_759_xlsx(), "Ordine 759")
    assert any(i["product_name_raw"] == "OLYMPIA" for i in preview["invoice_items"])


def test_excel_serial_date():
    assert excel_date_to_iso(datetime(2025, 3, 10)) == "2025-03-10"
    assert excel_date_to_iso(45726) == "2025-03-10"


def test_category_racket():
    cat, conf, _ = suggest_product_category("STARLIGHT 300")
    assert cat == ProductCategory.RACKET.value
    assert conf >= 0.5


def test_category_ball():
    cat, _, _ = suggest_product_category("palline beach")
    assert cat == ProductCategory.BALL.value


def test_category_bag():
    cat, _, _ = suggest_product_category("WASHBAG EPIC")
    assert cat == ProductCategory.BAG_ACCESSORY.value


def test_category_pickleball():
    cat, _, _ = suggest_product_category("PICKLEBALL BALL PK-01")
    assert cat in (ProductCategory.PICKLEBALL.value, ProductCategory.BALL.value)


def test_category_unknown():
    cat, conf, rev = suggest_product_category("ITEM COMPLETAMENTE DESCONHECIDO 999")
    assert cat == ProductCategory.OTHER.value
    assert conf <= 0.5
    assert rev is not None


def test_logistics_sheet():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "RITIRI HK")
    lines = preview["logistics_preview"]["logistics_lines"]
    assert any(l["product_name_raw"] == "WASHBAG EPIC" for l in lines)


def test_financial_preview_auxiliary():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "2025")
    assert preview["financial_preview"] is not None
    assert preview["financial_preview"]["payments_preview"]


def test_preview_no_persist(db):
    """Preview via parser não grava ordem."""
    from app.models import ImportationOrder

    before = db.query(ImportationOrder).count()
    parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    assert db.query(ImportationOrder).count() == before


def test_commit_creates_order(admin_client, db):
    from app.models import RawImportFile
    from app.services.heroes_import import save_raw_import_file
    from app.services.heroes_xlsx_import import preview_xlsx_sheet
    from app.services.heroes_xlsx_commit import commit_heroes_import_run

    content = build_ordine_758_xlsx()
    fh, path = save_raw_import_file(content, "ordine758.xlsx")
    raw = RawImportFile(
        file_hash=fh,
        storage_path=path,
        original_filename="ordine758.xlsx",
        source_system="HEROES_XLSX",
    )
    db.add(raw)
    db.flush()
    run = preview_xlsx_sheet(
        db,
        raw_file_id=raw.id,
        sheet_name="Ordine 758",
        content=content,
        filename="ordine758.xlsx",
        user_id=1,
    )
    imp = commit_heroes_import_run(
        db, run.id, user_id=1,
        confirm_import=True, confirm_sheet_match=True,
        confirmed_order_number="758",
    )
    assert imp.po_number == "HEROES-758"
    assert imp.invoices
    assert imp.items


def test_idempotency_same_sheet(db):
    from app.models import HeroesImportRun, RawImportFile
    from app.services.heroes_import import save_raw_import_file
    from app.services.heroes_xlsx_import import preview_xlsx_sheet
    from app.services.heroes_xlsx_commit import commit_heroes_import_run

    content = build_ordine_759_xlsx()
    fh, path = save_raw_import_file(content, "ordine759-idem.xlsx")
    raw = RawImportFile(
        file_hash=fh,
        storage_path=path,
        original_filename="ordine759-idem.xlsx",
        source_system="HEROES_XLSX",
    )
    db.add(raw)
    db.flush()
    run1 = preview_xlsx_sheet(
        db, raw_file_id=raw.id, sheet_name="Ordine 759", content=content,
        filename="ordine759-idem.xlsx", user_id=1,
    )
    commit_heroes_import_run(
        db, run1.id, user_id=1,
        confirm_import=True, confirm_sheet_match=True,
        confirmed_order_number="907",
    )
    run2 = preview_xlsx_sheet(
        db, raw_file_id=raw.id, sheet_name="Ordine 759", content=content,
        filename="ordine759-idem.xlsx", user_id=1,
    )
    assert run2.id == run1.id
    assert run2.status == "COMMITTED"


def test_api_xlsx_upload_preview_commit(admin_client, db, reset_env):
    reset_operational_test_data(db, skip_backup=True)

    content = build_ordine_758_xlsx()
    up = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={"file": ("ordine758.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert up.status_code == 201, up.text
    raw_id = up.json()["raw_file_id"]
    prev = admin_client.post(
        "/api/imports/heroes/xlsx/preview",
        json={"raw_file_id": raw_id, "sheet_name": "Ordine 758"},
    )
    assert prev.status_code == 200, prev.text
    run_id = prev.json()["run_id"]
    assert prev.json()["order_number"] == "758"
    commit = admin_client.post(
        "/api/imports/heroes/xlsx/commit",
        json={
            "run_id": run_id,
            "confirm_import": True,
            "confirm_sheet_match": True,
            "confirmed_order_number": "758",
        },
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["po_number"] == "HEROES-758"
