"""RUX-3A — Catalog identity refs (SKU sequence, tax_id, supplier_product_refs)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.catalog import public as catalog_public
from app.catalog.errors import CatalogValidationError, SkuDuplicate, SupplierTaxIdDuplicate
from app.catalog.models import SupplierProductRef


def test_allocate_next_sku_uniqueness(db):
    sku1 = catalog_public.allocate_next_sku(db)
    sku2 = catalog_public.allocate_next_sku(db)
    db.commit()
    assert sku1.startswith("EPIC-")
    assert sku2.startswith("EPIC-")
    assert sku1 != sku2


def test_create_product_auto_allocates_sku(db):
    p = catalog_public.create_product(db, description="Auto SKU item")
    db.commit()
    assert p.sku.startswith("EPIC-")


def test_create_product_explicit_sku_still_validates_uniqueness(db):
    catalog_public.create_product(db, sku="MANUAL-1", description="first")
    db.commit()
    with pytest.raises(SkuDuplicate):
        catalog_public.create_product(db, sku="MANUAL-1", description="second")


def test_supplier_tax_id_requires_country(db):
    with pytest.raises(CatalogValidationError, match="country_code"):
        catalog_public.create_supplier(db, name="No Country", tax_id="12345678901")


def test_supplier_tax_id_unique_per_country(db):
    catalog_public.create_supplier(
        db, name="IT Supplier A", country_code="IT", tax_id="IT 12345678901"
    )
    db.commit()
    with pytest.raises(SupplierTaxIdDuplicate):
        catalog_public.create_supplier(
            db, name="IT Supplier B", country_code="IT", tax_id="12345678901"
        )


def test_supplier_tax_id_it_normalization(db):
    s = catalog_public.create_supplier(
        db, name="IT Supplier Norm", country_code="IT", tax_id="IT 98765432109"
    )
    db.commit()
    assert s.tax_id == "98765432109"


def test_supplier_tax_id_different_country_allowed(db):
    catalog_public.create_supplier(
        db, name="IT Supplier X", country_code="IT", tax_id="11122233344"
    )
    br = catalog_public.create_supplier(
        db, name="BR Supplier", country_code="BR", tax_id="11122233344"
    )
    db.commit()
    assert br.tax_id == "11122233344"


def test_ean_ref_unique_constraint(db):
    sup = catalog_public.create_supplier(db, name="Ref Supplier", country_code="IT")
    p1 = catalog_public.create_product(db, sku="REF-P1", description="Product 1")
    p2 = catalog_public.create_product(db, sku="REF-P2", description="Product 2")
    db.commit()

    catalog_public.upsert_supplier_product_ref(
        db,
        supplier_id=sup.id,
        product_id=p1.id,
        code_kind="EAN",
        match_mode="AUTO",
        external_code="7890000012234",
    )
    db.commit()

    dup = SupplierProductRef(
        supplier_id=sup.id,
        product_id=p2.id,
        code_kind="EAN",
        match_mode="AUTO",
        external_code="7890-0000-12234",
        normalized_external_code="7890000012234",
        is_active=True,
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()


def test_class_ref_unique_with_fingerprint(db):
    sup = catalog_public.create_supplier(db, name="Class Supplier", country_code="IT")
    p1 = catalog_public.create_product(db, sku="CLASS-P1", description="Product 1")
    p2 = catalog_public.create_product(db, sku="CLASS-P2", description="Product 2")
    db.commit()

    catalog_public.upsert_supplier_product_ref(
        db,
        supplier_id=sup.id,
        product_id=p1.id,
        code_kind="SUPPLIER_CLASS",
        match_mode="SUGGEST",
        external_code="CTM-BL-M",
        external_description="Blue M",
    )
    db.commit()

    from app.catalog.normalization import compute_description_fingerprint

    dup = SupplierProductRef(
        supplier_id=sup.id,
        product_id=p2.id,
        code_kind="SUPPLIER_CLASS",
        match_mode="SUGGEST",
        external_code="ctm-bl-m",
        normalized_external_code="CTM-BL-M",
        external_description="blue   m",
        description_fingerprint=compute_description_fingerprint("blue   m"),
        is_active=True,
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()


def test_class_ref_same_code_different_description_allowed(db):
    sup = catalog_public.create_supplier(db, name="Class Supplier 2", country_code="IT")
    p1 = catalog_public.create_product(db, sku="CLASS-P3", description="Product 3")
    p2 = catalog_public.create_product(db, sku="CLASS-P4", description="Product 4")
    db.commit()

    r1 = catalog_public.upsert_supplier_product_ref(
        db,
        supplier_id=sup.id,
        product_id=p1.id,
        code_kind="SUPPLIER_CLASS",
        match_mode="SUGGEST",
        external_code="CTM-BL-M",
        external_description="Blue M",
    )
    r2 = catalog_public.upsert_supplier_product_ref(
        db,
        supplier_id=sup.id,
        product_id=p2.id,
        code_kind="SUPPLIER_CLASS",
        match_mode="SUGGEST",
        external_code="CTM-BL-M",
        external_description="Blue L",
    )
    db.commit()
    assert r1.id != r2.id


def test_match_auto_ean(db):
    sup = catalog_public.create_supplier(db, name="Match Supplier", country_code="IT")
    p = catalog_public.create_product(db, sku="MATCH-P1", description="Match product")
    db.commit()

    catalog_public.upsert_supplier_product_ref(
        db,
        supplier_id=sup.id,
        product_id=p.id,
        code_kind="EAN",
        match_mode="AUTO",
        external_code="7890000012258",
    )
    db.commit()

    hit = catalog_public.match_supplier_product_ref_auto(
        db, supplier_id=sup.id, code_kind="EAN", external_code="7890-0000-12258"
    )
    assert hit is not None
    assert hit.product_id == p.id


def test_match_suggest_class(db):
    sup = catalog_public.create_supplier(db, name="Suggest Supplier", country_code="IT")
    p = catalog_public.create_product(db, sku="SUG-P1", description="Suggest product")
    db.commit()

    catalog_public.upsert_supplier_product_ref(
        db,
        supplier_id=sup.id,
        product_id=p.id,
        code_kind="SUPPLIER_CLASS",
        match_mode="SUGGEST",
        external_code="CTM-BK-M",
        external_description="Black M",
    )
    db.commit()

    hits = catalog_public.match_supplier_product_ref_suggest(
        db,
        supplier_id=sup.id,
        code_kind="SUPPLIER_CLASS",
        external_code="ctm-bk-m",
        external_description="black m",
    )
    assert len(hits) == 1
    assert hits[0].product_id == p.id


def test_allocate_sku_api(admin_client):
    r = admin_client.post("/api/products/allocate-sku")
    assert r.status_code == 200, r.text
    assert r.json()["sku"].startswith("EPIC-")


def test_create_supplier_with_tax_id_api(admin_client):
    r = admin_client.post(
        "/api/suppliers",
        json={"name": "API Tax Supplier", "country_code": "IT", "tax_id": "99887766554"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["tax_id"] == "99887766554"


def test_create_product_without_sku_api(admin_client):
    r = admin_client.post("/api/products", json={"description": "API auto SKU"})
    assert r.status_code == 201, r.text
    assert r.json()["sku"].startswith("EPIC-")
