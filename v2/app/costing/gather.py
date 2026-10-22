"""Monta componentes (mercadoria, tributos, despesas, expense Costing) e aplica rateio."""

from __future__ import annotations

from decimal import Decimal

from app.costing.allocate import allocate_amount
from app.costing.errors import CostingValidation
from app.costing.freight import (
    ROLE_DOMESTIC_DELIVERY,
    ROLE_DOMESTIC_REMOVAL,
    ROLE_INTERNATIONAL,
    classify_freight_role,
    component_type_for_role,
)
from app.costing.money import money2, parse_decimal


def _type_from_tax(code: str | None, label: str | None) -> str:
    raw = (code or label or "TAX").upper().replace(" ", "_")
    return raw[:64]


def build_components(
    *,
    lines: list[dict],
    facts: dict,
    coverage: dict,
    freight_choice: str | None,
    expenses: list[dict],
    methods: dict[str, str] | None = None,
    manuals: dict[str, dict[str, str]] | None = None,
    kind: str,
) -> list[dict]:
    methods = methods or {}
    manuals = manuals or {}
    components: list[dict] = []
    coverage_ok = coverage.get("coverage") == "COMPLETE"

    # Mercadoria: um componente por Invoice, amount = Σ merchandise_brl.
    by_inv: dict[int, list[dict]] = {}
    for line in lines:
        iid = line.get("invoice_id")
        if iid is None:
            continue
        if line.get("merchandise_brl") is None:
            continue
        by_inv.setdefault(iid, []).append(line)
    for invoice_id, group in sorted(by_inv.items()):
        total = money2(sum((l["merchandise_brl"] for l in group), Decimal("0")))
        allocs = [
            {
                "invoice_item_id": l.get("invoice_item_id"),
                "shipment_item_id": l.get("shipment_item_id"),
                "amount_brl": l["merchandise_brl"],
                "residual_flag": bool(l.get("fx_residual")),
            }
            for l in group
        ]
        components.append(
            {
                "component_type": "MERCADORIA",
                "source_kind": "INVOICE",
                "source_id": invoice_id,
                "amount_orig": None,
                "currency": group[0].get("currency"),
                "amount_brl": total,
                "included": True,
                "allocation_method": "VALUE",
                "fx_rule": group[0].get("fx_status"),
                "status": "OK",
                "notes": None,
                "allocations": allocs,
            }
        )

    for fr in facts.get("fundings") or []:
        if fr.get("status") == "CANCELLED":
            continue
        for tx in fr.get("tax_lines") or []:
            amt = parse_decimal(tx.get("amount"))
            if amt is None:
                continue
            ctype = _type_from_tax(tx.get("code"), tx.get("label"))
            method = methods.get(f"TAX:{tx['id']}", "VALUE")
            included = coverage_ok
            try:
                allocs = allocate_amount(amt, lines, method, manual=manuals.get(f"TAX:{tx['id']}"))
                status = "OK"
                notes = None
            except CostingValidation as exc:
                allocs = []
                status = exc.code
                notes = exc.message
                included = False
            components.append(
                {
                    "component_type": ctype,
                    "source_kind": "TAX_LINE",
                    "source_id": tx["id"],
                    "amount_orig": amt,
                    "currency": tx.get("currency") or "BRL",
                    "amount_brl": money2(amt),
                    "included": included and status == "OK",
                    "allocation_method": method,
                    "fx_rule": "BRL",
                    "status": status,
                    "notes": notes,
                    "allocations": allocs,
                }
            )
        for ex in fr.get("expense_lines") or []:
            amt = parse_decimal(ex.get("amount"))
            if amt is None:
                continue
            role = classify_freight_role(ex.get("code"), ex.get("label"), source="expense")
            ctype = component_type_for_role(
                role, fallback_code=ex.get("code"), fallback_label=ex.get("label")
            )
            method = methods.get(f"EXPENSE:{ex['id']}", "VALUE")
            included = coverage_ok
            if role == ROLE_INTERNATIONAL and freight_choice == "EXCLUDE":
                included = False
            if role == ROLE_INTERNATIONAL and coverage.get("freight_conflict"):
                included = coverage_ok and freight_choice == "EXPENSE_LINE"
            try:
                allocs = allocate_amount(amt, lines, method, manual=manuals.get(f"EXPENSE:{ex['id']}"))
                status = "OK"
                notes = None
            except CostingValidation as exc:
                allocs = []
                status = exc.code
                notes = exc.message
                included = False
            if role == ROLE_INTERNATIONAL and coverage.get("freight_conflict") and freight_choice is None:
                notes = (notes + "; " if notes else "") + "Dois fretes internacionais — escolha explícita"
                status = "FREIGHT_CHOICE_REQUIRED"
            if role in (ROLE_DOMESTIC_REMOVAL, ROLE_DOMESTIC_DELIVERY):
                notes = (notes + "; " if notes else "") + "Despesa logística doméstica"
            components.append(
                {
                    "component_type": ctype,
                    "source_kind": "EXPENSE_LINE",
                    "source_id": ex["id"],
                    "amount_orig": amt,
                    "currency": ex.get("currency") or "BRL",
                    "amount_brl": money2(amt),
                    "included": included and status == "OK",
                    "allocation_method": method,
                    "fx_rule": "BRL",
                    "status": status,
                    "notes": notes,
                    "allocations": allocs,
                }
            )
        # ValueBasis FRETE é base CIF — nunca vira CostComponent.

    for exp in expenses:
        if exp.get("status") != "ACTIVE":
            continue
        amt = parse_decimal(exp.get("amount"))
        if amt is None:
            continue
        method = exp.get("allocation_method") or "VALUE"
        included = True
        if kind == "REALIZED" and not exp.get("document_id"):
            included = False
        try:
            allocs = allocate_amount(amt, lines, method, manual=manuals.get(f"COSTING_EXPENSE:{exp['id']}"))
            status = "OK"
            notes = None
        except CostingValidation as exc:
            allocs = []
            status = exc.code
            notes = exc.message
            included = False
        if kind == "REALIZED" and not exp.get("document_id"):
            status = "DOCUMENT_REQUIRED"
            notes = "Expense Costing exige documento para REALIZED"
        components.append(
            {
                "component_type": f"EXPENSE_COSTING_{(exp.get('category') or 'OUTRAS').upper()}",
                "source_kind": "COSTING_EXPENSE",
                "source_id": exp.get("id"),
                "amount_orig": amt,
                "currency": exp.get("currency") or "BRL",
                "amount_brl": money2(amt),
                "included": included and status == "OK",
                "allocation_method": method,
                "fx_rule": None,
                "status": status,
                "notes": notes,
                "allocations": allocs,
            }
        )
    return components
