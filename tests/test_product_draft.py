"""Testes de produtos rascunho (Entrega B)."""

from __future__ import annotations

import uuid

import pytest

from app.models import ImportationItem, ImportationOrder, Product, Supplier
from app.services.product_catalog import LIFECYCLE_ACTIVE, LIFECYCLE_DRAFT, list_products_for_combobox
from app.services.product_draft import (
    complete_draft_product,
    create_draft_product,
    link_draft_to_product,
    list_draft_products,
)

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_draft_excluded_from_combobox(db):
    uid = uuid.uuid4().hex[:6]
    draft = Product(
        sku_code=f"DRAFT-{uid}",
        description=f"Draft {uid}",
        lifecycle_status=LIFECYCLE_DRAFT,
    )
    active = Product(
        sku_code=f"ACT-{uid}",
        description=f"Active {uid}",
        lifecycle_status=LIFECYCLE_ACTIVE,
    )
    db.add_all([draft, active])
    db.commit()

    combobox = list_products_for_combobox(db)
    ids = {p.id for p in combobox}
    assert active.id in ids
    assert draft.id not in ids


def test_complete_draft_promotes_to_active(db):
    uid = uuid.uuid4().hex[:6]
    draft = create_draft_product(
        db,
        name_raw=f"bull-{uid}",
        category="RACKET",
        origin_run_id=99,
    )
    db.commit()

    completed = complete_draft_product(
        db,
        draft.id,
        sku_code=f"BULL-{uid}",
        description=f"Bull racket {uid}",
        category="RACKET",
        product_group="Raquetes",
        user_id=None,
    )
    db.commit()

    assert completed.lifecycle_status == LIFECYCLE_ACTIVE
    assert completed.sku_code == f"BULL-{uid}"
    assert completed.product_group == "Raquetes"


def test_complete_draft_updates_importation_item(db):
    uid = uuid.uuid4().hex[:6]
    sup = Supplier(name=f"S {uid}", country="IT", currency_default="EUR")
    db.add(sup)
    db.flush()
    imp = ImportationOrder(
        po_number=f"PO-{uid}",
        supplier_id=sup.id,
        currency="EUR",
        current_status="PO_CREATED",
    )
    draft = create_draft_product(db, name_raw=f"coch-{uid}", category="RACKET")
    db.add(imp)
    db.flush()
    item = ImportationItem(
        importation_id=imp.id,
        product_id=draft.id,
        description="old desc",
        quantity_ordered=10,
    )
    db.add(item)
    db.commit()

    complete_draft_product(
        db,
        draft.id,
        sku_code=f"COCH-{uid}",
        description=f"Coch {uid}",
        category="RACKET",
        product_group="Raquetes",
    )
    db.commit()
    db.refresh(item)

    assert item.product_id == draft.id
    assert item.description == f"Coch {uid}"


def test_link_draft_reassigns_importation_item(db):
    uid = uuid.uuid4().hex[:6]
    sup = Supplier(name=f"S2 {uid}", country="IT", currency_default="EUR")
    db.add(sup)
    db.flush()
    imp = ImportationOrder(
        po_number=f"PO2-{uid}",
        supplier_id=sup.id,
        currency="EUR",
        current_status="PO_CREATED",
    )
    draft = create_draft_product(db, name_raw=f"ison-{uid}", category="BALL")
    target = Product(
        sku_code=f"ISON-{uid}",
        description=f"Ison {uid}",
        category="BALL",
    )
    db.add_all([imp, target])
    db.flush()
    item = ImportationItem(
        importation_id=imp.id,
        product_id=draft.id,
        description=draft.description,
        quantity_ordered=5,
    )
    db.add(item)
    db.commit()

    link_draft_to_product(db, draft.id, target.id)
    db.commit()
    db.refresh(item)

    assert item.product_id == target.id
    refreshed_draft = db.query(Product).filter(Product.id == draft.id).first()
    assert refreshed_draft is not None
    assert refreshed_draft.is_active is False


def test_list_draft_products_api(admin_client, db):
    uid = uuid.uuid4().hex[:6]
    create_draft_product(db, name_raw=f"pending-{uid}", category="OTHER")
    db.commit()

    res = admin_client.get("/api/products/draft")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(f"pending-{uid}" in (row.get("description") or "") for row in body["items"])


def test_create_draft_from_staging_api(admin_client, db):
    from app.core.enums import StagingRowStatus
    from app.models import RawImportFile, StagingImportRow

    uid = uuid.uuid4().hex[:8]
    raw = RawImportFile(
        original_filename="t.xlsx",
        storage_path="tests/x.xlsx",
        file_hash=f"h-{uid}",
        source_system="heroes_xlsx",
    )
    db.add(raw)
    db.flush()
    staging = StagingImportRow(
        raw_file_id=raw.id,
        row_number=4,
        parsed_data_json={
            "issue_type": "SKU_UNRESOLVED",
            "product_name_raw": f"newsku-{uid}",
            "aliases": [f"newsku-{uid}"],
            "heroes_run_id": 1,
            "source": "heroes_xlsx",
            "suggested_category": "RACKET",
            "canonical_key": f"newsku|2026",
        },
        status=StagingRowStatus.PENDING_REVIEW.value,
        review_reason="test",
    )
    db.add(staging)
    db.commit()

    res = admin_client.post(f"/api/imports/staging/{staging.id}/create-draft")
    assert res.status_code == 200, res.text
    prod = res.json()
    assert prod["lifecycle_status"] == "DRAFT"
    assert f"newsku-{uid}" in prod["description"]

    listed = admin_client.get("/api/products/draft").json()
    assert any(row["id"] == prod["id"] for row in listed["items"])

    complete = admin_client.post(
        f"/api/products/{prod['id']}/complete",
        json={
            "sku_code": f"NS-{uid}",
            "description": f"New SKU {uid}",
            "category": "RACKET",
            "product_group": "Teste",
        },
    )
    assert complete.status_code == 200
    assert complete.json()["lifecycle_status"] == "ACTIVE"

    listed_after = admin_client.get("/api/products/draft").json()
    assert not any(row["id"] == prod["id"] for row in listed_after["items"])
