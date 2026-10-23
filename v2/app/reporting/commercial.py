"""Disponibilidade comercial — orquestração read-only no Reporting."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.customs import public as customs_public
from app.inventory import public as inventory_public
from app.logistics import public as logistics_public

_Q = Decimal("0.0001")


def _d(value: str | None) -> Decimal:
    if value in (None, "", "—"):
        return Decimal("0")
    return Decimal(str(value))


def _qty(value: Decimal | str | None) -> str:
    q = Decimal(str(value or 0))
    return f"{q:.4f}".rstrip("0").rstrip(".") or "0"


def _incoming_cell(transit: dict | None, clearance: str | None) -> str | None:
    t_qty = _d((transit or {}).get("qty")) if transit else Decimal("0")
    c_qty = _d(clearance)
    total = t_qty + c_qty
    if total <= 0:
        return None
    return _qty(total)


def availability(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    product_type: str | None = None,
    status: str | None = None,
    sort: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    stock_sorts = {"available", "-available", "incoming", "-incoming", "bonded", "-bonded"}

    filters = catalog_public.ProductListFilters(
        q=q or None,
        category=category or None,
        product_type=product_type or None,
        sort=sort if sort not in stock_sorts else "commercial_name",
        limit=limit,
        offset=0,
        needs_review=status == "attention",
        is_active=True,
    )
    products = catalog_public.product_read_population(db, filters)
    pids = [p.id for p in products]
    stock = inventory_public.stock_position_bulk(db, pids) if pids else {}
    cleared = inventory_public.cleared_not_received_bulk(db, pids) if pids else {}
    incoming = logistics_public.incoming_qty_by_product(db, product_ids=pids) if pids else {
        "by_product": {},
        "unassigned_qty": "0",
    }
    residuals = customs_public.clearance_residuals_by_product(db, pids) if pids else {
        "by_product": {},
        "unassigned_qty": "0",
    }
    transit_map: dict[int, dict] = incoming.get("by_product") or {}
    residual_map: dict[int, str] = residuals.get("by_product") or {}

    rows: list[dict[str, Any]] = []
    unassigned_qty = _d(incoming.get("unassigned_qty")) + _d(residuals.get("unassigned_qty"))
    for p in products:
        pos = stock.get(p.id) or {"DOMESTIC": "0", "BONDED": "0", "QUARANTINE": "0"}
        domestic = _qty(pos.get("DOMESTIC"))
        bonded = _qty(pos.get("BONDED"))
        quarantine = _qty(pos.get("QUARANTINE"))
        cnr = cleared.get(p.id, "0")
        incoming_cell = _incoming_cell(transit_map.get(p.id), residual_map.get(p.id))
        pending = bool(p.import_decision == "REVISAR" or p.taxonomy_status == "REVIEW" or not p.ncm)
        row = {
            "product_id": p.id,
            "sku": p.sku,
            "unit": p.unit,
            "commercial_name": p.commercial_name,
            "category": p.category.name if p.category else None,
            "product_type": p.product_type.name if p.product_type else None,
            "available_qty": domestic,
            "bonded_qty": bonded,
            "quarantine_qty": quarantine,
            "cleared_not_received_qty": cnr,
            "incoming_qty": incoming_cell,
            "next_eta": (transit_map.get(p.id) or {}).get("next_eta"),
            "needs_attention": pending,
            "href": f"/catalog/products/{p.id}",
            "stock_href": f"/inventory/movements?product_id={p.id}",
        }
        if status == "available" and _d(domestic) <= 0:
            continue
        if status == "incoming" and incoming_cell is None:
            continue
        rows.append(row)

    sku_available = sum(1 for r in rows if _d(r["available_qty"]) > 0)
    units = sorted({r["unit"] or "" for r in rows})
    totals_by_unit = [{"unit": unit or None, "qty": _qty(sum((_d(r["available_qty"]) for r in rows if (r["unit"] or "") == unit), Decimal("0"))) if unit else None} for unit in units]
    units_available = sum((_d(r["available_qty"]) for r in rows), Decimal("0")) if len(units) <= 1 and "" not in units else None
    incoming_skus = sum(1 for r in rows if r["incoming_qty"] is not None)
    pending_skus = sum(1 for r in rows if r["needs_attention"])
    by_category: dict[tuple[str, str], Decimal] = {}
    for r in rows:
        cat = (r.get("category") or "Sem categoria", r.get("unit") or "")
        by_category[cat] = by_category.get(cat, Decimal("0")) + _d(r["available_qty"])

    by_regime = [{"location_type": regime, "unit": unit or None,
                  "sku_count": sum(1 for r in rows if (r["unit"] or "") == unit and _d(r[key]) > 0),
                  "qty": _qty(sum((_d(r[key]) for r in rows if (r["unit"] or "") == unit), Decimal("0"))) if unit else None}
                 for unit in units for regime, key in [("DOMESTIC", "available_qty"), ("BONDED", "bonded_qty"), ("QUARANTINE", "quarantine_qty")]]
    total = len(rows)
    if sort in stock_sorts:
        key = {
            "available": lambda r: _d(r["available_qty"]),
            "-available": lambda r: _d(r["available_qty"]),
            "bonded": lambda r: _d(r["bonded_qty"]),
            "-bonded": lambda r: _d(r["bonded_qty"]),
            "incoming": lambda r: _d(r["incoming_qty"]),
            "-incoming": lambda r: _d(r["incoming_qty"]),
        }[sort]
        reverse = sort.startswith("-")
        rows.sort(key=key, reverse=reverse)
    rows = rows[offset : offset + limit]

    cats, types = catalog_public.taxonomy_catalog(db)
    category_facet = [{"value": c.slug, "label": c.name} for c in cats]
    type_facet = [{"value": t.slug, "label": t.name} for t in types]

    facets = catalog_public.product_facets(
        db,
        catalog_public.ProductListFilters(q=q or None, is_active=True, limit=1, offset=0),
    )

    footer = None
    if unassigned_qty > 0:
        footer = {
            "label": "Não atribuído a produto",
            "qty": _qty(unassigned_qty),
        }

    return {
        "rows": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
        "facets": {
            "category": category_facet,
            "product_type": type_facet,
            **({k: v for k, v in facets.items() if k in {"origin", "sport"}}),
        },
        "totals": {
            "sku_available": sku_available,
            "units_available": _qty(units_available) if units_available is not None else None,
            "by_unit": totals_by_unit,
            "sku_incoming": incoming_skus,
            "sku_attention": pending_skus,
        },
        "by_regime": by_regime,
        "totals_scope": "filtered_population",
        "by_category": [
            {"category": k[0], "unit": k[1] or None, "qty": _qty(v) if k[1] else None} for k, v in sorted(by_category.items(), key=lambda x: -x[1])
        ],
        "footer": footer,
        "empty": total == 0,
        "state": "empty" if total == 0 else "ok",
    }
