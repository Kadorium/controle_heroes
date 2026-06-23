"""Agregações do painel operacional — sem inventar dados ausentes."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.currency import normalize_import_currency
from app.core.enums import (
    RECONCILIATION_TOLERANCE_AMOUNT,
    CustomsDocumentStatus,
    ReviewQueueStatus,
)
from app.models import (
    CustomsDocument,
    DocumentAttachment,
    ImportationItem,
    ImportationOrder,
    Invoice,
    LandedCostVersion,
    Payment,
    Reconciliation,
    ReviewQueueItem,
    Shipment,
    StockEntry,
    Supplier,
)
from app.services.finance import importation_financial_summary, invoice_balance, payments_due_summary
from app.services.nationalization import quantity_chain
from app.services.reconciliation import blocking_reconciliations

STAGE_LABELS = [
    "Pedido",
    "Proforma",
    "Pago",
    "Embarcado",
    "Trânsito",
    "Aduana",
    "Fechado",
]

IN_TRANSIT_STATUSES = frozenset({"BOOKED", "SHIPPED", "IN_TRANSIT", "ARRIVED"})

CLOSED_STATUS = "CLOSED"


def stage_index_of(status: str) -> int:
    match status:
        case "PO_CREATED" | "ON_HOLD":
            return 0
        case "PROFORMA_RECEIVED":
            return 1
        case "ADVANCE_PAID" | "PARTIAL_PAID" | "FULL_PAID":
            return 2
        case "BOOKED" | "SHIPPED":
            return 3
        case "IN_TRANSIT":
            return 4
        case "ARRIVED":
            return 5
        case "CLOSED":
            return 6
        case _:
            return 0


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _format_eta(shipment: Shipment | None) -> str | None:
    if not shipment:
        return None
    eta: date | None = shipment.eta_actual or shipment.eta_planned
    if eta is None:
        return None
    return eta.isoformat()


def _first_shipments(db: Session, importation_ids: list[int]) -> dict[int, Shipment]:
    if not importation_ids:
        return {}
    rows = (
        db.query(Shipment)
        .filter(
            Shipment.importation_id.in_(importation_ids),
            Shipment.is_active.is_(True),
        )
        .order_by(Shipment.importation_id, Shipment.created_at.asc())
        .all()
    )
    out: dict[int, Shipment] = {}
    for s in rows:
        out.setdefault(s.importation_id, s)
    return out


def _stock_by_importation(db: Session, importation_ids: list[int]) -> dict[int, int]:
    if not importation_ids:
        return {}
    rows = (
        db.query(ImportationItem.importation_id, func.coalesce(func.sum(StockEntry.quantity_received), 0))
        .join(StockEntry, StockEntry.importation_item_id == ImportationItem.id)
        .filter(ImportationItem.importation_id.in_(importation_ids))
        .group_by(ImportationItem.importation_id)
        .all()
    )
    return {int(imp_id): int(total or 0) for imp_id, total in rows}


def _lc_by_importation(db: Session, importation_ids: list[int]) -> dict[int, LandedCostVersion]:
    if not importation_ids:
        return {}
    rows = (
        db.query(LandedCostVersion)
        .filter(LandedCostVersion.importation_id.in_(importation_ids))
        .order_by(
            LandedCostVersion.importation_id,
            LandedCostVersion.is_current_version.desc(),
            LandedCostVersion.version_number.desc(),
        )
        .all()
    )
    out: dict[int, LandedCostVersion] = {}
    for lc in rows:
        out.setdefault(lc.importation_id, lc)
    return out


def _divergent_by_importation(db: Session, importation_ids: list[int]) -> dict[int, list[Reconciliation]]:
    if not importation_ids:
        return {}
    rows = db.query(Reconciliation).filter(Reconciliation.importation_id.in_(importation_ids)).all()
    out: dict[int, list[Reconciliation]] = defaultdict(list)
    for r in rows:
        if r.status == "DIVERGENT" or (r.severity == "BLOCKING" and r.status != "OK"):
            out[r.importation_id].append(r)
    return dict(out)


def _count_closure_pending(db: Session, imp: ImportationOrder) -> int:
    """Contagem read-only de itens do checklist de fechamento que falhariam."""
    pending = 0
    inv_count = (
        db.query(Invoice)
        .filter(Invoice.importation_id == imp.id, Invoice.is_active.is_(True))
        .count()
    )
    if inv_count == 0:
        pending += 1

    summary = importation_financial_summary(db, imp)
    bal = summary["consolidated_balance"]
    if bal is not None:
        if _d(Decimal(str(bal))).copy_abs() > RECONCILIATION_TOLERANCE_AMOUNT:
            pending += 1
    else:
        pending += 1

    di_ok = (
        db.query(CustomsDocument)
        .filter(
            CustomsDocument.importation_id == imp.id,
            CustomsDocument.status == CustomsDocumentStatus.OFFICIAL.value,
            CustomsDocument.is_valid.is_(True),
        )
        .count()
        > 0
    )
    if not di_ok:
        pending += 1

    proforma = (
        db.query(DocumentAttachment)
        .filter(
            DocumentAttachment.entity_type == "importation_order",
            DocumentAttachment.entity_id == str(imp.id),
            DocumentAttachment.document_type == "PROFORMA",
            DocumentAttachment.is_current_version.is_(True),
        )
        .count()
        > 0
    )
    if not proforma:
        pending += 1

    lc_final = (
        db.query(LandedCostVersion)
        .filter(
            LandedCostVersion.importation_id == imp.id,
            LandedCostVersion.version_type == "FINAL",
        )
        .first()
    )
    if lc_final is None:
        pending += 1

    chain = quantity_chain(db, imp.id)
    nat_ok = any((c.get("quantity_nationalized") or 0) > 0 for c in chain) if chain else False
    if not nat_ok:
        pending += 1

    if blocking_reconciliations(db, imp.id):
        pending += 1

    return pending


def _build_action_items(
    db: Session,
    imp: ImportationOrder,
    *,
    has_official_customs: bool,
    divergent: list[Reconciliation],
    closure_pending: int,
) -> list[dict]:
    items: list[dict] = []
    if imp.current_status in IN_TRANSIT_STATUSES and not has_official_customs:
        items.append(
            {
                "kind": "customs",
                "label": "DI/DUIMP",
                "detail": "documento oficial faltando",
                "tone": "danger",
            }
        )
    if divergent:
        items.append(
            {
                "kind": "reconciliations",
                "label": "Divergência",
                "detail": f"{len(divergent)} item(ns) em conciliação",
                "tone": "warning",
            }
        )
    if closure_pending > 0 and imp.current_status != CLOSED_STATUS:
        items.append(
            {
                "kind": "closure",
                "label": "Fechamento",
                "detail": f"{closure_pending} pendência(s) no checklist",
                "tone": "warning",
            }
        )
    return items


def get_dashboard_summary(db: Session) -> dict:
    all_imps = (
        db.query(ImportationOrder)
        .filter(ImportationOrder.is_active.is_(True))
        .order_by(ImportationOrder.created_at.desc())
        .all()
    )

    stage_counts = [0] * len(STAGE_LABELS)
    for imp in all_imps:
        stage_counts[stage_index_of(imp.current_status)] += 1

    open_imps = [i for i in all_imps if i.current_status != CLOSED_STATUS]
    open_ids = [i.id for i in open_imps]

    open_value_by_currency: dict[str, Decimal | None] = {}
    has_unknown_balance = False
    for imp in open_imps:
        summary = importation_financial_summary(db, imp)
        bal = summary["consolidated_balance"]
        cur = normalize_import_currency(imp.currency)
        if bal is None:
            has_unknown_balance = True
            open_value_by_currency.setdefault(cur, None)
            continue
        dec = Decimal(str(bal))
        if cur not in open_value_by_currency or open_value_by_currency[cur] is not None:
            prev = open_value_by_currency.get(cur)
            open_value_by_currency[cur] = (prev or Decimal("0")) + dec if prev is not None else dec

    if has_unknown_balance:
        for cur in list(open_value_by_currency.keys()):
            if open_value_by_currency[cur] is not None:
                # moedas com saldo parcial conhecido permanecem; as com null ficam null
                pass

    divergent_map = _divergent_by_importation(db, open_ids)
    divergence_importations_count = len(divergent_map)
    divergence_reconciliations_count = sum(len(v) for v in divergent_map.values())

    stocked_total = sum(_stock_by_importation(db, open_ids).values())

    review_queue_count = (
        db.query(ReviewQueueItem)
        .filter(ReviewQueueItem.status == ReviewQueueStatus.OPEN.value)
        .count()
    )

    closure_pending_count = sum(_count_closure_pending(db, imp) > 0 for imp in open_imps)

    shipments = _first_shipments(db, open_ids)
    eta_available = any(_format_eta(shipments.get(i)) for i in open_ids)

    due_summary = payments_due_summary(db, window_days=7)

    return {
        "open_importations_count": len(open_imps),
        "open_value_by_currency": {
            k: str(v) if v is not None else None for k, v in sorted(open_value_by_currency.items())
        },
        "divergence_importations_count": divergence_importations_count,
        "divergence_reconciliations_count": divergence_reconciliations_count,
        "stocked_units_total": stocked_total,
        "review_queue_count": review_queue_count,
        "stage_counts": [{"label": STAGE_LABELS[i], "count": stage_counts[i]} for i in range(len(STAGE_LABELS))],
        "closure_pending_importations_count": closure_pending_count,
        "payments_due_count": due_summary["due_count"],
        "payments_overdue_count": due_summary["overdue_count"],
        "payments_due_amount_by_currency": due_summary["due_amount_by_currency"],
        "payments_due_window_days": due_summary["window_days"],
        "data_availability": {
            "payments_due": due_summary["has_data"],
            "eta": eta_available,
            "monthly_stock_trend": False,
            "fx_rate": False,
        },
    }


def _pending_payments_for_importation(db: Session, imp: ImportationOrder, summary: dict) -> list[dict]:
    today = date.today()
    invoice_ids = [inv["invoice_id"] for inv in summary["invoices"]]
    planned_by_invoice: dict[int, list[Payment]] = defaultdict(list)
    if invoice_ids:
        for p in (
            db.query(Payment)
            .filter(
                Payment.invoice_id.in_(invoice_ids),
                Payment.is_active.is_(True),
                Payment.payment_date.is_(None),
                Payment.due_date.isnot(None),
                Payment.receipt_reference.is_(None),
                Payment.approved_without_receipt.is_(False),
            )
            .order_by(Payment.due_date.asc().nullslast())
            .all()
        ):
            planned_by_invoice[p.invoice_id].append(p)

    items: list[dict] = []
    for inv in summary["invoices"]:
        bal = inv.get("balance")
        if bal is None or Decimal(str(bal)) <= 0:
            continue
        planned = planned_by_invoice.get(inv["invoice_id"], [])
        if planned:
            for p in planned:
                due = p.due_date.isoformat() if p.due_date else None
                items.append(
                    {
                        "payment_id": p.id,
                        "invoice_id": inv["invoice_id"],
                        "invoice_number": inv["invoice_number"],
                        "invoice_type": inv["invoice_type"],
                        "balance": str(p.amount_foreign) if p.amount_foreign is not None else bal,
                        "currency": normalize_import_currency(p.currency_foreign or summary["currency"]),
                        "due_date": due,
                        "is_overdue": p.due_date is not None and p.due_date < today,
                    }
                )
        else:
            items.append(
                {
                    "payment_id": None,
                    "invoice_id": inv["invoice_id"],
                    "invoice_number": inv["invoice_number"],
                    "invoice_type": inv["invoice_type"],
                    "balance": bal,
                    "currency": normalize_import_currency(summary["currency"]),
                    "due_date": None,
                    "is_overdue": False,
                }
            )

    items.sort(key=lambda x: (x["due_date"] is None, x["due_date"] or ""))
    return items


def get_dashboard_importations(db: Session, *, list_limit: int = 100) -> dict:
    suppliers = {s.id: s.name for s in db.query(Supplier).filter(Supplier.is_active.is_(True)).all()}

    open_imps = (
        db.query(ImportationOrder)
        .filter(
            ImportationOrder.is_active.is_(True),
            ImportationOrder.current_status != CLOSED_STATUS,
        )
        .order_by(ImportationOrder.created_at.desc())
        .all()
    )
    open_ids = [i.id for i in open_imps]

    shipments = _first_shipments(db, open_ids)
    stock_map = _stock_by_importation(db, open_ids)
    lc_map = _lc_by_importation(db, open_ids)
    divergent_map = _divergent_by_importation(db, open_ids)

    official_customs_ids = {
        row[0]
        for row in db.query(CustomsDocument.importation_id)
        .filter(
            CustomsDocument.importation_id.in_(open_ids),
            CustomsDocument.status == CustomsDocumentStatus.OFFICIAL.value,
            CustomsDocument.is_valid.is_(True),
        )
        .distinct()
        .all()
    }

    items: list[dict] = []
    for imp in open_imps[:list_limit]:
        summary = importation_financial_summary(db, imp)
        divergent = divergent_map.get(imp.id, [])
        shipment = shipments.get(imp.id)
        modal = shipment.modal if shipment else None
        lc = lc_map.get(imp.id)
        lc_actual = str(lc.total_cost) if lc and lc.total_cost is not None else None
        lc_estimated = str(imp.estimated_total) if imp.estimated_total is not None else None
        closure_pending = _count_closure_pending(db, imp)
        pending_payments = _pending_payments_for_importation(db, imp, summary)

        items.append(
            {
                "id": imp.id,
                "po_number": imp.po_number,
                "status": imp.current_status,
                "supplier_name": suppliers.get(imp.supplier_id, "—"),
                "currency": normalize_import_currency(imp.currency),
                "created_at": imp.created_at.isoformat() if isinstance(imp.created_at, datetime) else str(imp.created_at),
                "modal": modal,
                "stage_index": stage_index_of(imp.current_status),
                "in_transit": imp.current_status in IN_TRANSIT_STATUSES,
                "open_value": summary["consolidated_balance"],
                "stocked_qty": stock_map.get(imp.id, 0),
                "has_divergence": len(divergent) > 0,
                "divergence_count": len(divergent),
                "lc_estimated": lc_estimated,
                "lc_actual": lc_actual,
                "eta": _format_eta(shipment),
                "closure_pending_count": closure_pending,
                "action_items": _build_action_items(
                    db,
                    imp,
                    has_official_customs=imp.id in official_customs_ids,
                    divergent=divergent,
                    closure_pending=closure_pending,
                ),
                "pending_payments": pending_payments,
            }
        )

    return {"items": items, "total_open": len(open_imps)}
