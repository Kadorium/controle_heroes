"""L-UX-001-C — staging, match SKU, commit bloqueado."""

from __future__ import annotations

import uuid

import pytest

from app.core.enums import ReviewQueueStatus, StagingRowStatus
from app.models import ImportationItem, Product, ReviewQueueItem, StagingImportRow
from app.services.heroes_product_match import match_product
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_match_product_priority_supplier_code(db):
    code = f"starlight-{uuid.uuid4().hex[:6]}"
    p = Product(sku_code=f"M1-{uuid.uuid4().hex[:4]}", description="Outro", supplier_code=code)
    db.add(p)
    db.commit()
    assert match_product(db, code.upper()) == p


def test_c_staging_and_commit_block_resolve_flow(admin_client, db):
    uid = uuid.uuid4().hex[:8]
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"SKU {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    imp = admin_client.post(
        "/api/importations",
        json={"po_number": f"SKU-{uid}", "supplier_id": sup["id"], "currency": "EUR", "incoterm": "FOB"},
    ).json()
    content = build_ordine_758_xlsx()
    upload = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={"file": ("o.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    raw_id = upload.json()["raw_file_id"]
    admin_client.post(f"/api/importations/{imp['id']}/link-heroes-raw", json={"raw_file_id": raw_id})

    prev = admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")
    assert prev.status_code == 200
    body = prev.json()
    if not body.get("sku_review_open_count"):
        pytest.skip("Todos produtos já casaram no cadastro")

    blocked = admin_client.post(
        f"/api/importations/{imp['id']}/heroes-import/commit",
        json={"confirm_import": True, "confirm_sheet_match": True},
    )
    assert blocked.status_code == 400
    assert "SKUs" in blocked.json()["detail"]

    before_products = db.query(Product).count()
    staging = (
        db.query(StagingImportRow)
        .filter(
            StagingImportRow.raw_file_id == raw_id,
            StagingImportRow.status == StagingRowStatus.PENDING_REVIEW.value,
        )
        .first()
    )
    assert staging is not None
    data = staging.parsed_data_json
    assert data.get("issue_type") == "SKU_UNRESOLVED"
    assert data.get("invoice_number") is not None or data.get("context") == "da_spedire"

    sku_prod = Product(
        sku_code=f"RES-{uuid.uuid4().hex[:5]}",
        description=data["product_name_raw"],
        supplier_code=str(data["product_name_raw"]).lower(),
    )
    db.add(sku_prod)
    db.commit()

    resolved = admin_client.patch(
        f"/api/imports/staging/{staging.id}/resolve-sku",
        json={"product_id": sku_prod.id},
    )
    assert resolved.status_code == 200

    for name, code in (
        ("AURA POWER", "aura power"),
        ("palline beach", "palline beach"),
        ("WASHBAG EPIC", "washbag epic"),
        ("STARLIGHT 300", "starlight 300"),
    ):
        if not db.query(Product).filter(Product.supplier_code == code).first():
            db.add(Product(sku_code=f"X-{uuid.uuid4().hex[:4]}", description=name, supplier_code=code))
    db.commit()
    admin_client.get(f"/api/importations/{imp['id']}/heroes-import/preview")

    open_left = (
        db.query(ReviewQueueItem)
        .join(StagingImportRow, ReviewQueueItem.staging_row_id == StagingImportRow.id)
        .filter(
            StagingImportRow.raw_file_id == raw_id,
            ReviewQueueItem.status == ReviewQueueStatus.OPEN.value,
        )
        .count()
    )
    if open_left:
        pytest.skip("Ainda há SKUs pendentes após resolve parcial")

    commit = admin_client.post(
        f"/api/importations/{imp['id']}/heroes-import/commit",
        json={"confirm_import": True, "confirm_sheet_match": True},
    )
    assert commit.status_code == 200, commit.text
    assert db.query(Product).count() == before_products + 1
    assert db.query(ImportationItem).filter(ImportationItem.importation_id == imp["id"]).count() >= 1
