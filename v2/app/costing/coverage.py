"""DEC-J6-SOURCE-COVERAGE. Frete CIF (ValueBasis) não conflita com FRETE INTERNACIONAL."""

from __future__ import annotations

import re
from decimal import Decimal

from app.costing.freight import (
    ROLE_CUSTOMS_BASIS,
    ROLE_DOMESTIC_DELIVERY,
    ROLE_DOMESTIC_REMOVAL,
    ROLE_INTERNATIONAL,
    classify_freight_role,
)
from app.costing.money import money2, parse_decimal

_INV_RE = re.compile(r"\b(?:INV[-\s]?)?(\d{3,})\b", re.I)
_FOB_RE = re.compile(r"\bFOB\b", re.I)


def _is_fob(code: str | None, label: str | None) -> bool:
    blob = f"{code or ''} {label or ''}"
    return bool(_FOB_RE.search(blob))


def analyze(facts: dict) -> dict:
    invoices = facts.get("invoices") or []
    process_numbers = {str(i.get("invoice_number") or "").strip() for i in invoices}
    process_digits = set()
    for n in process_numbers:
        process_digits.update(_INV_RE.findall(n))
        if n.isdigit():
            process_digits.add(n)

    merch = Decimal("0")
    merch_currency = None
    merch_known = False
    for line in facts.get("invoice_lines") or []:
        net = parse_decimal(line.get("process_net"))
        if net is not None:
            merch += net
            merch_known = True
            merch_currency = merch_currency or line.get("currency")

    coverage = "COMPLETE"
    reasons: list[str] = []
    mentioned: set[str] = set()
    fob_amount = None
    fob_currency = None
    freight_basis = None
    international_expenses: list[dict] = []
    domestic_expenses: list[dict] = []
    tax_sum = Decimal("0")
    exp_sum = Decimal("0")
    declared = None
    funding_included = False

    for fr in facts.get("fundings") or []:
        if fr.get("status") == "CANCELLED":
            continue
        funding_included = True
        declared = parse_decimal(fr.get("declared_total"))
        text = " ".join(filter(None, [fr.get("reference"), fr.get("notes")]))
        mentioned.update(_INV_RE.findall(text or ""))
        for vb in fr.get("value_bases") or []:
            if _is_fob(vb.get("code"), vb.get("label")):
                fob_amount = parse_decimal(vb.get("amount"))
                fob_currency = vb.get("currency")
            role = classify_freight_role(vb.get("code"), vb.get("label"), source="value_basis")
            if role == ROLE_CUSTOMS_BASIS:
                freight_basis = vb
        for tx in fr.get("tax_lines") or []:
            amt = parse_decimal(tx.get("amount"))
            if amt is not None:
                tax_sum += amt
        for ex in fr.get("expense_lines") or []:
            amt = parse_decimal(ex.get("amount"))
            if amt is not None:
                exp_sum += amt
            role = classify_freight_role(ex.get("code"), ex.get("label"), source="expense")
            if role == ROLE_INTERNATIONAL:
                international_expenses.append(ex)
            elif role in (ROLE_DOMESTIC_REMOVAL, ROLE_DOMESTIC_DELIVERY):
                domestic_expenses.append(ex)

    extra_refs = sorted(n for n in mentioned if n not in process_digits and n not in process_numbers)
    if extra_refs:
        coverage = "INCOMPLETE"
        reasons.append(
            f"Numerário cita faturas fora deste processo: {', '.join(extra_refs)}"
        )

    if fob_amount is not None and merch_known and merch_currency and fob_currency:
        if fob_currency == merch_currency and money2(abs(fob_amount - merch)) > money2(Decimal("0.01")):
            if abs(fob_amount - merch) > max(Decimal("1"), merch * Decimal("0.05")):
                coverage = "INCOMPLETE"
                reasons.append(
                    f"FOB do Numerário ({fob_amount} {fob_currency}) não cobre só a mercadoria "
                    f"deste processo ({merch} {merch_currency})"
                )

    # ValueBasis CIF e FRETE INTERNACIONAL são fatos distintos — não abrem FREIGHT_CONFLICT.
    freight_conflict = len(international_expenses) > 1

    funding_math_ok = True
    funding_delta = None
    if declared is not None and funding_included:
        funding_delta = money2((tax_sum + exp_sum) - declared)
        if abs(funding_delta) > Decimal("0.01"):
            funding_math_ok = False

    mentioned_sorted = sorted(mentioned)
    return {
        "coverage": coverage,
        "reasons": reasons,
        "process_invoice_numbers": sorted(process_numbers),
        "mentioned_invoice_refs": mentioned_sorted,
        "extra_refs": extra_refs,
        "invoice_count": len(process_numbers),
        "mentioned_count": len(mentioned_sorted),
        "fob_amount": str(fob_amount) if fob_amount is not None else None,
        "fob_currency": fob_currency,
        "merchandise_foreign": str(merch) if merch_known else None,
        "merchandise_currency": merch_currency,
        "freight_conflict": freight_conflict,
        "freight_basis": freight_basis,
        "freight_expense": international_expenses[0] if international_expenses else None,
        "international_freight_count": len(international_expenses),
        "domestic_freight_count": len(domestic_expenses),
        "funding_included": funding_included,
        "funding_declared": str(declared) if declared is not None else None,
        "funding_tax_expense_sum": str(money2(tax_sum + exp_sum)) if funding_included else None,
        "funding_delta": str(funding_delta) if funding_delta is not None else None,
        "funding_math_ok": funding_math_ok,
    }
