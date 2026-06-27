"""L-UX-001-B — merge Heroes na ordem ATTACHED."""

from __future__ import annotations

import uuid

import pytest

from sqlalchemy import func

from app.config import ROOT_DIR
from app.core.enums import HeroesImportRunStatus
from app.models import ImportationItem, ImportationOrder, Invoice, Payment, Product, StagingImportRow
from app.core.enums import StagingRowStatus
from app.services.heroes_workbook_paths import HEROES_WORKBOOK_FILENAME
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx

REAL_WORKBOOK = ROOT_DIR / HEROES_WORKBOOK_FILENAME


def _resolve_all_open_staging(admin_client, db, raw_id: int, *, show_product_id: int | None = None) -> None:
    """Resolve grupos staging pendentes (isolamento entre testes)."""
    from app.services.heroes_product_match import match_product

    pending = (
        db.query(StagingImportRow)
        .filter(
            StagingImportRow.raw_file_id == raw_id,
            StagingImportRow.status == StagingRowStatus.PENDING_REVIEW.value,
        )
        .all()
    )
    for staging in pending:
        data = staging.parsed_data_json or {}
        product_id = None
        if show_product_id and data.get("canonical_key") == "show|2026":
            product_id = show_product_id
        else:
            name = str(data.get("product_name_raw") or "item")
            matched = match_product(db, name)
            if matched:
                product_id = matched.id
            else:
                existing = db.query(Product).filter(Product.supplier_code == name.lower()).first()
                if existing:
                    product_id = existing.id
                else:
                    p = Product(
                        sku_code=f"TST-{uuid.uuid4().hex[:5]}",
                        description=name,
                        supplier_code=name.lower(),
                    )
                    db.add(p)
                    db.flush()
                    product_id = p.id
        db.commit()
        admin_client.patch(
            f"/api/imports/staging/{staging.id}/resolve-sku",
            json={"product_id": product_id},
        )


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def _manual_order_with_link(admin_client, db, content: bytes, *, po: str | None = None):
    uid = uuid.uuid4().hex[:8]
    po = po or f"MANUAL-{uid}"
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"Heroes Merge {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": po,
            "supplier_id": sup["id"],
            "currency": "EUR",
            "incoterm": "FOB",
        },
    ).json()
    upload = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={
            "file": (
                "ord758.xlsx",
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
    return imp, link.json(), raw_id


def test_b1_preview_attached_same_run_id(admin_client, db):
    content = build_ordine_758_xlsx()
    imp, link, _ = _manual_order_with_link(admin_client, db, content)
    run_id = link["run_id"]

    prev = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev.status_code == 200, prev.text
    body = prev.json()
    assert body["run_id"] == run_id
    assert body["status"] == HeroesImportRunStatus.PREVIEW.value
    assert body["preview"].get("invoice_blocks")
    assert len(body["preview"]["invoice_blocks"]) >= 1


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="Planilha real ausente")
def test_b2_merge_commit_preserves_po_and_creates_entities(admin_client, db):
    content = REAL_WORKBOOK.read_bytes()
    imp, link, _ = _manual_order_with_link(admin_client, db, content, po="ORD-758-MERGE")
    po_before = imp["po_number"]

    prev = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev.status_code == 200

    db.query(Product).filter(Product.supplier_code.isnot(None)).count()
    products = db.query(Product).all()
    for p in products:
        if p.description and p.description.lower() in ("starlight", "aura", "starlight 300"):
            p.supplier_code = p.description.lower()
    db.commit()

    prev2 = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev2.status_code == 200
    if prev2.json().get("sku_review_open_count", 0) > 0:
        pytest.skip("SKUs pendentes — resolver na sub-tarefa C e2e")

    commit = admin_client.post(
        f"/api/importations/{imp['id']}/heroes-import/commit",
        json={"confirm_import": True, "confirm_sheet_match": True},
    )
    assert commit.status_code == 200, commit.text

    imp_row = db.query(ImportationOrder).filter(ImportationOrder.id == imp["id"]).first()
    assert imp_row.po_number == po_before
    invoices = db.query(Invoice).filter(Invoice.importation_id == imp["id"]).count()
    items = db.query(ImportationItem).filter(ImportationItem.importation_id == imp["id"]).count()
    assert invoices >= 1
    assert items >= 1

    payments = (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.importation_id == imp["id"])
        .count()
    )
    assert payments >= 1

    commit2 = admin_client.post(
        f"/api/importations/{imp['id']}/heroes-import/commit",
        json={"confirm_import": True, "confirm_sheet_match": True},
    )
    assert commit2.status_code == 200


def test_b2_preexisting_item_qty_summed(admin_client, db):
    content = build_ordine_758_xlsx()
    imp, link, raw_id = _manual_order_with_link(admin_client, db, content)
    star = Product(
        sku_code=f"STAR-{uuid.uuid4().hex[:6]}",
        description="STARLIGHT 300",
        supplier_code=f"starlight-300-{uuid.uuid4().hex[:6]}",
    )
    db.add(star)
    db.flush()
    for other in db.query(Product).filter(
        func.lower(Product.description) == "starlight 300",
        Product.id != star.id,
    ):
        other.is_active = False
    db.add(
        ImportationItem(
            importation_id=imp["id"],
            product_id=star.id,
            supplier_sku=star.sku_code,
            description="STARLIGHT 300",
            quantity_ordered=2,
        )
    )
    for name, code in (
        ("AURA POWER", "aura power"),
        ("palline beach", "palline beach"),
        ("WASHBAG EPIC", "washbag epic"),
    ):
        if not db.query(Product).filter(Product.supplier_code == code).first():
            db.add(Product(sku_code=f"SKU-{uuid.uuid4().hex[:5]}", description=name, supplier_code=code))
    show = Product(
        sku_code=f"SHOW-{uuid.uuid4().hex[:5]}",
        description="SHOW 2026",
        category="RACKET",
        launch_date=__import__("datetime").date(2026, 1, 1),
    )
    db.add(show)
    db.commit()

    prev = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev.status_code == 200
    _resolve_all_open_staging(admin_client, db, raw_id, show_product_id=show.id)
    admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")

    commit = admin_client.post(
        f"/api/importations/{imp['id']}/heroes-import/commit",
        json={"confirm_import": True, "confirm_sheet_match": True},
    )
    assert commit.status_code == 200, commit.text

    item = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == imp["id"], ImportationItem.product_id == star.id)
        .all()
    )
    assert len(item) == 1
    assert item[0].quantity_ordered == 12


def test_b_merge_invoice_conflict_warning(admin_client, db):
    """Fatura já cadastrada na ordem manual → warning, sem duplicar Invoice."""
    content = build_ordine_758_xlsx()
    imp, _, raw_id = _manual_order_with_link(admin_client, db, content)
    db.add(
        Invoice(
            importation_id=imp["id"],
            invoice_number="F-100",
            invoice_type="PROFORMA",
            currency="EUR",
        )
    )
    for name, code in (
        ("STARLIGHT 300", "starlight 300"),
        ("AURA POWER", "aura power"),
        ("palline beach", "palline beach"),
        ("WASHBAG EPIC", "washbag epic"),
    ):
        if not db.query(Product).filter(Product.supplier_code == code).first():
            db.add(Product(sku_code=f"SKU-{uuid.uuid4().hex[:5]}", description=name, supplier_code=code))
    show = Product(
        sku_code=f"SHOW-{uuid.uuid4().hex[:5]}",
        description="SHOW 2026",
        category="RACKET",
        launch_date=__import__("datetime").date(2026, 1, 1),
    )
    db.add(show)
    db.commit()

    prev = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev.status_code == 200
    _resolve_all_open_staging(admin_client, db, raw_id, show_product_id=show.id)
    admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    open_after = (
        db.query(StagingImportRow)
        .filter(
            StagingImportRow.raw_file_id == raw_id,
            StagingImportRow.status == StagingRowStatus.PENDING_REVIEW.value,
        )
        .count()
    )
    if open_after > 0:
        pytest.skip("SKUs pendentes no cadastro de teste")

    commit = admin_client.post(
        f"/api/importations/{imp['id']}/heroes-import/commit",
        json={"confirm_import": True, "confirm_sheet_match": True},
    )
    assert commit.status_code == 200, commit.text
    warnings = commit.json().get("merge_warnings") or []
    assert any("F-100" in w and "já existe" in w for w in warnings)

    dup_count = (
        db.query(Invoice)
        .filter(
            Invoice.importation_id == imp["id"],
            Invoice.invoice_number == "F-100",
            Invoice.is_active.is_(True),
        )
        .count()
    )
    assert dup_count == 1
