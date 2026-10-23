"""Read-only physical stock projection. No receipt/cost calculation and no default-location writes."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session
from app.catalog import public as catalog
from app.inventory.models import StockBalance, StockLocation

REGIMES = ("DOMESTIC", "BONDED", "QUARANTINE")


def positions(db: Session, *, q=None, product_id=None, regime=None, location_id=None, status="positive", sort="name", limit=25, offset=0):
    products = catalog.stock_product_population(db, q)
    if product_id is not None:
        products = [p for p in products if p["product_id"] == product_id]
    balances = db.query(StockBalance.product_id, StockBalance.location_id, StockBalance.qty,
                        StockLocation.code, StockLocation.name, StockLocation.location_type).join(
                            StockLocation, StockLocation.id == StockBalance.location_id)
    by_product = defaultdict(list)
    locations = {}
    for row in balances.all():
        locations[row.location_id] = {"id": row.location_id, "name": row.name, "regime": row.location_type}
        if regime and row.location_type != regime or location_id and row.location_id != location_id:
            continue
        by_product[row.product_id].append({"location_id": row.location_id, "code": row.code,
            "name": row.name, "regime": row.location_type, "qty": str(row.qty)})
    rows = []
    for p in products:
        local = by_product[p["product_id"]]
        amounts = {r: sum((Decimal(b["qty"]) for b in local if b["regime"] == r), Decimal(0)) for r in REGIMES}
        positive = any(v > 0 for v in amounts.values())
        if status == "positive" and not positive or status == "zero" and any(v != 0 for v in amounts.values()):
            continue
        rows.append({**p, "quantities": {k: str(v) for k, v in amounts.items()}, "balances": local})
    totals = defaultdict(lambda: {r: Decimal(0) for r in REGIMES})
    for p in rows:
        for r in REGIMES:
            totals[p["unit"]][r] += Decimal(p["quantities"][r])
    key = sort.lstrip("-")
    rows.sort(key=lambda r: (r["name"].casefold(), r["product_id"]))
    if key in REGIMES:
        rows.sort(key=lambda r: Decimal(r["quantities"][key]), reverse=sort.startswith("-"))
    elif key == "sku":
        rows.sort(key=lambda r: (r["sku"].casefold(), r["product_id"]), reverse=sort.startswith("-"))
    elif sort == "-name":
        rows.reverse()
    return {"rows": rows[offset:offset+limit], "total": len(rows), "limit": limit, "offset": offset,
        "locations": sorted(locations.values(), key=lambda loc: (loc["name"].casefold(), loc["id"])),
        "totals": [{"unit": unit, "quantities": {r: str(v) if unit else None for r,v in amounts.items()},
                    "sku_count": sum(1 for p in rows if p["unit"] == unit),
                    "quantity_state": "known" if unit else "unit_missing"} for unit, amounts in sorted(totals.items(), key=lambda x:x[0] or "")],
        "filters": {"q": q, "product_id": product_id, "regime": regime, "location_id": location_id, "status": status, "sort": sort},
        "scope": "current_physical_filtered_population", "state": "ok" if rows else "empty",
        "generated_at": datetime.now(timezone.utc).isoformat()}
