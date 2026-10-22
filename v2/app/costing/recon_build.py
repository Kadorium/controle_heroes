"""Pares mínimos de publicação — primitivos; Reconciliation não importa Costing."""

from __future__ import annotations

from decimal import Decimal

from app.costing.money import money2, parse_decimal


def _pair(
    pair_type: str,
    left_label: str,
    left_value,
    right_label: str,
    right_value,
    *,
    delta=None,
    unit: str | None = None,
    tolerance: str | None = None,
    severity: str = "WARNING",
    blocks: bool = False,
) -> dict:
    return {
        "pair_type": pair_type,
        "left_label": left_label,
        "left_value": None if left_value is None else str(left_value),
        "right_label": right_label,
        "right_value": None if right_value is None else str(right_value),
        "delta": None if delta is None else str(delta),
        "unit": unit,
        "tolerance": tolerance,
        "severity": severity,
        "blocks_publish": blocks,
        "status": "OPEN",
        "reason": None,
    }


def build_pairs(
    *,
    kind: str,
    lines: list[dict],
    components: list[dict],
    coverage: dict,
    facts: dict,
    freight_choice: str | None,
) -> list[dict]:
    pairs: list[dict] = []
    coverage_incomplete = coverage.get("coverage") == "INCOMPLETE"
    complete_kinds = kind in ("REVISED", "REALIZED")

    if coverage_incomplete:
        pairs.append(
            _pair(
                "SOURCE_COVERAGE",
                "Faturas do processo",
                ",".join(coverage.get("process_invoice_numbers") or []) or None,
                "Cobertura do Numerário",
                "; ".join(coverage.get("reasons") or []) or "INCOMPLETE",
                severity="BLOCKING",
                blocks=complete_kinds,
            )
        )

    if coverage.get("freight_conflict") and not freight_choice:
        pairs.append(
            _pair(
                "FREIGHT_CONFLICT",
                "Fretes internacionais no Numerário",
                str(coverage.get("international_freight_count") or 0),
                "Escolha explícita",
                freight_choice,
                unit=None,
                severity="BLOCKING",
                blocks=complete_kinds,
            )
        )

    merch_lines = [l for l in lines if l.get("merchandise_brl") is not None]
    merch_sum = money2(sum((l["merchandise_brl"] for l in merch_lines), Decimal("0"))) if merch_lines else None
    inv_net = Decimal("0")
    inv_known = False
    for inv in facts.get("invoices") or []:
        n = parse_decimal(inv.get("net_amount"))
        if n is not None:
            inv_net += n
            inv_known = True
    # Compare merchandise BRL vs invoice foreign net is not same unit — pair process-scoped foreign nets.
    process_net = Decimal("0")
    process_net_known = False
    for line in lines:
        n = parse_decimal(line.get("foreign_net"))
        if n is not None:
            process_net += n
            process_net_known = True
    if merch_lines and process_net_known:
        # FX: Σ line BRL vs Σ fx_invoice_brl unique
        fx_pools = {}
        for line in merch_lines:
            iid = line.get("invoice_id")
            pool = parse_decimal(line.get("fx_invoice_brl"))
            if iid is not None and pool is not None:
                fx_pools[iid] = pool
        pool_sum = money2(sum(fx_pools.values(), Decimal("0"))) if fx_pools else None
        if pool_sum is not None and merch_sum is not None and pool_sum != merch_sum:
            pairs.append(
                _pair(
                    "FX_INVOICE_BRL",
                    "Σ BRL linhas",
                    merch_sum,
                    "Σ BRL Treasury/plano por Invoice",
                    pool_sum,
                    delta=money2(merch_sum - pool_sum),
                    unit="BRL",
                    tolerance="0",
                    severity="BLOCKING",
                    blocks=kind == "REALIZED",
                )
            )

    if any(l.get("fx_status") == "FX_OPEN" for l in lines) and kind == "REALIZED":
        pairs.append(
            _pair(
                "FX_OPEN",
                "FX realizado",
                "incompleto",
                "Saldo estrangeiro aberto",
                "sim",
                severity="BLOCKING",
                blocks=True,
            )
        )

    if coverage.get("funding_included") and coverage.get("funding_delta") is not None:
        ok = coverage.get("funding_math_ok")
        pairs.append(
            _pair(
                "FUNDING_DECLARED",
                "declared_total",
                coverage.get("funding_declared"),
                "Σ tax+expense",
                coverage.get("funding_tax_expense_sum"),
                delta=coverage.get("funding_delta"),
                unit="BRL",
                tolerance="0.01",
                severity="BLOCKING" if not ok else "WARNING",
                blocks=bool(not ok) and any(c["included"] and c["source_kind"] in ("TAX_LINE", "EXPENSE_LINE") for c in components),
            )
        )

    for line in lines:
        qty = parse_decimal(line.get("qty"))
        if qty is None or qty <= 0:
            pairs.append(
                _pair(
                    "QTY",
                    "qty da CostingLine",
                    qty,
                    "esperado > 0",
                    "0",
                    unit="UN",
                    tolerance="0",
                    severity="BLOCKING",
                    blocks=True,
                )
            )
        if line.get("merchandise_source") == "SHIPMENT_ONLY" and kind in ("REVISED", "REALIZED"):
            pairs.append(
                _pair(
                    "MERCHANDISE_MISSING",
                    "linha sem InvoiceItem",
                    f"shipment_item={line.get('shipment_item_id')}",
                    "mercadoria factual",
                    "ausente",
                    severity="BLOCKING",
                    blocks=True,
                )
            )
    if any(l.get("synthesis_ambiguous") for l in lines):
        pairs.append(
            _pair(
                "SYNTHESIS_AMBIGUOUS",
                "Invoice↔Shipment",
                "N correspondências",
                "ligação explícita",
                "ausente",
                severity="BLOCKING",
                blocks=complete_kinds,
            )
        )

    for comp in components:
        allocs = comp.get("allocations") or []
        if comp.get("status") in ("missing_basis", "zero_basis", "manual_sum", "manual_missing_line"):
            pairs.append(
                _pair(
                    "ALLOCATION_BASIS",
                    f"{comp['component_type']} {comp['source_kind']}",
                    comp.get("amount_brl"),
                    "base de rateio",
                    comp.get("notes") or comp.get("status"),
                    severity="BLOCKING",
                    blocks=comp.get("included", False) or complete_kinds,
                )
            )
            continue
        if not allocs:
            continue
        s = money2(sum((a["amount_brl"] for a in allocs), Decimal("0")))
        amt = money2(parse_decimal(comp.get("amount_brl")) or Decimal("0"))
        if s != amt:
            pairs.append(
                _pair(
                    "ALLOCATION_SUM",
                    f"Σ alloc {comp['component_type']}",
                    s,
                    "componente",
                    amt,
                    delta=money2(s - amt),
                    unit="BRL",
                    tolerance="0",
                    severity="BLOCKING",
                    blocks=True,
                )
            )

    sku_total = Decimal("0")
    included_total = Decimal("0")
    by_line: dict[tuple, Decimal] = {}
    for comp in components:
        for a in comp.get("allocations") or []:
            key = (a.get("invoice_item_id"), a.get("shipment_item_id"))
            by_line[key] = by_line.get(key, Decimal("0")) + a["amount_brl"]
            if comp.get("included"):
                included_total += a["amount_brl"]
            sku_total += a["amount_brl"]
    gross = money2(sku_total)
    included = money2(included_total)
    recon_included = money2(
        sum((c["amount_brl"] for c in components if c.get("included") and c.get("amount_brl") is not None), Decimal("0"))
    )
    if included != recon_included:
        pairs.append(
            _pair(
                "SKU_VS_VERSION",
                "Σ SKU incluído",
                included,
                "Σ componentes incluídos",
                recon_included,
                delta=money2(included - recon_included),
                unit="BRL",
                tolerance="0",
                severity="BLOCKING",
                blocks=True,
            )
        )

    for exp_like in components:
        if exp_like["source_kind"] == "COSTING_EXPENSE" and exp_like.get("status") == "DOCUMENT_REQUIRED":
            pairs.append(
                _pair(
                    "EXPENSE_DOCUMENT",
                    exp_like["component_type"],
                    exp_like.get("amount_brl"),
                    "documento",
                    "ausente",
                    severity="BLOCKING",
                    blocks=kind == "REALIZED",
                )
            )

    return pairs
