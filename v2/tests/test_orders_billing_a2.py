"""A2 Document Readiness — order_date, invoice_date, unit snapshots, order documents."""

from datetime import date, timedelta
from io import BytesIO


def _sup_prod(client, tag="A2"):
    s = client.post("/api/suppliers", json={"name": f"Sup {tag}", "country_code": "IT"}).json()
    p1 = client.post("/api/products", json={"sku": f"SKU-{tag}-1", "description": "A"}).json()
    p2 = client.post("/api/products", json={"sku": f"SKU-{tag}-2", "description": "B"}).json()
    return s, p1, p2


def test_order_date_notes_unit_and_document(admin_client):
    c = admin_client
    s, p1, p2 = _sup_prod(c, "ORD")
    r = c.post(
        "/api/orders",
        json={
            "code": "ORD-A2-DATE",
            "supplier_id": s["id"],
            "currency": "EUR",
            "order_date": "2026-06-04",
            "notes": "Ordine 589 notes",
        },
    )
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["order_date"] == "2026-06-04"
    assert o["notes"] == "Ordine 589 notes"

    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p1["id"],
            "quantity": "10",
            "unit_price": "5",
            "unit": "pz",
        },
    ).json()
    assert o["items"][0]["unit"] == "PZ"

    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p2["id"],
            "quantity": "2",
            "unit_price": "50",
            "unit": "SET",
        },
    ).json()
    assert o["items"][1]["unit"] == "SET"

    # item without unit
    o = c.patch(
        f"/api/orders/{o['id']}/items/{o['items'][1]['id']}",
        json={"expected_version": o["version"], "unit": None},
    ).json()
    # clearing unit via null
    assert o["items"][1]["unit"] is None

    o = c.patch(
        f"/api/orders/{o['id']}/items/{o['items'][1]['id']}",
        json={"expected_version": o["version"], "unit": "CTNS"},
    ).json()
    assert o["items"][1]["unit"] == "CTNS"

    o = c.patch(
        f"/api/orders/{o['id']}",
        json={"expected_version": o["version"], "order_date": "2026-06-05", "notes": "updated"},
    ).json()
    assert o["order_date"] == "2026-06-05"
    assert o["notes"] == "updated"

    r = c.post(
        "/api/documents",
        data={"entity_type": "order", "entity_id": str(o["id"]), "role": "official"},
        files={"file": ("Ordine_589.pdf", BytesIO(b"%PDF-1.4 a2"), "application/pdf")},
    )
    assert r.status_code in (200, 201), r.text
    o = c.get(f"/api/orders/{o['id']}").json()
    assert any(d["original_filename"] == "Ordine_589.pdf" for d in o["documents"])

    audit = c.get("/api/audit", params={"entity_type": "order", "entity_id": str(o["id"])})
    assert audit.status_code == 200
    actions = {e["action"] for e in audit.json()}
    assert "create" in actions
    assert "update_header" in actions
    assert "update_item" in actions


def test_invoice_inherits_unit_and_date_immutable_after_issue(admin_client):
    c = admin_client
    s, p1, _ = _sup_prod(c, "INV")
    o = c.post(
        "/api/orders",
        json={"code": "ORD-A2-INV", "supplier_id": s["id"], "order_date": "2026-03-30"},
    ).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p1["id"],
            "quantity": "150",
            "unit_price": "6.50",
            "unit": "PZ",
        },
    ).json()
    o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()

    inv = c.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": "F-A2-202", "invoice_date": "2026-03-30"},
    ).json()
    assert inv["invoice_date"] == "2026-03-30"
    assert inv["items"][0]["unit"] == "PZ"

    # explicit override on replace
    inv = c.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": o["items"][0]["id"],
                    "quantity": "150",
                    "unit_price_gross": "6.50",
                    "unit": "SET",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    assert inv["items"][0]["unit"] == "SET"

    # patch date while DRAFT
    inv = c.patch(
        f"/api/invoices/{inv['id']}",
        json={"expected_version": inv["version"], "invoice_date": "2026-04-01"},
    ).json()
    assert inv["invoice_date"] == "2026-04-01"

    today = date.today()
    inv = c.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "PERCENT",
            "terms": [
                {"due_date": today.isoformat(), "percent": "30"},
                {"due_date": (today + timedelta(days=30)).isoformat(), "percent": "70"},
            ],
        },
    ).json()

    # attach doc + issue
    c.post(
        "/api/documents",
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
        files={"file": ("Fattura.pdf", BytesIO(b"%PDF-1.4 inv"), "application/pdf")},
    )
    r = c.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["status"] == "ISSUED"
    assert inv["items"][0]["unit"] == "SET"

    r = c.patch(
        f"/api/invoices/{inv['id']}",
        json={"expected_version": inv["version"], "invoice_date": "2026-05-01"},
    )
    assert r.status_code == 409, r.text


def test_invoice_inherits_when_unit_omitted_on_replace(admin_client):
    c = admin_client
    s, p1, _ = _sup_prod(c, "INH")
    o = c.post("/api/orders", json={"code": "ORD-A2-INH", "supplier_id": s["id"]}).json()
    o = c.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p1["id"],
            "quantity": "1",
            "unit_price": "1",
            "unit": "UN",
        },
    ).json()
    o = c.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = c.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": "F-INH"},
    ).json()
    inv = c.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": o["items"][0]["id"],
                    "quantity": "1",
                    "unit_price_gross": "1",
                }
            ],
        },
    ).json()
    assert inv["items"][0]["unit"] == "UN"


def test_migration_010_revises_009():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("010")
    assert rev is not None
    assert rev.down_revision == "009"


def test_migration_021_revises_019():
    """RUX-3B: 021 a partir de 019 — não reutiliza a 020 isolada."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("021")
    assert rev is not None
    assert rev.down_revision == "019"
    # 020 Catalog RUX-3A não está na chain (arquivo isolado fora de versions/)
    assert "020" not in {r.revision for r in script.walk_revisions()}
    assert EXPECTED_ALEMBIC_REVISION == "023"


def test_migration_022_revises_021():
    """J4-FIN FIN-1: payments.order_id."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("022")
    assert rev is not None
    assert rev.down_revision == "021"
    assert script.get_current_head() == "023"
    assert EXPECTED_ALEMBIC_REVISION == "023"


def test_migration_023_revises_022():
    """J4-FIN FIN-3: IBAN/banco de pagamento + terms_from_document."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from app.foundation.schema_revision import EXPECTED_ALEMBIC_REVISION

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("023")
    assert rev is not None
    assert rev.down_revision == "022"
    assert script.get_current_head() == "023"
    assert EXPECTED_ALEMBIC_REVISION == "023"