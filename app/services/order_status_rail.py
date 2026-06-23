"""Régua de status da Central da Ordem — derivada de dados reais."""

from __future__ import annotations

RAIL_STAGES = [
    {"key": "pedido", "label": "Pedido", "statuses": ["PO_CREATED", "SI_OPEN", "PROFORMA_RECEIVED"]},
    {"key": "faturado", "label": "Faturado", "statuses": ["PROFORMA_RECEIVED", "ADVANCE_PAID", "PARTIAL_PAID", "FULL_PAID"]},
    {"key": "acconto", "label": "Acconto", "statuses": ["ADVANCE_PAID", "PARTIAL_PAID"]},
    {"key": "despachar", "label": "A despachar", "statuses": ["BOOKED", "SHIPPED"]},
    {"key": "transito", "label": "Em trânsito", "statuses": ["IN_TRANSIT", "SHIPPED"]},
    {"key": "aduana", "label": "Aduana", "statuses": ["ARRIVED", "DI_SUBMITTED", "DUIMP_REGISTERED", "CUSTOMS_RELEASED", "CLEARED"]},
    {"key": "estoque", "label": "Estoque", "statuses": ["RECEIVED_IN_STOCK", "DELIVERED"]},
    {"key": "fechado", "label": "Fechado", "statuses": ["CLOSED"]},
]


def _status_implies_stage(current_status: str, stage: dict) -> bool:
    return current_status in stage["statuses"]


def _stage_index_for_status(current_status: str) -> int:
    for i, stage in enumerate(RAIL_STAGES):
        if current_status in stage["statuses"]:
            return i
    if current_status == "PO_CREATED":
        return 0
    return 0


def _stage_data_supported(
    key: str,
    *,
    has_invoices: bool,
    has_payments: bool,
    has_shipments: bool,
    shipment_in_transit: bool,
    has_customs: bool,
    has_stock: bool,
    is_closed: bool,
) -> bool:
    if key == "pedido":
        return True
    if key == "faturado":
        return has_invoices
    if key == "acconto":
        return has_payments
    if key == "despachar":
        return has_shipments
    if key == "transito":
        return shipment_in_transit
    if key == "aduana":
        return has_customs
    if key == "estoque":
        return has_stock
    if key == "fechado":
        return is_closed
    return False


def _rail_subtitle(key: str, rail_context: dict | None) -> str | None:
    if not rail_context:
        return None
    ctx = rail_context
    if key == "faturado":
        total = ctx.get("invoices_count") or 0
        settled = ctx.get("invoices_settled_count") or 0
        if total > 0:
            return f"{settled}/{total} faturas"
    if key == "acconto":
        paid = ctx.get("total_paid")
        cur = ctx.get("currency") or "EUR"
        if paid:
            return f"{cur} {paid} versato"
    if key in ("despachar", "transito"):
        eta = ctx.get("next_eta")
        if eta:
            return f"ETA {eta.strftime('%d/%m')}"
        td = ctx.get("to_dispatch")
        qty = ctx.get("quantity_ordered")
        if td is not None and qty:
            return f"{qty - td}/{qty} un."
    return None


def build_status_rail(
    current_status: str,
    *,
    has_invoices: bool,
    has_payments: bool,
    has_shipments: bool,
    shipment_in_transit: bool,
    has_customs: bool = False,
    has_stock: bool = False,
    is_closed: bool = False,
    rail_context: dict | None = None,
) -> dict:
    """Deriva estados da régua a partir de dados reais; valida current_status declarado."""
    stages: list[dict] = []
    alerts: list[str] = []
    declared_idx = _stage_index_for_status(current_status)

    for i, stage in enumerate(RAIL_STAGES):
        key = stage["key"]
        declared = _status_implies_stage(current_status, stage) or i <= declared_idx
        supported = _stage_data_supported(
            key,
            has_invoices=has_invoices,
            has_payments=has_payments,
            has_shipments=has_shipments,
            shipment_in_transit=shipment_in_transit,
            has_customs=has_customs,
            has_stock=has_stock,
            is_closed=is_closed,
        )
        if supported:
            state = "done"
        elif declared and key != "pedido":
            state = "declared_without_data"
            alerts.append(f"Status {stage['label']} declarado sem dado de suporte")
        elif declared and i == declared_idx:
            state = "now"
        else:
            state = "todo"
        stages.append(
            {
                "key": key,
                "label": stage["label"],
                "state": state,
                "data_supported": supported,
                "status_declared": declared,
                "subtitle": _rail_subtitle(key, rail_context),
            }
        )

    current_idx = 0
    for i, s in enumerate(stages):
        if s["state"] in ("done", "now", "declared_without_data"):
            current_idx = i

    return {"stages": stages, "current_index": current_idx, "alerts": list(dict.fromkeys(alerts))}
