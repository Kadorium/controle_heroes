"""Testes de match_product — exclusão de rascunhos e candidatos parciais."""

from __future__ import annotations

import uuid

from app.models import Product
from app.services.heroes_product_match import (
    MATCH_AUTO_RESOLVE_SCORE,
    MATCH_SUGGEST_MIN_SCORE,
    find_best_product_candidate,
    match_product,
)
from app.services.product_catalog import LIFECYCLE_DRAFT


def test_match_product_ignores_draft(db):
    code = f"draft-hit-{uuid.uuid4().hex[:6]}"
    draft = Product(
        sku_code=f"DRAFT-{uuid.uuid4().hex[:5]}",
        description=code,
        supplier_code=code,
        lifecycle_status=LIFECYCLE_DRAFT,
    )
    active = Product(
        sku_code=f"ACT-{uuid.uuid4().hex[:5]}",
        description=f"Active {code}",
        supplier_code=f"active-{code}",
    )
    db.add_all([draft, active])
    db.commit()

    assert match_product(db, code) is None
    assert match_product(db, f"active-{code}") == active


def test_find_best_product_candidate_partial_match(db):
    uid = uuid.uuid4().hex[:5]
    show = Product(
        sku_code=f"SHOW26-{uid}",
        description="SHOW 2026",
        category="APPAREL",
        launch_date=__import__("datetime").date(2026, 1, 1),
    )
    db.add(show)
    db.commit()

    best = find_best_product_candidate(db, "show 26", category_hint="RACKET")
    assert best is not None
    assert best.product.id == show.id
    assert MATCH_SUGGEST_MIN_SCORE <= best.score < MATCH_AUTO_RESOLVE_SCORE


def test_is_slug_shell_detects_import_slug(db):
    from app.services.heroes_product_match import is_slug_shell

    slug = Product(
        sku_code="ISON",
        description="ison",
        category="RACKET",
        product_group="Sem grupo",
    )
    quality = Product(
        sku_code="HEROES-BT-ISON-2025",
        description="ISON",
        category="RAQUETE",
        product_group="RAQUETES",
        launch_date=__import__("datetime").date(2025, 1, 1),
        commercial_notes="Oficial",
    )
    assert is_slug_shell(slug) is True
    assert is_slug_shell(quality) is False


def test_find_product_candidates_ignores_slug_shell(db):
    from app.services.heroes_product_match import find_product_candidates, is_slug_shell

    uid = uuid.uuid4().hex[:5]
    slug = Product(sku_code=f"SHOW-{uid}", description=f"show-{uid}", category="RACKET")
    quality = Product(
        sku_code=f"SHOW26-{uid}",
        description="SHOW 2026",
        category="RACKET",
        product_group="RAQUETES",
        launch_date=__import__("datetime").date(2026, 1, 1),
        commercial_notes="cadastro epic",
    )
    db.add_all([slug, quality])
    db.commit()
    assert is_slug_shell(slug)

    candidates = find_product_candidates(db, "show 26", category_hint="RACKET")
    assert candidates
    assert all(c.product.id != slug.id for c in candidates)
    assert candidates[0].product.id == quality.id


def test_build_sku_triage_groups_shows_all_without_auto_resolve(db):
    from app.services.heroes_xlsx_staging import build_sku_triage_groups, sync_heroes_xlsx_staging
    from app.models import HeroesImportRun, RawImportFile

    uid = uuid.uuid4().hex[:5]
    show = Product(
        sku_code=f"SHOW-P-{uid}",
        description=f"SHOW 2026 {uid}",
        category="APPAREL",
        launch_date=__import__("datetime").date(2026, 1, 1),
    )
    db.add(show)
    db.commit()

    raw = RawImportFile(
        original_filename="t.xlsx",
        storage_path="tests/fixtures/x.xlsx",
        file_hash=f"hash-{uid}",
        source_system="heroes_xlsx",
    )
    db.add(raw)
    db.flush()
    run = HeroesImportRun(
        raw_file_id=raw.id,
        file_checksum=raw.file_hash,
        original_filename="t.xlsx",
        sheet_name="ordine 1",
        sheet_type="ORDINE",
        parser_version="1",
        idempotency_key=f"test-{uid}",
        status="PREVIEW",
        preview_json={},
    )
    db.add(run)
    db.flush()

    preview = {
        "invoice_blocks": [
            {
                "invoice_number": "1",
                "invoice_date": "2026-01-01",
                "items": [
                    {"row_number": 4, "product_name_raw": "show 26", "item_quantity": 10},
                ],
            }
        ],
        "da_spedire": [],
    }
    sync_heroes_xlsx_staging(db, run_id=run.id, raw_file_id=raw.id, preview=preview)
    groups = build_sku_triage_groups(db, run_id=run.id, raw_file_id=raw.id)

    assert len(groups) == 1
    g = groups[0]
    assert g["suggested_product_id"] is not None
    assert g["match_confidence"] is not None
    assert g["status"] == "pending"
    assert g["resolved_product_id"] is None
    assert g["suggestion_badge"] in ("verify", "suggestion")


def test_high_confidence_still_requires_triage_confirmation(db):
    from app.services.heroes_xlsx_staging import build_sku_triage_groups, sync_heroes_xlsx_staging
    from app.models import HeroesImportRun, RawImportFile

    uid = uuid.uuid4().hex[:5]
    quality = Product(
        sku_code=f"STAR-{uid}",
        description="STARLIGHT 2026",
        category="RACKET",
        product_group="RAQUETES",
        launch_date=__import__("datetime").date(2026, 1, 1),
        commercial_notes="epic",
    )
    db.add(quality)
    db.commit()

    raw = RawImportFile(
        original_filename="t.xlsx",
        storage_path="tests/fixtures/x.xlsx",
        file_hash=f"hash2-{uid}",
        source_system="heroes_xlsx",
    )
    db.add(raw)
    db.flush()
    run = HeroesImportRun(
        raw_file_id=raw.id,
        file_checksum=raw.file_hash,
        original_filename="t.xlsx",
        sheet_name="ordine 1",
        sheet_type="ORDINE",
        parser_version="1",
        idempotency_key=f"test2-{uid}",
        status="PREVIEW",
        preview_json={},
    )
    db.add(run)
    db.flush()

    preview = {
        "invoice_blocks": [
            {
                "invoice_number": "1",
                "invoice_date": "2026-01-01",
                "items": [
                    {"row_number": 4, "product_name_raw": "starlight 26", "item_quantity": 10},
                ],
            }
        ],
        "da_spedire": [],
    }
    sync_heroes_xlsx_staging(db, run_id=run.id, raw_file_id=raw.id, preview=preview)
    groups = build_sku_triage_groups(db, run_id=run.id, raw_file_id=raw.id)

    assert len(groups) == 1
    g = groups[0]
    assert g["status"] == "pending"
    assert g["resolved_product_id"] is None
    assert float(g["match_confidence"]) >= MATCH_AUTO_RESOLVE_SCORE
    assert g["suggestion_badge"] == "suggestion"
