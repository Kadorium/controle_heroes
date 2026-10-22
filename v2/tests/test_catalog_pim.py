"""CAT-PIM Onda 1 — taxonomy, quality, search, PATCH type, import idempotency."""

from app.catalog.taxonomy import ensure_taxonomy, type_by_name, category_by_name
from app.catalog.heroes_import import commit_heroes_batch


def test_taxonomy_seed_is_idempotent(db):
    ensure_taxonomy(db)
    ensure_taxonomy(db)
    db.commit()
    from app.catalog.models import ProductCategory, ProductType

    assert db.query(ProductCategory).count() == 3
    assert db.query(ProductType).count() == 8
    assert category_by_name(db, "Raquetes")
    assert type_by_name(db, "Raquete")
    assert type_by_name(db, "Vestuário")


def test_create_product_backfills_commercial_name(admin_client):
    r = admin_client.post("/api/products", json={"sku": "PIM-NEW", "description": "Nome comercial"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["commercial_name"] == "Nome comercial"
    assert body["quality"]["essential_ok"] is False
    assert any(i["code"] == "ncm" and "informação fiscal pendente" in i["consequence"] for i in body["quality"]["items"])
    assert "ainda não está pronto para a operação" not in r.text


def test_product_list_search_and_review_filters(admin_client, db):
    ensure_taxonomy(db)
    db.commit()
    cat = category_by_name(db, "Raquetes")
    ptype = type_by_name(db, "Raquete")
    a = admin_client.post("/api/products", json={"sku": "HEROES-BT-HARLEY-2024", "description": "#HARLEY 2024"}).json()
    b = admin_client.post("/api/products", json={"sku": "HEROES-BT-HARLEY-2025", "description": "#HARLEY 2025"}).json()
    admin_client.patch(
        f"/api/products/{a['id']}",
        json={
            "category_id": cat.id,
            "product_type_id": ptype.id,
            "subcategory": "Beach Tennis",
            "attributes": {"sport": "BEACH TENNIS", "model": "HARLEY", "collection_year": "2024"},
            "short_description": "Raquete HARLEY 2024",
        },
    )
    admin_client.patch(
        f"/api/products/{b['id']}",
        json={
            "category_id": cat.id,
            "product_type_id": ptype.id,
            "subcategory": "Beach Tennis",
            "attributes": {"sport": "BEACH TENNIS", "model": "HARLEY", "collection_year": "2025"},
            "taxonomy_status": "REVIEW",
            "taxonomy_reason": "status UNKNOWN no CSV",
        },
    )
    found = admin_client.get("/api/catalog/product-list", params={"q": "HARLEY"})
    assert found.status_code == 200
    skus = {x["sku"] for x in found.json()["items"]}
    assert "HEROES-BT-HARLEY-2024" in skus
    assert "HEROES-BT-HARLEY-2025" in skus

    year = admin_client.get("/api/catalog/product-list", params={"q": "2026"})
    assert year.status_code == 200

    classification = admin_client.get(
        "/api/catalog/product-list", params={"needs_classification_review": True}
    )
    assert classification.status_code == 200
    assert all(x["needs_classification_review"] for x in classification.json()["items"])
    assert "CONFIDENT" not in classification.text
    assert any(x["sku"] == "HEROES-BT-HARLEY-2025" for x in classification.json()["items"])

    product_review = admin_client.get("/api/catalog/product-list", params={"needs_review": True})
    assert product_review.status_code == 200
    assert not any(x["sku"] == "HEROES-BT-HARLEY-2025" for x in product_review.json()["items"])

    raquetes = admin_client.get("/api/catalog/product-list", params={"category": "raquetes"})
    assert raquetes.status_code == 200
    assert raquetes.json()["total"] >= 2
    assert "category" in raquetes.json()["facets"]


def test_patch_type_preserves_attributes(admin_client, db):
    ensure_taxonomy(db)
    db.commit()
    vest = type_by_name(db, "Vestuário")
    raq = type_by_name(db, "Raquete")
    cat = category_by_name(db, "Vestuário")
    created = admin_client.post("/api/products", json={"sku": "PIM-TYPE", "description": "Felpa"}).json()
    admin_client.patch(
        f"/api/products/{created['id']}",
        json={
            "category_id": cat.id,
            "product_type_id": vest.id,
            "attributes": {"garment_kind": "MOLETOM", "gender": "Unisex"},
            "color": "PURE RED",
        },
    )
    changed = admin_client.patch(
        f"/api/products/{created['id']}",
        json={"product_type_id": raq.id},
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert body["attributes"]["garment_kind"] == "MOLETOM"
    assert body["color"] == "PURE RED"
    assert any("preservadas" in n.lower() for n in body["notices"])


def _heroes_payload(**overrides):
    base = {
        "sku": "HEROES-BT-ARION-2026",
        "decision": "EDITAR",
        "commercial_name": "#ARION 2026",
        "short_description": "Raquete ARION",
        "category": "Raquetes",
        "subcategory": "Beach Tennis",
        "product_type": "Raquete",
        "taxonomy_status": "CONFIDENT",
        "short_generic": False,
        "is_active": True,
        "lifecycle_status": "ACTIVE",
        "color": "BLACK",
        "attributes": {"sport": "BEACH TENNIS", "model": "ARION", "collection_year": "2026"},
        "provenance": {"commercial_name": "csv_historical", "model": "deterministic_rule"},
        "ncm": None,
        "ean": None,
    }
    base.update(overrides)
    return base


def test_heroes_import_idempotent_and_conflict(db, admin_client):
    ensure_taxonomy(db)
    db.commit()
    from app.audit.models import AuditLog
    from app.catalog.commands import update_product
    from app.catalog.models import Product

    payload = _heroes_payload()
    first = commit_heroes_batch(db, [payload], filename="t.xlsx", checksum="aaa", actor_id="test")
    db.commit()
    assert first["created"] == 1
    assert first["updated"] == 0
    assert first["unchanged"] == 0
    assert first["conflicts"] == []
    row = db.query(Product).filter(Product.sku == payload["sku"]).one()
    created_at = row.created_at
    updated_at = row.updated_at
    audits = db.query(AuditLog).filter(AuditLog.reason_code == "CATALOG_HEROES_IMPORT").count()

    second = commit_heroes_batch(db, [payload], filename="t.xlsx", checksum="aaa", actor_id="test")
    db.commit()
    db.refresh(row)
    assert second["created"] == 0
    assert second["updated"] == 0
    assert second["unchanged"] == 1
    assert second["batch_id"] is None
    assert row.updated_at == updated_at
    assert row.created_at == created_at
    assert db.query(AuditLog).filter(AuditLog.reason_code == "CATALOG_HEROES_IMPORT").count() == audits

    update_product(db, row.id, commercial_name="Nome manual")
    db.commit()
    blocked = commit_heroes_batch(db, [payload], filename="t.xlsx", checksum="bbb", actor_id="test")
    assert blocked["conflicts"]
    assert any("edição manual" in c["reason"] for c in blocked["conflicts"])
    db.rollback()
    db.expire_all()
    assert db.query(Product).filter(Product.sku == payload["sku"]).one().commercial_name == "Nome manual"

    other = admin_client.post("/api/products", json={"sku": "MDM-R-001", "description": "Massa"}).json()
    stolen = dict(payload, sku="MDM-R-001", commercial_name="Outro")
    db.expire_all()
    row_mdm = db.query(Product).filter(Product.sku == "MDM-R-001").one()
    assert row_mdm.source_kind == "manual"
    blocked2 = commit_heroes_batch(db, [stolen], filename="t.xlsx", checksum="ccc", actor_id="test")
    assert any("fora deste lote" in c["reason"] for c in blocked2["conflicts"])
    assert other["id"] == row_mdm.id


def test_heroes_import_intentional_xlsx_change(db):
    ensure_taxonomy(db)
    db.commit()
    from app.audit.models import AuditLog
    from app.catalog.models import Product

    keep = _heroes_payload(sku="HEROES-KEEP", commercial_name="#KEEP")
    change = _heroes_payload(sku="HEROES-CHANGE", commercial_name="#CHANGE")
    first = commit_heroes_batch(db, [keep, change], filename="t.xlsx", checksum="aaa", actor_id="test")
    db.commit()
    assert first["created"] == 2
    audits = db.query(AuditLog).filter(AuditLog.reason_code == "CATALOG_HEROES_IMPORT").count()
    ts_keep = db.query(Product).filter(Product.sku == "HEROES-KEEP").one().updated_at

    second = commit_heroes_batch(
        db,
        [keep, dict(change, commercial_name="#CHANGE EDITADO")],
        filename="t.xlsx",
        checksum="bbb",
        actor_id="test",
    )
    db.commit()
    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["unchanged"] == 1
    db.expire_all()
    assert db.query(Product).filter(Product.sku == "HEROES-KEEP").one().commercial_name == "#KEEP"
    assert db.query(Product).filter(Product.sku == "HEROES-KEEP").one().updated_at == ts_keep
    assert db.query(Product).filter(Product.sku == "HEROES-CHANGE").one().commercial_name == "#CHANGE EDITADO"
    assert db.query(AuditLog).filter(AuditLog.reason_code == "CATALOG_HEROES_IMPORT").count() == audits + 1


def test_heroes_import_invalid_cases_no_partial_write(db):
    ensure_taxonomy(db)
    db.commit()
    from app.catalog.models import Product

    good = _heroes_payload(sku="HEROES-PARTIAL-GOOD")
    bad_type = _heroes_payload(sku="HEROES-PARTIAL-BAD", product_type="Tipo Inventado")
    blocked = commit_heroes_batch(db, [good, bad_type], filename="t.xlsx", checksum="x", actor_id="test")
    assert blocked["conflicts"]
    assert blocked["created"] == 0
    assert db.query(Product).filter(Product.sku.in_([good["sku"], bad_type["sku"]])).count() == 0

    bad_decision = commit_heroes_batch(
        db, [_heroes_payload(decision="TALVEZ")], filename="t.xlsx", checksum="y", actor_id="test"
    )
    assert any("decisão inválida" in c["reason"] for c in bad_decision["conflicts"])
    assert bad_decision["created"] == 0

    bad_cat = commit_heroes_batch(
        db, [_heroes_payload(category="Planetas")], filename="t.xlsx", checksum="z", actor_id="test"
    )
    assert any("categoria inválida" in c["reason"] for c in bad_cat["conflicts"])


def test_review_semantics_split(admin_client, db):
    ensure_taxonomy(db)
    db.commit()
    from app.catalog.models import Product

    cat = category_by_name(db, "Raquetes")
    ptype = type_by_name(db, "Raquete")
    weak = admin_client.post("/api/products", json={"sku": "PIM-WEAK", "description": "Curta fraca"}).json()
    tax = admin_client.post("/api/products", json={"sku": "PIM-TAX", "description": "Taxonomia"}).json()
    admin_client.patch(
        f"/api/products/{weak['id']}",
        json={"category_id": cat.id, "product_type_id": ptype.id, "taxonomy_status": "CONFIDENT"},
    )
    admin_client.patch(
        f"/api/products/{tax['id']}",
        json={"category_id": cat.id, "product_type_id": ptype.id, "taxonomy_status": "REVIEW"},
    )
    db.expire_all()
    weak_row = db.query(Product).filter(Product.sku == "PIM-WEAK").one()
    weak_row.import_decision = "REVISAR"
    weak_row.short_generic = True
    tax_row = db.query(Product).filter(Product.sku == "PIM-TAX").one()
    tax_row.import_decision = "REVISAR"
    db.commit()

    general = admin_client.get("/api/catalog/product-list", params={"needs_review": True})
    skus_g = {x["sku"] for x in general.json()["items"]}
    assert "PIM-WEAK" in skus_g
    assert "PIM-TAX" in skus_g

    classification = admin_client.get(
        "/api/catalog/product-list", params={"needs_classification_review": True}
    )
    skus_c = {x["sku"] for x in classification.json()["items"]}
    assert "PIM-TAX" in skus_c
    assert "PIM-WEAK" not in skus_c

    shorts = admin_client.get("/api/catalog/product-list", params={"short_generic": True})
    skus_s = {x["sku"] for x in shorts.json()["items"]}
    assert "PIM-WEAK" in skus_s
    assert "PIM-TAX" not in skus_s

    detail = admin_client.get(f"/api/products/{weak['id']}").json()
    assert detail["needs_classification_review"] is False
    assert detail["needs_review"] is True
    assert detail["short_generic"] is True
    assert "classificação duvidosa" not in (detail.get("taxonomy_reason") or "").lower()


def test_taxonomy_endpoint(admin_client):
    r = admin_client.get("/api/catalog/taxonomy")
    assert r.status_code == 200, r.text
    body = r.json()
    assert {c["name"] for c in body["categories"]} == {"Raquetes", "Acessórios", "Vestuário"}
    assert len(body["product_types"]) == 8


def test_migration_027_revises_026():
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("027")
    assert rev is not None
    assert rev.down_revision == "026"
    assert script.get_current_head() == "031"
    assert EXPECTED_ALEMBIC_REVISION == "031"
    assert "import_decision" in Path(__file__).resolve().parents[1].joinpath(
        "alembic/versions/027_catalog_pim_taxonomy.py"
    ).read_text(encoding="utf-8")


def test_search_finds_commercial_fields(admin_client, db):
    ensure_taxonomy(db)
    db.commit()
    cat = category_by_name(db, "Raquetes")
    ptype = type_by_name(db, "Raquete")
    created = admin_client.post("/api/products", json={"sku": "PIM-GRAV", "description": "Gravity ATLAS"}).json()
    admin_client.patch(
        f"/api/products/{created['id']}",
        json={
            "category_id": cat.id,
            "product_type_id": ptype.id,
            "subcategory": "Beach Tennis",
            "attributes": {"sport": "BEACH TENNIS", "model": "ATLAS", "collection_year": "2026"},
        },
    )
    for q in ("gravity", "beach tennis", "2026", "ATLAS"):
        r = admin_client.get("/api/catalog/product-list", params={"q": q})
        assert r.status_code == 200, r.text
        assert any(x["sku"] == "PIM-GRAV" for x in r.json()["items"]), q
    picker = admin_client.get("/api/products", params={"q": "Gravity ATLAS", "active_only": True})
    assert picker.status_code == 200
    assert any(x["sku"] == "PIM-GRAV" for x in picker.json())


def test_heroes_preview_duplicate_sku(db):
    from app.catalog.heroes_import import preview_heroes_batch

    preview = preview_heroes_batch(
        [
            {"sku": "HEROES-DUP", "decision": "EDITAR"},
            {"sku": "HEROES-DUP", "decision": "EDITAR"},
        ]
    )
    assert preview["conflicts"]


def test_heroes_preview_splits_review_semantics():
    from app.catalog.heroes_import import preview_heroes_batch

    preview = preview_heroes_batch(
        [
            {
                "sku": "HEROES-A",
                "decision": "REVISAR",
                "taxonomy_status": "CONFIDENT",
            },
            {
                "sku": "HEROES-B",
                "decision": "REVISAR",
                "taxonomy_status": "REVIEW",
            },
            {
                "sku": "HEROES-C",
                "decision": "EDITAR",
                "taxonomy_status": "CONFIDENT",
            },
        ]
    )
    assert preview["review"] == 2
    assert preview["classification_review"] == 1
    assert not preview["conflicts"]


def test_commit_92_cli_refuses_epic_v2():
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    script = repo / "docs" / "v2" / "etapa-cat-pim" / "scripts" / "commit_92.py"
    xlsx = repo / "docs" / "v2" / "etapa-cat-pim" / "review" / "CAT_PIM_92_REVIEW.xlsx"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--xlsx",
            str(xlsx),
            "--commit",
            "--i-validated-xlsx",
            "--database-url",
            "postgresql://postgres@localhost:5433/epic_v2",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo),
    )
    assert result.returncode != 0
    blob = (result.stdout or "") + (result.stderr or "")
    assert "epic_v2" in blob


def test_commit_92_guard_and_invalid_xlsx(tmp_path):
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[2] / "docs" / "v2" / "etapa-cat-pim" / "scripts"
    sys.path.insert(0, str(scripts))
    import commit_92

    assert commit_92._db_name("postgresql://postgres@localhost:5433/epic_v2") == "epic_v2"
    assert commit_92._db_name("postgresql://postgres@localhost:5433/epic_v2_test") == "epic_v2_test"

    assert "epic_v2_promotion_test" in commit_92.ALLOWED_COMMIT_DBS
    mutated = tmp_path / "mut.xlsx"
    mutated.write_bytes(b"not-the-validated-xlsx")
    assert commit_92._checksum(mutated) != commit_92.EXPECTED_XLSX_SHA256
    assert commit_92._csv_checksum() == commit_92.EXPECTED_CSV_SHA256

    from openpyxl import Workbook

    bad = tmp_path / "bad.xlsx"
    wb = Workbook()
    wb.active.title = "Outra"
    wb.save(bad)
    try:
        commit_92.load_decisions(bad)
        raise AssertionError("XLSX sem aba Revisao deveria falhar")
    except SystemExit as exc:
        assert "Revisao" in str(exc)


def test_commit_92_promote_mode_guards():
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[2] / "docs" / "v2" / "etapa-cat-pim" / "scripts"
    sys.path.insert(0, str(scripts))
    import commit_92

    try:
        commit_92.resolve_commit_mode(
            "epic_v2",
            promote_ops=False,
            confirm_ops="",
            promote_rehearsal=False,
            confirm_rehearsal="",
        )
        raise AssertionError("epic_v2 sem modo dedicado deveria recusar")
    except SystemExit as exc:
        assert "nunca epic_v2" in str(exc)

    try:
        commit_92.resolve_commit_mode(
            "epic_v2",
            promote_ops=True,
            confirm_ops="",
            promote_rehearsal=False,
            confirm_rehearsal="",
        )
        raise AssertionError("promote sem confirmação deveria recusar")
    except SystemExit as exc:
        assert "i-confirm-promote-epic-v2" in str(exc)

    try:
        commit_92.resolve_commit_mode(
            "epic_v2_test",
            promote_ops=True,
            confirm_ops=commit_92.PROMOTE_CONFIRM_EPIC_V2,
            promote_rehearsal=False,
            confirm_rehearsal="",
        )
        raise AssertionError("promote contra teste deveria recusar")
    except SystemExit as exc:
        assert "epic_v2" in str(exc)

    try:
        commit_92.resolve_commit_mode(
            "epic_v2",
            promote_ops=False,
            confirm_ops="",
            promote_rehearsal=True,
            confirm_rehearsal=commit_92.PROMOTE_CONFIRM_REHEARSAL,
        )
        raise AssertionError("rehearsal contra epic_v2 deveria recusar")
    except SystemExit as exc:
        assert "epic_v2_promotion_test" in str(exc)

    assert (
        commit_92.resolve_commit_mode(
            "epic_v2",
            promote_ops=True,
            confirm_ops=commit_92.PROMOTE_CONFIRM_EPIC_V2,
            promote_rehearsal=False,
            confirm_rehearsal="",
        )
        == "ops"
    )
    assert (
        commit_92.resolve_commit_mode(
            "epic_v2_promotion_test",
            promote_ops=False,
            confirm_ops="",
            promote_rehearsal=True,
            confirm_rehearsal=commit_92.PROMOTE_CONFIRM_REHEARSAL,
        )
        == "rehearsal"
    )
    assert (
        commit_92.resolve_commit_mode(
            "epic_v2_test",
            promote_ops=False,
            confirm_ops="",
            promote_rehearsal=False,
            confirm_rehearsal="",
        )
        == "allowed"
    )


def test_commit_92_cli_promote_without_confirm_refuses():
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    script = repo / "docs" / "v2" / "etapa-cat-pim" / "scripts" / "commit_92.py"
    xlsx = repo / "docs" / "v2" / "etapa-cat-pim" / "review" / "CAT_PIM_92_REVIEW.xlsx"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--xlsx",
            str(xlsx),
            "--commit",
            "--i-validated-xlsx",
            "--promote-to-epic-v2",
            "--database-url",
            "postgresql://postgres@localhost:5433/epic_v2",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo),
    )
    assert result.returncode != 0
    blob = (result.stdout or "") + (result.stderr or "")
    assert "i-confirm-promote-epic-v2" in blob


def test_commit_92_cli_rehearsal_refuses_ops_db():
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    script = repo / "docs" / "v2" / "etapa-cat-pim" / "scripts" / "commit_92.py"
    xlsx = repo / "docs" / "v2" / "etapa-cat-pim" / "review" / "CAT_PIM_92_REVIEW.xlsx"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--xlsx",
            str(xlsx),
            "--commit",
            "--i-validated-xlsx",
            "--promote-rehearsal",
            "--i-confirm-promote-rehearsal",
            "APPLY-027-AND-92-TO-PROMOTION-CLONE",
            "--database-url",
            "postgresql://postgres@localhost:5433/epic_v2",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo),
    )
    assert result.returncode != 0
    blob = (result.stdout or "") + (result.stderr or "")
    assert "epic_v2_promotion_test" in blob
