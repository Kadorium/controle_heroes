"""Testes Ordine 132 — revisão financeira, versato e cards operacionais."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.config import ROOT_DIR
from app.services.heroes_financial_preview import attach_financial_review_to_preview, build_financial_review
from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME, resolve_heroes_workbook_path
from app.services.heroes_xlsx_parser import parse_xlsx_sheet
from tests.fixtures.heroes_xlsx_builder import build_ordine_132_xlsx

REAL_WORKBOOK = ROOT_DIR / HEROES_WORKBOOK_FILENAME


def test_ordine_132_parses_versato_and_financial_review():
    preview = parse_xlsx_sheet(build_ordine_132_xlsx(), "ordine 132")
    assert preview.get("legacy_sheet_summary") is not None
    assert preview["legacy_sheet_summary"]["versato_amount"] == "198500"

    review = build_financial_review(preview)
    assert review["versato_amount"] == "198500"
    assert review["acconto_total"] == "9750"
    assert review["last_acconto_rimasto"] == "188750"
    assert review["expected_rimasto"] == "188750"
    assert review["requires_manual_review"] is False
    assert len(review["invoice_rows"]) == 3


def test_ordine_132_financial_review_warns_when_acconto_exceeds_versato():
    preview = parse_xlsx_sheet(build_ordine_132_xlsx(), "ordine 132")
    attach_financial_review_to_preview(preview)
    preview["legacy_sheet_summary"]["versato_amount"] = "1000"
    review = build_financial_review(preview)
    assert review["requires_manual_review"] is True
    assert any("excede versato" in w for w in review["warnings"])


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_ordine_132_preview_includes_financial_review(admin_client):
    uid = _uid()
    supplier = admin_client.post(
        "/api/suppliers",
        json={"name": f"Heroes132 {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"HEROES-132-{uid}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
        },
    ).json()

    content = build_ordine_132_xlsx()
    upload = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={
            "file": (
                "ordine132.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload.status_code == 201
    raw_id = upload.json()["raw_file_id"]

    link = admin_client.post(
        f"/api/importations/{imp['id']}/link-heroes-raw",
        json={"raw_file_id": raw_id},
    )
    assert link.status_code == 201

    prev = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev.status_code == 200
    body = prev.json()
    review = body["preview"].get("financial_review")
    assert review is not None
    assert review["versato_amount"] == "198500"


def test_order_central_brl_estimated_for_heroes_acconto(admin_client, db):
    from app.models import ImportationOrder, Invoice, Payment
    from app.services.order_central import build_order_central

    supplier = admin_client.post(
        "/api/suppliers",
        json={"name": f"BRL132 {_uid()}", "country": "IT", "currency_default": "EUR"},
    ).json()
    imp_resp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"HEROES-BRL-{_uid()}",
            "supplier_id": supplier["id"],
            "currency": "EUR",
        },
    ).json()
    imp_id = imp_resp["id"]

    imp = db.query(ImportationOrder).filter(ImportationOrder.id == imp_id).first()
    imp.estimated_total = Decimal("198500")
    inv = Invoice(
        importation_id=imp_id,
        invoice_type="PROFORMA",
        invoice_number="72",
        currency="EUR",
        amount=None,
        is_active=True,
    )
    db.add(inv)
    db.flush()
    db.add(
        Payment(
            invoice_id=inv.id,
            payment_type="ADVANCE",
            amount_foreign=Decimal("5500"),
            currency_foreign="EUR",
            receipt_reference="ACCONTO-72",
            is_active=True,
        )
    )
    db.commit()

    oc = build_order_central(db, imp_id)
    header = oc["operational_header"]
    assert header["settled_eur"] is not None
    assert Decimal(header["settled_eur"]) == Decimal("5500")
    assert header.get("settled_brl") is not None


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_real_ordine_132_parses_da_spedire_inline_layout():
    """Ordine 132 real: marcador inline na col D, sem cabeçalho listino/sconto."""
    path = resolve_heroes_workbook_path()
    assert path is not None
    preview = parse_xlsx_sheet(path.read_bytes(), "ordine 132")
    assert not any("Cabeçalho DA SPEDIRE não encontrado" in w for w in preview.get("warnings", []))
    da = preview["da_spedire"]
    assert len(da) >= 3
    names = {d["product_name_raw"].lower() for d in da}
    assert "starlight" in names
    assert "ison" in names
    assert "rebel" in names
    star = next(d for d in da if d["product_name_raw"].lower() == "starlight")
    assert star["quantity_to_dispatch"] == 0


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_real_ordine_132_duplicate_columns_uses_first_acconto_block():
    """Ordine 132 real tem cabecalho duplicado — parser deve usar 1o bloco (48000 na fatura 561)."""
    path = resolve_heroes_workbook_path()
    assert path is not None
    preview = parse_xlsx_sheet(path.read_bytes(), "ordine 132")
    b561 = next(b for b in preview["invoice_blocks"] if str(b.get("invoice_number", "")).startswith("561"))
    assert b561["acconto_payments"][0]["amount"] in ("48000", "48000.0")
    review = build_financial_review(preview)
    assert Decimal(review["acconto_total"]) == Decimal("196250")
    assert review["requires_manual_review"] is False
    assert review["last_acconto_rimasto"] in ("2250", "2250.0")
