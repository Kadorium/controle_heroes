"""Coleta de fatos via APIs públicas — Costing não importa internals alheios."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.costing.money import parse_decimal
from app.customs import public as customs_public
from app.logistics import public as logistics_public
from app.orders import public as orders_public
from app.treasury import public as treasury_public


def collect(db: Session, process_id: int) -> dict:
    customs = customs_public.process_cost_facts(db, process_id)
    inv_alloc_ids = [a["invoice_item_id"] for a in customs["invoice_item_allocations"]]
    shp_alloc_ids = [a["shipment_item_id"] for a in customs["shipment_item_allocations"]]
    invoice_items = billing_public.costable_invoice_items(db, inv_alloc_ids)
    by_inv_item = {r["invoice_item_id"]: r for r in invoice_items}

    # Invoice-level linked but not item-allocated: still list invoices for coverage.
    linked_invoices = []
    for iid in customs["invoice_ids"]:
        inv = billing_public.get_invoice(db, iid)
        totals = billing_public.invoice_totals_as_strings(inv)
        fx = treasury_public.fx_queries.invoice_fx_facts(db, iid)
        linked_invoices.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "currency": inv.currency,
                "net_amount": totals.get("net_amount"),
                "fx": fx,
            }
        )

    physical = logistics_public.item_physical_bases(db, shp_alloc_ids)
    by_shp = {r["shipment_item_id"]: r for r in physical}

    invoice_lines = []
    for a in customs["invoice_item_allocations"]:
        fact = by_inv_item.get(a["invoice_item_id"])
        if not fact:
            continue
        inv_qty = parse_decimal(fact["quantity"])
        alloc_qty = parse_decimal(a["allocated_qty"])
        net = parse_decimal(fact["line_net_amount"])
        line_net = None
        if net is not None and inv_qty and alloc_qty:
            line_net = (net * alloc_qty / inv_qty) if inv_qty != 0 else None
        invoice_lines.append(
            {
                **fact,
                "allocated_qty": a["allocated_qty"],
                "process_net": str(line_net) if line_net is not None else None,
            }
        )

    shipment_lines = []
    for a in customs["shipment_item_allocations"]:
        phys = by_shp.get(a["shipment_item_id"])
        if not phys:
            continue
        shipment_lines.append({**phys, "allocated_qty": a["allocated_qty"]})

    return {
        "process": {
            "id": customs["process_id"],
            "code": customs["code"],
            "external_reference": customs["external_reference"],
            "status": customs["status"],
        },
        "invoices": linked_invoices,
        "invoice_lines": invoice_lines,
        "shipment_lines": shipment_lines,
        "fundings": customs["fundings"],
    }


def order_item_estimate(db: Session, order_item_id: int | None) -> dict | None:
    if not order_item_id:
        return None
    try:
        oi = orders_public.get_order_item(db, order_item_id)
    except orders_public.OrdersError:
        return None
    qty = Decimal(str(oi.quantity))
    price = oi.unit_price
    net = (qty * price) if price is not None else None
    return {
        "order_item_id": oi.id,
        "product_id": oi.product_id,
        "sku_snapshot": oi.sku_snapshot,
        "description_snapshot": oi.description_snapshot,
        "quantity": str(qty),
        "unit_price": str(price) if price is not None else None,
        "estimated_net": str(net) if net is not None else None,
        "order_id": oi.order_id,
    }
