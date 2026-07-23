from datetime import date

from app.services.product_name_normalize import (
    clean_product_description,
    launch_date_from_year,
    normalize_existing_products,
)
from app.models import Product


def test_remove_hash_and_extract_trailing_year():
    assert clean_product_description("#ARION 2026") == ("ARION", 2026)
    assert clean_product_description("#ISON 2023") == ("ISON", 2023)


def test_remove_hash_in_middle():
    assert clean_product_description("Fascia #HEADWOW FIERCE") == ("Fascia HEADWOW FIERCE", None)
    assert clean_product_description("Small Trolley #BABYLON") == ("Small Trolley BABYLON", None)


def test_extract_leading_year():
    assert clean_product_description("2025 Gravity ATLAS") == ("Gravity ATLAS", 2025)
    assert clean_product_description("2024 #CEU") == ("CEU", 2024)


def test_no_year_in_name():
    assert clean_product_description("Thunder FIERCE") == ("Thunder FIERCE", None)


def test_ambiguous_multiple_years():
    cleaned, year = clean_product_description("Model 2024 vs 2025")
    assert year is None
    assert cleaned == "Model 2024 vs 2025"


def test_launch_date_from_year():
    assert launch_date_from_year(2026) == date(2026, 1, 1)


def test_normalize_existing_products(db):
    p1 = Product(
        sku_code="NORM-1",
        description="#ARION 2026",
        product_group="Raquetes",
        lifecycle_status="ACTIVE",
        is_active=True,
    )
    p2 = Product(
        sku_code="NORM-2",
        description="Fascia #HEADWOW FIERCE",
        product_group="Acessorios",
        lifecycle_status="ACTIVE",
        is_active=True,
    )
    db.add_all([p1, p2])
    db.commit()

    result = normalize_existing_products(db)
    assert result["updated"] == 2

    db.refresh(p1)
    db.refresh(p2)
    assert p1.description == "ARION"
    assert p1.launch_date == date(2026, 1, 1)
    assert p2.description == "Fascia HEADWOW FIERCE"
    assert p2.launch_date is None
