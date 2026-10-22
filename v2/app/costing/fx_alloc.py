"""DEC-J6-FX-ITEM-ALLOCATION — BRL Treasury da Invoice → linhas pelo líquido estrangeiro."""

from __future__ import annotations

from decimal import Decimal

from app.costing.money import alloc6, money2, parse_decimal


def apply_fx(lines: list[dict], invoices: list[dict], *, kind: str) -> list[dict]:
    by_inv = {i["invoice_id"]: i for i in invoices}
    grouped: dict[int | None, list[dict]] = {}
    for line in lines:
        grouped.setdefault(line.get("invoice_id"), []).append(line)

    for invoice_id, group in grouped.items():
        if invoice_id is None:
            for line in group:
                line["merchandise_brl"] = None
                line["fx_status"] = "NO_INVOICE"
                line["fx_invoice_brl"] = None
            continue
        inv = by_inv.get(invoice_id) or {}
        fx = inv.get("fx") or {}
        currency = group[0].get("currency") or inv.get("currency")
        foreign_nets = [parse_decimal(l.get("foreign_net")) for l in group]
        if any(n is None for n in foreign_nets):
            for line in group:
                line["merchandise_brl"] = None
                line["fx_status"] = "NET_MISSING"
                line["fx_invoice_brl"] = None
            continue
        scope = sum((n for n in foreign_nets if n is not None), Decimal("0"))

        if currency == "BRL":
            pool = money2(scope)
            status = "BRL"
        else:
            realized = parse_decimal(fx.get("realized_brl")) or Decimal("0")
            initial = parse_decimal(fx.get("initial_rate"))
            current = parse_decimal(fx.get("current_rate"))
            open_foreign = parse_decimal(fx.get("open_foreign")) or Decimal("0")
            has_realized = bool(fx.get("has_realized"))
            if kind == "REALIZED":
                if open_foreign > 0 or not has_realized:
                    for line in group:
                        line["merchandise_brl"] = None
                        line["fx_status"] = "FX_OPEN"
                        line["fx_invoice_brl"] = None
                    continue
                pool = money2(realized)
                status = "REALIZED"
            elif kind == "REVISED":
                if has_realized:
                    rest = Decimal("0")
                    rate = current or initial
                    if open_foreign > 0 and rate:
                        rest = money2(open_foreign * rate)
                    pool = money2(realized + rest)
                    status = "REVISED_MIXED" if open_foreign > 0 else "REALIZED"
                elif current:
                    pool = money2(scope * current)
                    status = "CURRENT"
                elif initial:
                    pool = money2(scope * initial)
                    status = "INITIAL"
                else:
                    for line in group:
                        line["merchandise_brl"] = None
                        line["fx_status"] = "FX_MISSING"
                        line["fx_invoice_brl"] = None
                    continue
            else:  # ESTIMATED
                rate = initial or current
                if rate is None:
                    for line in group:
                        line["merchandise_brl"] = None
                        line["fx_status"] = "FX_MISSING"
                        line["fx_invoice_brl"] = None
                    continue
                pool = money2(scope * rate)
                status = "INITIAL"

        if scope == 0:
            for line in group:
                line["merchandise_brl"] = None
                line["fx_status"] = "ZERO_NET"
                line["fx_invoice_brl"] = str(pool)
            continue

        allocated = Decimal("0")
        last_i = len(group) - 1
        for i, line in enumerate(group):
            net = parse_decimal(line["foreign_net"]) or Decimal("0")
            if i == last_i:
                share = money2(pool - allocated)
                line["fx_residual"] = True
            else:
                share = money2(pool * net / scope)
                allocated += share
                line["fx_residual"] = False
            line["merchandise_brl"] = share
            line["fx_status"] = status
            line["fx_invoice_brl"] = str(pool)
    return lines
