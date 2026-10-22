"""Rateio por componente — base explícita; ausência bloqueia; residual na última linha estável."""

from __future__ import annotations

from decimal import Decimal

from app.costing.errors import CostingValidation
from app.costing.money import alloc6, money2, parse_decimal


def line_key(line: dict) -> tuple:
    return (
        line.get("invoice_item_id") or 0,
        line.get("shipment_item_id") or 0,
        line.get("sku_snapshot") or "",
    )


def stable_lines(lines: list[dict]) -> list[dict]:
    return sorted(lines, key=line_key)


def weights_for(lines: list[dict], method: str) -> list[Decimal | None]:
    method = (method or "VALUE").upper()
    out: list[Decimal | None] = []
    for line in lines:
        if method == "VALUE":
            out.append(parse_decimal(line.get("merchandise_brl")))
        elif method == "QUANTITY":
            out.append(parse_decimal(line.get("qty")))
        elif method == "WEIGHT":
            out.append(parse_decimal(line.get("net_weight_kg")))
        elif method == "VOLUME":
            out.append(parse_decimal(line.get("volume_m3")))
        elif method == "MANUAL":
            out.append(parse_decimal(line.get("manual_weight")))
        else:
            raise CostingValidation(f"Método de rateio inválido: {method}", code="allocation_method")
    return out


def allocate_amount(
    total: Decimal,
    lines: list[dict],
    method: str,
    *,
    manual: dict[str, str] | None = None,
) -> list[dict]:
    """Retorna [{line_ref, amount_brl, residual_flag}]. Soma = total (money2)."""
    ordered = stable_lines(lines)
    if method.upper() == "MANUAL":
        if not manual:
            raise CostingValidation("Rateio MANUAL exige mapa explícito", code="manual_required")
        amounts = []
        acc = Decimal("0")
        for i, line in enumerate(ordered):
            key = f"{line.get('invoice_item_id') or ''}:{line.get('shipment_item_id') or ''}"
            part = parse_decimal(manual.get(key))
            if part is None:
                raise CostingValidation(
                    f"Rateio MANUAL sem valor para linha {key}", code="manual_missing_line"
                )
            amounts.append(money2(part))
            acc += money2(part)
        if money2(acc) != money2(total):
            raise CostingValidation(
                f"Rateio MANUAL ({acc}) deve fechar o componente ({total})",
                code="manual_sum",
            )
        last = len(ordered) - 1
        return [
            {
                "invoice_item_id": line.get("invoice_item_id"),
                "shipment_item_id": line.get("shipment_item_id"),
                "amount_brl": amounts[i],
                "residual_flag": i == last,
            }
            for i, line in enumerate(ordered)
        ]

    ws = weights_for(ordered, method)
    if any(w is None for w in ws):
        raise CostingValidation(
            f"Base {method} ausente — não preencher com zero", code="missing_basis"
        )
    s = sum((w for w in ws if w is not None), Decimal("0"))
    if s <= 0:
        raise CostingValidation(f"Base {method} soma zero — não ratear", code="zero_basis")

    total = money2(total)
    allocated = Decimal("0")
    last = len(ordered) - 1
    rows = []
    for i, line in enumerate(ordered):
        w = ws[i] or Decimal("0")
        if i == last:
            amount = money2(total - allocated)
            residual = True
        else:
            amount = money2(total * w / s)
            allocated += amount
            residual = False
        rows.append(
            {
                "invoice_item_id": line.get("invoice_item_id"),
                "shipment_item_id": line.get("shipment_item_id"),
                "amount_brl": amount,
                "residual_flag": residual,
            }
        )
    return rows
