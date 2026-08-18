"""G4 — Fattura match também por OrderItem.external_code (pós-bind)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

from app.ingestion.fattura_line_match import plan_fattura_lines


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _fake_doc(*lines: tuple[str, str, str]):
    """lines: (sku, qty, unit_price). Objeto mínimo — plan_fattura_lines só lê rows."""
    rows = []
    for idx, (sku, qty, price) in enumerate(lines, start=1):
        cells = {
            "sku": {"raw": sku, "normalized": sku},
            "quantity": {"raw": qty, "normalized": qty},
            "unit_price": {"raw": price, "normalized": price},
            "unit": {"raw": "PZ", "normalized": "PZ"},
        }
        rows.append(SimpleNamespace(row_index=idx, cells_json=json.dumps(cells)))
    return SimpleNamespace(rows=rows)


def test_g4_match_by_external_code_when_sku_snapshot_differs(admin_client, db):
    from app.billing import public as billing_public
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public

    sid = catalog_public.create_supplier(db, name=f"G4 Sup {_uid()}", country_code="IT").id
    product = catalog_public.create_product(
        db, sku=f"CAT-G4-{_uid()}", description="racchette 2027 GRAFICATE cat"
    )
    db.flush()

    order = orders_public.create_order(
        db,
        code=f"G4-EXT-{_uid()}",
        supplier_id=sid,
        created_by_actor_id="1",
        currency="EUR",
    )
    db.flush()
    order = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        line_kind="COMMITMENT",
        external_code="I.V. 2",
        description="racchette 2027 GRAFICATE",
        quantity="14600",
        unit_price="50.00",
        unit="PZ",
    )
    order = orders_public.confirm_order(db, order.id, expected_version=order.version)
    item_id = order.items[0].id
    issued = billing_public.issued_qty_for_order_item(db, order.id, item_id)
    order = orders_public.bind_commitment_product(
        db,
        order.id,
        item_id,
        product.id,
        actor="1",
        expected_version=order.version,
        issued_qty=issued,
    )
    db.flush()
    bound = next(i for i in order.items if i.id == item_id)
    assert bound.line_kind == "PRODUCT"
    assert bound.sku_snapshot == product.sku
    assert bound.external_code == "I.V. 2"
    assert bound.sku_snapshot != "I.V. 2"

    plan = plan_fattura_lines(db, _fake_doc(("I.V. 2", "200", "50.00")), order)
    assert not plan.blockers or all(b.code != "fattura_sku_not_on_order" for b in plan.blockers)
    matched = [m for m in plan.matches if m.order_item_id == item_id]
    assert matched, f"expected external_code match; plan={plan}"
    assert matched[0].order_item_id == item_id


def test_g4_match_by_sku_snapshot_still_works(admin_client, db):
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public

    sid = catalog_public.create_supplier(db, name=f"G4 Sup {_uid()}", country_code="IT").id
    sku = f"8057-G4-{_uid()}"
    product = catalog_public.create_product(db, sku=sku, description="produto EAN")
    db.flush()
    order = orders_public.create_order(
        db,
        code=f"G4-SKU-{_uid()}",
        supplier_id=sid,
        created_by_actor_id="1",
        currency="EUR",
    )
    db.flush()
    order = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        product_id=product.id,
        quantity="100",
        unit_price="10.00",
        unit="PZ",
    )
    order = orders_public.confirm_order(db, order.id, expected_version=order.version)
    db.flush()
    item_id = order.items[0].id

    plan = plan_fattura_lines(db, _fake_doc((sku, "10", "10.00")), order)
    matched = [m for m in plan.matches if m.order_item_id == item_id]
    assert matched
    assert matched[0].order_item_id == item_id


def test_g4_pure_commitment_still_unbillable(admin_client, db):
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public

    sid = catalog_public.create_supplier(db, name=f"G4 Sup {_uid()}", country_code="IT").id
    db.flush()
    order = orders_public.create_order(
        db,
        code=f"G4-CMT-{_uid()}",
        supplier_id=sid,
        created_by_actor_id="1",
        currency="EUR",
    )
    db.flush()
    order = orders_public.add_item(
        db,
        order.id,
        expected_version=order.version,
        line_kind="COMMITMENT",
        external_code="I.V. 2",
        description="compromisso puro",
        quantity="14600",
        unit_price="50.00",
        unit="PZ",
    )
    order = orders_public.confirm_order(db, order.id, expected_version=order.version)
    db.flush()

    plan = plan_fattura_lines(db, _fake_doc(("I.V. 2", "200", "50.00")), order)
    assert plan.commitment_only is True
    assert any(b.code == "fattura_no_billable_lines" for b in plan.blockers)
    assert plan.matches == [] or all(m.order_item_id is None for m in plan.matches)
