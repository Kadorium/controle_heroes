"""DEC-J6-LINE-SYNTHESIS — InvoiceItem / ShipmentItem; nunca match por SKU."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.costing.errors import CostingValidation
from app.costing.money import parse_decimal


def _qty(value) -> Decimal:
    d = parse_decimal(value)
    if d is None or d <= 0:
        raise CostingValidation("Quantidade da linha deve ser > 0", code="qty_invalid")
    return d


def synthesize(facts: dict, *, line_links: list[dict] | None = None) -> list[dict]:
    """Retorna linhas candidatas (ainda sem persistência / sem BRL)."""
    inv_lines = list(facts.get("invoice_lines") or [])
    shp_lines = list(facts.get("shipment_lines") or [])
    links = list(line_links or [])

    used_inv: set[int] = set()
    used_shp: set[int] = set()
    out: list[dict] = []
    ambiguous = False

    def _from_inv(inv: dict, shp: dict | None, qty: Decimal) -> dict:
        return {
            "invoice_item_id": inv["invoice_item_id"],
            "shipment_item_id": shp["shipment_item_id"] if shp else None,
            "order_item_id": inv.get("order_item_id")
            or (shp.get("order_item_id") if shp else None),
            "product_id": inv.get("product_id") or (shp.get("product_id") if shp else None),
            "sku_snapshot": inv.get("sku_snapshot") or (shp.get("sku") if shp else ""),
            "description_snapshot": inv.get("description_snapshot")
            or (shp.get("description") if shp else ""),
            "qty": qty,
            "foreign_net": parse_decimal(inv.get("process_net")),
            "currency": inv.get("currency"),
            "invoice_id": inv.get("invoice_id"),
            "invoice_status": inv.get("invoice_status"),
            "net_weight_kg": parse_decimal(shp.get("net_weight_kg")) if shp else None,
            "volume_m3": parse_decimal(shp.get("volume_m3")) if shp else None,
            "merchandise_source": "INVOICE",
        }

    def _from_shp(shp: dict) -> dict:
        return {
            "invoice_item_id": None,
            "shipment_item_id": shp["shipment_item_id"],
            "order_item_id": shp.get("order_item_id"),
            "product_id": shp.get("product_id"),
            "sku_snapshot": shp.get("sku") or "",
            "description_snapshot": shp.get("description") or "",
            "qty": _qty(shp.get("allocated_qty") or shp.get("quantity")),
            "foreign_net": None,
            "currency": None,
            "invoice_id": None,
            "invoice_status": None,
            "net_weight_kg": parse_decimal(shp.get("net_weight_kg")),
            "volume_m3": parse_decimal(shp.get("volume_m3")),
            "merchandise_source": "SHIPMENT_ONLY",
        }

    # Explicit links first.
    inv_by_id = {i["invoice_item_id"]: i for i in inv_lines}
    shp_by_id = {s["shipment_item_id"]: s for s in shp_lines}
    for link in links:
        iid = link.get("invoice_item_id")
        sid = link.get("shipment_item_id")
        if iid is None and sid is None:
            raise CostingValidation("Ligação de linha exige invoice_item_id ou shipment_item_id")
        if iid is not None and iid in used_inv:
            raise CostingValidation("InvoiceItem já ligado nesta versão", code="duplicate_invoice_item")
        if sid is not None and sid in used_shp:
            raise CostingValidation("ShipmentItem já ligado nesta versão", code="duplicate_shipment_item")
        inv = inv_by_id.get(iid) if iid is not None else None
        shp = shp_by_id.get(sid) if sid is not None else None
        if iid is not None and inv is None:
            raise CostingValidation(f"InvoiceItem {iid} não alocado no processo")
        if sid is not None and shp is None:
            raise CostingValidation(f"ShipmentItem {sid} não alocado no processo")
        if inv and shp:
            if inv.get("order_item_id") != shp.get("order_item_id"):
                raise CostingValidation(
                    "Ligação Invoice↔Shipment só é válida com o mesmo order_item_id",
                    code="synthesis_order_item_mismatch",
                )
            qty = parse_decimal(link.get("qty")) or _qty(inv.get("allocated_qty"))
            out.append(_from_inv(inv, shp, qty))
        elif inv:
            out.append(_from_inv(inv, None, _qty(inv.get("allocated_qty"))))
        else:
            out.append(_from_shp(shp))
        if iid is not None:
            used_inv.add(iid)
        if sid is not None:
            used_shp.add(sid)

    remaining_inv = [i for i in inv_lines if i["invoice_item_id"] not in used_inv]
    remaining_shp = [s for s in shp_lines if s["shipment_item_id"] not in used_shp]

    inv_by_oi: dict[int, list] = defaultdict(list)
    shp_by_oi: dict[int, list] = defaultdict(list)
    for i in remaining_inv:
        oi = i.get("order_item_id")
        if oi is not None:
            inv_by_oi[oi].append(i)
    for s in remaining_shp:
        oi = s.get("order_item_id")
        if oi is not None:
            shp_by_oi[oi].append(s)

    matched_inv: set[int] = set()
    matched_shp: set[int] = set()
    ois = set(inv_by_oi) | set(shp_by_oi)
    for oi in sorted(ois):
        ivs = inv_by_oi.get(oi, [])
        shs = shp_by_oi.get(oi, [])
        if len(ivs) == 1 and len(shs) == 1:
            inv, shp = ivs[0], shs[0]
            qty = _qty(inv.get("allocated_qty"))
            out.append(_from_inv(inv, shp, qty))
            matched_inv.add(inv["invoice_item_id"])
            matched_shp.add(shp["shipment_item_id"])
        elif len(ivs) > 1 or (len(ivs) >= 1 and len(shs) > 1) or (len(shs) > 1 and len(ivs) >= 1):
            if ivs and shs:
                ambiguous = True

    for inv in remaining_inv:
        if inv["invoice_item_id"] in matched_inv:
            continue
        out.append(_from_inv(inv, None, _qty(inv.get("allocated_qty"))))
    for shp in remaining_shp:
        if shp["shipment_item_id"] in matched_shp:
            continue
        out.append(_from_shp(shp))

    if not out:
        raise CostingValidation(
            "Processo sem InvoiceItem ou ShipmentItem alocado — não há linha de custo",
            code="no_costing_lines",
        )
    out.sort(
        key=lambda r: (
            r.get("invoice_item_id") or 0,
            r.get("shipment_item_id") or 0,
            r.get("sku_snapshot") or "",
        )
    )
    for row in out:
        row["synthesis_ambiguous"] = ambiguous
    return out
