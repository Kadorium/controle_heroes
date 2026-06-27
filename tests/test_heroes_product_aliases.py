"""Testes aliases Heroes no produto."""

import uuid

from app.models import Product
from app.services.heroes_product_aliases import (
    match_product_by_stored_aliases,
    merge_heroes_aliases_into_notes,
    parse_heroes_aliases,
    save_heroes_aliases_on_product,
)


def test_parse_and_merge_aliases():
    notes = merge_heroes_aliases_into_notes(None, ["show 26", "show"])
    assert parse_heroes_aliases(notes) == {"show", "show 26"}
    notes2 = merge_heroes_aliases_into_notes(notes, ["show26"])
    assert parse_heroes_aliases(notes2) == {"show", "show 26", "show26"}


def test_match_by_stored_aliases(db):
    p = Product(
        sku_code=f"AL-{uuid.uuid4().hex[:5]}",
        description="SHOW 2026",
        commercial_notes=merge_heroes_aliases_into_notes(None, ["show", "show 26"]),
    )
    db.add(p)
    db.commit()
    assert match_product_by_stored_aliases(db, "show") == p
    assert match_product_by_stored_aliases(db, "SHOW 26") == p


def test_save_aliases_on_resolve(db):
    p = Product(sku_code=f"SV-{uuid.uuid4().hex[:5]}", description="SHOW 2026")
    db.add(p)
    db.flush()
    save_heroes_aliases_on_product(p, ["show 26", "show26"], extra_aliases=["show"])
    db.commit()
    assert "show" in parse_heroes_aliases(p.commercial_notes)
