"""Revisão financeira Heroes — versato, acconti e acconto rimasto (informativo)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.parse import optional_decimal
from app.services.heroes_invoice_blocks import get_invoice_blocks_for_preview

TOLERANCE = Decimal("0.01")


def _decimal_str(val: Decimal | None) -> str | None:
    return str(val) if val is not None else None


def build_financial_review(preview: dict[str, Any]) -> dict[str, Any]:
    """Deriva totais e warnings para revisão manual antes do commit."""
    legacy = preview.get("legacy_sheet_summary") or {}
    versato = optional_decimal(legacy.get("versato_amount"))
    currency = legacy.get("versato_currency") or preview.get("currency") or "EUR"

    acconto_total = Decimal("0")
    last_rimasto: Decimal | None = None
    last_rimasto_row: int | None = None

    for row in preview.get("invoice_items") or []:
        rim = optional_decimal(row.get("acconto_remaining"))
        if rim is not None:
            last_rimasto = rim
            last_rimasto_row = row.get("row_number")

    invoice_rows: list[dict[str, Any]] = []
    for block in get_invoice_blocks_for_preview(preview):
        inv_num = block.get("invoice_number") or "—"
        payments = block.get("acconto_payments") or []
        acconto_sum = Decimal("0")
        for pay in payments:
            amt = optional_decimal(pay.get("amount"))
            if amt is not None:
                acconto_sum += amt
        acconto_total += acconto_sum
        rimasto = optional_decimal(block.get("acconto_remaining"))
        invoice_rows.append(
            {
                "invoice_number": inv_num,
                "invoice_date": block.get("invoice_date"),
                "acconto_amount": _decimal_str(acconto_sum) if acconto_sum else None,
                "acconto_remaining": _decimal_str(rimasto),
            }
        )

    warnings: list[str] = []
    expected_rimasto: Decimal | None = None
    delta_rimasto: Decimal | None = None
    delta_versato: Decimal | None = None

    if versato is not None:
        expected_rimasto = versato - acconto_total
        delta_versato = acconto_total - versato
        if delta_versato > TOLERANCE:
            warnings.append(
                f"Soma dos acconti ({acconto_total}) excede versato ({versato}) em {delta_versato}."
            )
        if last_rimasto is not None and expected_rimasto is not None:
            delta_rimasto = last_rimasto - expected_rimasto
            if abs(delta_rimasto) > TOLERANCE:
                warnings.append(
                    f"Último acconto rimasto ({last_rimasto}) difere do esperado "
                    f"versato − Σ acconti ({expected_rimasto}) em {delta_rimasto}."
                )
        elif last_rimasto is None and acconto_total > Decimal("0"):
            warnings.append("Acconti detectados sem acconto rimasto na planilha — revisar.")

    return {
        "versato_amount": _decimal_str(versato),
        "versato_currency": currency,
        "acconto_total": _decimal_str(acconto_total) if acconto_total else None,
        "last_acconto_rimasto": _decimal_str(last_rimasto),
        "last_acconto_rimasto_row": last_rimasto_row,
        "expected_rimasto": _decimal_str(expected_rimasto),
        "delta_rimasto": _decimal_str(delta_rimasto),
        "delta_versato": _decimal_str(delta_versato),
        "warnings": warnings,
        "requires_manual_review": len(warnings) > 0,
        "invoice_rows": invoice_rows,
    }


def attach_financial_review_to_preview(preview: dict[str, Any]) -> dict[str, Any]:
    preview["financial_review"] = build_financial_review(preview)
    return preview


def apply_financial_overrides(
    preview: dict[str, Any],
    *,
    versato_override: str | None = None,
    acconto_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Aplica ajustes manuais do preview antes do commit."""
    if versato_override is not None:
        legacy = dict(preview.get("legacy_sheet_summary") or {})
        legacy["versato_amount"] = versato_override
        preview["legacy_sheet_summary"] = legacy

    if acconto_overrides:
        blocks = get_invoice_blocks_for_preview(preview)
        for block in blocks:
            inv_num = str(block.get("invoice_number") or "")
            if inv_num not in acconto_overrides:
                continue
            amount = acconto_overrides[inv_num]
            block["acconto_payments"] = [
                {
                    "amount": amount,
                    "receipt_reference": f"ACCONTO-{inv_num}",
                }
            ]
        preview["invoice_blocks"] = blocks

    attach_financial_review_to_preview(preview)
    return preview
