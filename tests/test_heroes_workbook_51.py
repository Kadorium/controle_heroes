"""Testes Fase pós-MVP 5.1 — profiling, parse it-IT, paths, export."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
import zipfile

from app.config import ROOT_DIR
from app.core.enums import HeroesSheetType
from app.core.parse_it import parse_it_date, parse_it_number
from app.services.heroes_order_format_v1 import export_normalized_xlsx, export_normalized_zip, preview_to_canonical
from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME, resolve_heroes_workbook_path
from app.services.heroes_workbook_profiler import profile_workbook_file
from app.services.heroes_xlsx_parser import parse_xlsx_sheet
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx, build_ordine_759_xlsx


REAL_WORKBOOK = ROOT_DIR / HEROES_WORKBOOK_FILENAME
REAL_RAW = ROOT_DIR / "data" / "raw" / HEROES_WORKBOOK_FILENAME


@pytest.fixture
def reset_env(monkeypatch):
    from app.config import get_settings
    from app.services.reset_operational_data import RESET_ENV_VAR

    get_settings.cache_clear()
    monkeypatch.setenv(RESET_ENV_VAR, "1")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_parse_it_number_euro_thousands():
    assert parse_it_number("10.000,00 €") == Decimal("10000.00")
    assert parse_it_number("1.234,56") == Decimal("1234.56")
    assert parse_it_number(10000) == Decimal("10000")


def test_parse_it_date_dd_mm():
    iso, review = parse_it_date("03/04")
    assert iso is not None
    assert review is True
    iso2, review2 = parse_it_date("15/03/2025")
    assert iso2 == "2025-03-15"
    assert review2 is False


def test_resolve_workbook_root_first(tmp_path, monkeypatch):
    fake = tmp_path / HEROES_WORKBOOK_FILENAME
    fake.write_bytes(b"x")
    monkeypatch.setattr(
        "app.services.heroes_workbook_paths.SEARCH_PATHS",
        (fake, tmp_path / "data" / "raw" / HEROES_WORKBOOK_FILENAME),
    )
    assert resolve_heroes_workbook_path() == fake.resolve()


def test_resolve_workbook_data_raw_second(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw" / HEROES_WORKBOOK_FILENAME
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"y")
    monkeypatch.setattr(
        "app.services.heroes_workbook_paths.SEARCH_PATHS",
        (tmp_path / HEROES_WORKBOOK_FILENAME, raw),
    )
    assert resolve_heroes_workbook_path() == raw.resolve()


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente na raiz")
def test_real_workbook_found_at_root():
    path = resolve_heroes_workbook_path()
    assert path is not None
    assert path.name == HEROES_WORKBOOK_FILENAME
    assert path.parent == ROOT_DIR


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_profiling_lists_all_sheets():
    report = profile_workbook_file(REAL_WORKBOOK)
    assert report["sheet_count"] == 14
    names = {s["sheet_name"] for s in report["sheets"]}
    assert "Ordine 758" in names
    assert "RITIRI HK" in names
    assert "2026" in names


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_profiling_classifies_ordine_758():
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == "Ordine 758")
    assert sh["sheet_type"] == HeroesSheetType.ORDER.value
    assert sh["order_number_from_content"] == "758"
    assert sh["recommendation"] == "importar"


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_profiling_classifies_ritiri_hk():
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == "RITIRI HK")
    assert sh["sheet_type"] == HeroesSheetType.LOGISTICS.value


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_profiling_classifies_2026():
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == "2026")
    assert sh["sheet_type"] == HeroesSheetType.FINANCIAL_ANNUAL.value


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_profiling_detects_ordine_759_divergence():
    report = profile_workbook_file(REAL_WORKBOOK)
    sh = next(s for s in report["sheets"] if s["sheet_name"] == "Ordine 759")
    assert sh["order_number_from_sheet_name"] == "759"
    assert sh["order_number_from_content"] == "907"
    assert sh["order_number_divergence"] is True
    assert sh["recommendation"] == "revisão manual"


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_profiling_no_db_writes():
    report = profile_workbook_file(REAL_WORKBOOK)
    assert report["database_writes"] is False
    assert report["read_only_mode"] is True


def test_parser_content_order_over_name_on_divergence():
    """Conteúdo prevalece sobre nome da sheet para order_number."""
    content = build_ordine_759_xlsx()
    preview = parse_xlsx_sheet(content, "Ordine 759")
    assert preview["order_number_from_sheet_name"] == "759"
    assert preview["order_number_from_content"] == "907"
    assert preview["order_number_divergence"] is True
    assert preview["order_number"] == "907"


def test_articolo_header_not_racket_only():
    preview = parse_xlsx_sheet(build_ordine_759_xlsx(), "Ordine 759")
    item = next(i for i in preview["invoice_items"] if i["product_name_raw"] == "OLYMPIA")
    assert item["source_column_product_header"] == "articolo"


def test_non_racket_not_forced_racket():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    wash = next(i for i in preview["invoice_items"] if "WASHBAG" in i["product_name_raw"])
    assert wash["suggested_category"] != "RACKET"


def test_export_normalized_xlsx_and_zip():
    preview = parse_xlsx_sheet(build_ordine_758_xlsx(), "Ordine 758")
    canonical = preview_to_canonical(preview)
    xlsx = export_normalized_xlsx(canonical)
    assert len(xlsx) > 1000
    z = export_normalized_zip(canonical)
    with zipfile.ZipFile(BytesIO(z)) as zf:
        names = zf.namelist()
    assert "orders.csv" in names
    assert "invoice_items.csv" in names


def test_commit_requires_confirmation(admin_client, db, reset_env):
    from app.services.reset_operational_data import reset_operational_test_data

    reset_operational_test_data(db, skip_backup=True)
    content = build_ordine_758_xlsx()
    up = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={"file": ("t.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    raw_id = up.json()["raw_file_id"]
    prev = admin_client.post(
        "/api/imports/heroes/xlsx/preview",
        json={"raw_file_id": raw_id, "sheet_name": "Ordine 758"},
    )
    run_id = prev.json()["run_id"]
    bad = admin_client.post("/api/imports/heroes/xlsx/commit", json={"run_id": run_id})
    assert bad.status_code == 400


def test_load_local_endpoint(admin_client):
    if not REAL_WORKBOOK.is_file() and not REAL_RAW.is_file():
        pytest.skip("Planilha real ausente")
    res = admin_client.post("/api/imports/heroes/xlsx/load-local")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["workbook_profile"]["sheet_count"] == 14


def test_preview_returns_canonical(admin_client, db, reset_env):
    from app.services.reset_operational_data import reset_operational_test_data

    reset_operational_test_data(db, skip_backup=True)
    content = build_ordine_758_xlsx()
    up = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={"file": ("t.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    raw_id = up.json()["raw_file_id"]
    prev = admin_client.post(
        "/api/imports/heroes/xlsx/preview",
        json={"raw_file_id": raw_id, "sheet_name": "Ordine 758"},
    )
    assert prev.json().get("canonical") is not None
    assert prev.json()["canonical"]["format_version"] == "Heroes Order Import Format v1"
