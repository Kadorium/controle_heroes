"""Agregação da central da ordem e fila operacional — Fase 6."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import DEFAULT_IMPORT_CURRENCY
from app.core.currency import normalize_import_currency

from app.models import (
    BrazilCurrentAccount,
    Credit,
    CustomsDocument,
    Discount,
    HeroesDispatchPendingItem,
    HeroesLegacySheetSummary,
    ImportationItem,
    ImportationOrder,
    Invoice,
    InvoiceItem,
    Nationalization,
    Payment,
    Product,
    Shipment,
    StockEntry,
    Supplier,
)
from app.services.dashboard import (
    CLOSED_STATUS,
    _build_action_items,
    _count_closure_pending,
    _divergent_by_importation,
)
from app.services.finance import (
    _d,
    _payment_is_settled,
    invoice_balance,
    invoice_discount_total,
    invoice_has_settled_payments,
    invoice_paid_total,
)
from app.services.nationalization import quantity_chain
from app.services.order_status_rail import build_status_rail


def _invoice_open_deadlines(invoices: list[dict], today: date) -> dict:
    """Prazos a partir de faturas em aberto (saldo > 0), não só pagamentos planejados."""
    open_invoices: list[dict] = []
    dated_candidates: list[tuple[date, dict]] = []
    overdue_count = 0
    overdue_amount = Decimal("0")

    for inv in invoices:
        balance_raw = inv.get("balance")
        if balance_raw is None:
            continue
        balance = _d(balance_raw)
        if balance <= Decimal("0"):
            continue

        open_invoices.append(inv)
        due = inv.get("payment_due_date") or inv.get("invoice_date")
        if due is None:
            continue
        if isinstance(due, str):
            due = date.fromisoformat(due)

        dated_candidates.append((due, inv))
        if due < today:
            overdue_count += 1
            overdue_amount += balance

    if not open_invoices:
        return {
            "next_due_date": None,
            "overdue_count": 0,
            "overdue_amount_foreign": None,
            "next_open_invoice_number": None,
            "next_open_invoice_balance": None,
        }

    if dated_candidates:
        next_due, next_inv = min(dated_candidates, key=lambda row: row[0])
    else:
        next_due = None
        next_inv = open_invoices[0]

    return {
        "next_due_date": next_due,
        "overdue_count": overdue_count,
        "overdue_amount_foreign": str(overdue_amount) if overdue_amount > Decimal("0") else None,
        "next_open_invoice_number": next_inv.get("invoice_number"),
        "next_open_invoice_balance": str(next_inv.get("balance")) if next_inv.get("balance") is not None else None,
    }


def _financial_totals_by_currency(db: Session, importation: ImportationOrder) -> dict:
    """Totais financeiros por moeda — nunca soma moedas distintas em um único campo."""
    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == importation.id, Invoice.is_active.is_(True))
        .all()
    )
    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "invoiced": Decimal("0"),
            "paid": Decimal("0"),
            "discounts": Decimal("0"),
            "has_null_amount": False,
        }
    )

    for inv in invoices:
        cur = normalize_import_currency(inv.currency or importation.currency)
        bucket = buckets[cur]
        if inv.amount is not None:
            bucket["invoiced"] += inv.amount
        else:
            bucket["has_null_amount"] = True
        bucket["paid"] += invoice_paid_total(db, inv)
        bucket["discounts"] += invoice_discount_total(db, inv)

    def _balance(bucket: dict) -> str | None:
        if bucket["has_null_amount"]:
            return None
        return str(bucket["invoiced"] - bucket["discounts"] - bucket["paid"])

    totals_by_currency = {}
    for cur, b in buckets.items():
        invs_for_cur = [
            inv
            for inv in invoices
            if normalize_import_currency(inv.currency or importation.currency) == cur
        ]
        has_settled = any(invoice_has_settled_payments(db, inv) for inv in invs_for_cur)
        totals_by_currency[cur] = {
            "total_invoiced": str(b["invoiced"]) if not b["has_null_amount"] else None,
            "total_paid": str(b["paid"]) if has_settled else None,
            "total_discounts": str(b["discounts"]),
            "consolidated_balance": _balance(b),
        }

    primary = normalize_import_currency(importation.currency)
    multi = len(buckets) > 1

    if multi:
        return {
            "currency": primary,
            "total_invoiced": None,
            "total_paid": None,
            "consolidated_balance": None,
            "totals_by_currency": totals_by_currency,
        }

    if not buckets:
        return {
            "currency": primary,
            "total_invoiced": None,
            "total_paid": None,
            "consolidated_balance": None,
            "totals_by_currency": None,
        }

    only = totals_by_currency[next(iter(buckets))]
    return {
        "currency": next(iter(buckets)),
        "total_invoiced": only["total_invoiced"],
        "total_paid": only["total_paid"],
        "consolidated_balance": only["consolidated_balance"],
        "totals_by_currency": None,
    }


def _compute_to_dispatch(chain: list[dict]) -> int | None:
    if not chain:
        return None
    total = 0
    for row in chain:
        ordered = row.get("quantity_ordered")
        shipped = row.get("quantity_shipped")
        if ordered is None:
            continue
        total += max(0, ordered - (shipped or 0))
    return total


def _invoiced_qty_by_item(db: Session, importation_id: int) -> dict[int, int]:
    rows = (
        db.query(InvoiceItem.importation_item_id, InvoiceItem.quantity)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .filter(
            Invoice.importation_id == importation_id,
            Invoice.is_active.is_(True),
            InvoiceItem.is_active.is_(True),
            InvoiceItem.importation_item_id.isnot(None),
        )
        .all()
    )
    totals: dict[int, int] = defaultdict(int)
    for item_id, qty in rows:
        if item_id is not None and qty is not None:
            totals[item_id] += qty
    return dict(totals)


def _build_legacy_summary(db: Session, importation_id: int) -> dict | None:
    row = (
        db.query(HeroesLegacySheetSummary)
        .filter(
            HeroesLegacySheetSummary.importation_id == importation_id,
            HeroesLegacySheetSummary.is_active.is_(True),
        )
        .order_by(HeroesLegacySheetSummary.created_at.desc())
        .first()
    )
    if not row or row.versato_amount is None:
        return None
    return {
        "versato_amount": str(row.versato_amount),
        "versato_currency": row.versato_currency,
        "versato_source": f"{row.sheet_name} · {row.versato_source_cell or row.versato_source_row or 'topo'}",
        "versato_confidence": row.versato_confidence,
        "sheet_name": row.sheet_name,
        "source": "planilha Heroes",
    }


def _dispatch_by_product(db: Session, importation_id: int) -> dict[int, HeroesDispatchPendingItem]:
    rows = (
        db.query(HeroesDispatchPendingItem)
        .filter(
            HeroesDispatchPendingItem.importation_id == importation_id,
            HeroesDispatchPendingItem.is_active.is_(True),
        )
        .all()
    )
    by_product: dict[int, HeroesDispatchPendingItem] = {}
    for r in rows:
        if r.product_id:
            by_product[r.product_id] = r
    return by_product


def _build_dispatch_pending_list(db: Session, importation_id: int) -> list[dict]:
    rows = (
        db.query(HeroesDispatchPendingItem)
        .filter(
            HeroesDispatchPendingItem.importation_id == importation_id,
            HeroesDispatchPendingItem.is_active.is_(True),
        )
        .order_by(HeroesDispatchPendingItem.source_row)
        .all()
    )
    return [
        {
            "id": r.id,
            "product_name_raw": r.product_name_raw,
            "product_id": r.product_id,
            "product_category_suggested": r.product_category_suggested,
            "quantity_to_dispatch": r.quantity_to_dispatch,
            "price_listino": str(r.price_listino) if r.price_listino is not None else None,
            "price_fattura": str(r.price_fattura) if r.price_fattura is not None else None,
            "discount_unit": str(r.discount_unit) if r.discount_unit is not None else None,
            "acconto_amount": str(r.acconto_amount) if r.acconto_amount is not None else None,
            "credit_remaining": str(r.credit_remaining) if r.credit_remaining is not None else None,
            "currency": r.currency,
            "source_sheet": r.source_sheet,
            "source_row": r.source_row,
            "needs_review": r.needs_review,
            "heroes_source": True,
        }
        for r in rows
    ]


def _build_models(db: Session, importation_id: int) -> list[dict]:
    chain = quantity_chain(db, importation_id)
    invoiced_map = _invoiced_qty_by_item(db, importation_id)
    items = (
        db.query(ImportationItem)
        .options(joinedload(ImportationItem.product))
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    item_by_id = {i.id: i for i in items}
    dispatch_map = _dispatch_by_product(db, importation_id)
    models: list[dict] = []

    for row in chain:
        item_id = row["importation_item_id"]
        item = item_by_id.get(item_id)
        product: Product | None = item.product if item else None
        label = None
        if product:
            label = product.sku_code
        elif item and item.description:
            label = item.description
        elif item and item.supplier_sku:
            label = item.supplier_sku

        da = dispatch_map.get(item.product_id) if item and item.product_id else None
        dispatch_qty = da.quantity_to_dispatch if da else None
        ordered = row.get("quantity_ordered")
        shipped = row.get("quantity_shipped")
        if ordered is not None and shipped is not None:
            to_dispatch_val = max(0, ordered - shipped)
        elif ordered is not None:
            to_dispatch_val = ordered
        else:
            to_dispatch_val = None
        if dispatch_qty is not None and to_dispatch_val is not None and dispatch_qty != to_dispatch_val:
            to_dispatch_val = dispatch_qty
        elif dispatch_qty is not None and to_dispatch_val is None:
            to_dispatch_val = dispatch_qty

        models.append(
            {
                "importation_item_id": item_id,
                "product_id": item.product_id if item else None,
                "supplier_sku": item.supplier_sku if item else None,
                "description": item.description if item else None,
                "product_sku": product.sku_code if product else None,
                "product_category": product.category if product else None,
                "model_label": label,
                "quantity_ordered": ordered,
                "quantity_shipped": shipped,
                "quantity_nationalized": row.get("quantity_nationalized"),
                "quantity_stocked": row.get("quantity_stocked"),
                "quantity_invoiced": invoiced_map.get(item_id),
                "to_dispatch": to_dispatch_val,
                "price_listino": str(da.price_listino) if da and da.price_listino is not None else None,
                "price_fattura": str(da.price_fattura) if da and da.price_fattura is not None else None,
                "discount_unit": str(da.discount_unit) if da and da.discount_unit is not None else None,
                "acconto_amount": str(da.acconto_amount) if da and da.acconto_amount is not None else None,
                "credit_remaining": str(da.credit_remaining) if da and da.credit_remaining is not None else None,
                "heroes_source": da is not None,
                "dispatch_needs_review": da.needs_review if da else False,
            }
        )
    return models


def _build_invoices(db: Session, importation_id: int) -> list[dict]:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True))
        .order_by(Invoice.created_at)
        .all()
    )
    item_ids = {
        ii.importation_item_id
        for inv in invoices
        for ii in inv.items
        if ii.is_active and ii.importation_item_id
    }
    product_ids = {
        ii.product_id for inv in invoices for ii in inv.items if ii.is_active and ii.product_id
    }
    import_items = {
        i.id: i
        for i in db.query(ImportationItem)
        .options(joinedload(ImportationItem.product))
        .filter(ImportationItem.id.in_(item_ids))
        .all()
    } if item_ids else {}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()} if product_ids else {}

    inv_ids = [i.id for i in invoices]
    payment_due_by_inv: dict[int, date] = {}
    if inv_ids:
        for p in (
            db.query(Payment)
            .filter(Payment.invoice_id.in_(inv_ids), Payment.is_active.is_(True))
            .all()
        ):
            if p.due_date is not None and not _payment_is_settled(p):
                prev = payment_due_by_inv.get(p.invoice_id)
                if prev is None or p.due_date < prev:
                    payment_due_by_inv[p.invoice_id] = p.due_date

    result = []
    for inv in invoices:
        inv_items = []
        for ii in inv.items:
            if not ii.is_active:
                continue
            imp_item = import_items.get(ii.importation_item_id) if ii.importation_item_id else None
            product = products.get(ii.product_id) if ii.product_id else None
            if not product and imp_item and imp_item.product:
                product = imp_item.product
            description = imp_item.description if imp_item else None
            inv_items.append(
                {
                    "id": ii.id,
                    "importation_item_id": ii.importation_item_id,
                    "product_id": ii.product_id,
                    "product_sku": product.sku_code if product else None,
                    "description": description,
                    "quantity": ii.quantity,
                    "unit_price": ii.unit_price,
                    "amount": ii.amount,
                }
            )
        result.append(
            {
                "id": inv.id,
                "invoice_type": inv.invoice_type,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "payment_due_date": payment_due_by_inv.get(inv.id),
                "amount": inv.amount,
                "currency": normalize_import_currency(inv.currency),
                "discount_amount": inv.discount_amount,
                "balance": invoice_balance(db, inv),
                "paid_total": invoice_paid_total(db, inv),
                "items": inv_items,
            }
        )
    return result


def _build_payments(db: Session, importation_id: int) -> tuple[list[dict], list[dict]]:
    payments = (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(
            Invoice.importation_id == importation_id,
            Invoice.is_active.is_(True),
            Payment.is_active.is_(True),
        )
        .order_by(Payment.created_at)
        .all()
    )
    invoice_map = {
        inv.id: inv
        for inv in db.query(Invoice).filter(Invoice.importation_id == importation_id).all()
    }
    planned: list[dict] = []
    settled: list[dict] = []

    for p in payments:
        inv = invoice_map.get(p.invoice_id)
        payload = {
            "id": p.id,
            "invoice_id": p.invoice_id,
            "payment_type": p.payment_type,
            "payment_date": p.payment_date,
            "due_date": p.due_date,
            "amount_foreign": p.amount_foreign,
            "amount_local": p.amount_local,
            "exchange_rate": p.exchange_rate,
            "currency_foreign": normalize_import_currency(p.currency_foreign) if p.currency_foreign else None,
            "receipt_reference": p.receipt_reference,
            "exchange_contract_number": p.exchange_contract_number,
            "settlement_date": p.settlement_date,
            "bank_name": p.bank_name,
            "approved_without_receipt": p.approved_without_receipt,
            "is_active": p.is_active,
            "is_settled": _payment_is_settled(p),
            "invoice_number": inv.invoice_number if inv else None,
            "invoice_type": inv.invoice_type if inv else None,
        }
        if _payment_is_settled(p):
            settled.append(payload)
        else:
            planned.append(payload)
    return planned, settled


def _pending_actions(db: Session, imp: ImportationOrder) -> list[dict]:
    from app.models import CustomsDocument
    from app.core.enums import CustomsDocumentStatus

    divergent = _divergent_by_importation(db, [imp.id]).get(imp.id, [])
    official = (
        db.query(CustomsDocument)
        .filter(
            CustomsDocument.importation_id == imp.id,
            CustomsDocument.status == CustomsDocumentStatus.OFFICIAL.value,
            CustomsDocument.is_valid.is_(True),
        )
        .count()
        > 0
    )
    closure_pending = _count_closure_pending(db, imp)
    return _build_action_items(
        db,
        imp,
        has_official_customs=official,
        divergent=divergent,
        closure_pending=closure_pending,
    )


def _ship_date(s: Shipment, field: str) -> date | None:
    if field == "etd":
        return s.etd_actual or s.etd_planned
    return s.eta_actual or s.eta_planned


def _next_ship_dates(shipments: list[Shipment]) -> tuple[date | None, date | None]:
    active = [s for s in shipments if s.is_active]
    etds = [d for s in active if (d := _ship_date(s, "etd"))]
    etas = [d for s in active if (d := _ship_date(s, "eta"))]
    return (min(etds) if etds else None, min(etas) if etas else None)


def _active_modal(shipments: list[Shipment]) -> str | None:
    if not shipments:
        return None
    for s in shipments:
        if s.is_active and s.status in ("IN_TRANSIT", "SHIPPED"):
            return s.modal
    active = [s for s in shipments if s.is_active]
    return active[-1].modal if active else None


def _open_balance_brl_equivalent(db: Session, importation_id: int) -> str | None:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True))
        .all()
    )
    total = Decimal("0")
    has_open_without_rate = False
    for inv in invoices:
        bal = invoice_balance(db, inv)
        if bal is None or bal <= Decimal("0"):
            continue
        if inv.expected_exchange_rate is None:
            has_open_without_rate = True
            continue
        total += bal * inv.expected_exchange_rate
    if has_open_without_rate and total == Decimal("0"):
        return None
    return str(total) if total > Decimal("0") else ("0" if not has_open_without_rate else None)


def _build_finance_operational(
    db: Session,
    imp: ImportationOrder,
    financial: dict,
    *,
    legacy_versato: Decimal | None = None,
    mark_rate: Decimal | None = None,
) -> dict[str, str | None]:
    """Totais operacionais: ordem, faturado, liquidado e saldos (EUR + BRL)."""
    from app.services.fx_pnl import _get_provision_rate

    opening = _get_provision_rate(db, imp.id)
    brl_rate = mark_rate or opening
    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id == imp.id, Invoice.is_active.is_(True))
        .all()
    )

    invoiced_eur = Decimal("0")
    invoiced_brl = Decimal("0")
    has_invoiced_eur = False
    has_invoiced_brl = False
    open_eur_sum = Decimal("0")
    has_open_eur = False
    has_null_invoice_amount = False

    for inv in invoices:
        if inv.amount is not None:
            invoiced_eur += inv.amount
            has_invoiced_eur = True
            rate = inv.expected_exchange_rate or opening
            if rate is not None:
                invoiced_brl += inv.amount * rate
                has_invoiced_brl = True
        else:
            has_null_invoice_amount = True
        bal = invoice_balance(db, inv)
        if bal is not None:
            open_eur_sum += bal
            has_open_eur = True

    open_eur: Decimal | None = None
    if financial.get("consolidated_balance") is not None:
        open_eur = Decimal(financial["consolidated_balance"])
    elif has_open_eur and not has_null_invoice_amount:
        open_eur = open_eur_sum
    elif has_open_eur:
        open_eur = open_eur_sum

    settled_eur = Decimal("0")
    has_settled_eur = False
    for inv in invoices:
        if invoice_has_settled_payments(db, inv):
            has_settled_eur = True
        settled_eur += invoice_paid_total(db, inv)
    if not has_settled_eur:
        settled_eur = None

    order_total_eur: Decimal | None = imp.estimated_total
    if order_total_eur is None and legacy_versato is not None:
        order_total_eur = legacy_versato
    if order_total_eur is None and has_invoiced_eur:
        order_total_eur = invoiced_eur + open_eur_sum
    if order_total_eur is None and settled_eur is not None:
        open_part = open_eur if open_eur is not None else Decimal("0")
        order_total_eur = settled_eur + open_part

    remaining_eur: Decimal | None = None
    if order_total_eur is not None and has_invoiced_eur:
        remaining_eur = max(Decimal("0"), order_total_eur - invoiced_eur)

    settled_brl = Decimal("0")
    has_settled_brl = False
    for p in (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(
            Invoice.importation_id == imp.id,
            Invoice.is_active.is_(True),
            Payment.is_active.is_(True),
        )
        .all()
    ):
        if not _payment_is_settled(p) or p.amount_foreign is None:
            continue
        if p.amount_local is not None:
            settled_brl += p.amount_local
            has_settled_brl = True
            continue
        pay_cur = normalize_import_currency(p.currency_foreign or imp.currency)
        if pay_cur == "BRL":
            settled_brl += p.amount_foreign
            has_settled_brl = True
        elif p.exchange_rate is not None and p.exchange_rate > 0:
            settled_brl += p.amount_foreign * p.exchange_rate
            has_settled_brl = True

    order_total_brl: Decimal | None = None
    if order_total_eur is not None and brl_rate is not None:
        order_total_brl = order_total_eur * brl_rate

    remaining_brl: Decimal | None = None
    if remaining_eur is not None and brl_rate is not None:
        remaining_brl = remaining_eur * brl_rate

    open_brl = _open_balance_brl_equivalent(db, imp.id)
    if open_brl is None and open_eur is not None and brl_rate is not None:
        open_brl = str(open_eur * brl_rate)

    return {
        "order_total_eur": str(order_total_eur) if order_total_eur is not None else None,
        "order_total_brl": str(order_total_brl) if order_total_brl is not None else None,
        "invoiced_eur": str(invoiced_eur) if has_invoiced_eur else None,
        "invoiced_brl": str(invoiced_brl) if has_invoiced_brl else None,
        "settled_eur": str(settled_eur) if settled_eur is not None else None,
        "settled_brl": str(settled_brl) if has_settled_brl else None,
        "remaining_to_invoice_eur": str(remaining_eur) if remaining_eur is not None else None,
        "remaining_to_invoice_brl": str(remaining_brl) if remaining_brl is not None else None,
        "balance_to_settle_eur": str(open_eur) if open_eur is not None else None,
        "balance_to_settle_brl": open_brl,
        "opening_exchange_rate": str(opening) if opening is not None else None,
    }


def _build_operational_header(
    db: Session,
    imp: ImportationOrder,
    *,
    financial: dict,
    invoices: list[dict],
    shipments: list[Shipment],
    chain: list[dict],
    credits: list[Credit],
    pending_actions_count: int,
    legacy_versato: Decimal | None = None,
) -> dict:
    today = date.today()
    counts = _invoice_counts_for_queue(db, [imp])
    invoices_count, invoices_settled_count = counts.get(imp.id, (0, 0))

    deadline_info = _invoice_open_deadlines(invoices, today)

    next_etd, next_eta = _next_ship_dates(shipments)
    qty_ordered = sum((c.get("quantity_ordered") or 0) for c in chain) if chain else None
    primary = normalize_import_currency(imp.currency)
    credit_avail = sum(
        _d(c.amount_available)
        for c in credits
        if normalize_import_currency(c.currency) == primary
    )

    from app.services.fx_pnl import compute_fx_pnl
    from app.services.fx_reference import fetch_fx_reference

    mark_rate = None
    try:
        ref = fetch_fx_reference()
        if ref.get("rate") is not None:
            mark_rate = Decimal(str(ref["rate"]))
    except Exception:
        mark_rate = None
    fx_pnl = compute_fx_pnl(db, imp.id, mark_rate=mark_rate)
    finance_ops = _build_finance_operational(
        db,
        imp,
        financial,
        legacy_versato=legacy_versato,
        mark_rate=mark_rate,
    )

    return {
        "invoices_count": invoices_count,
        "invoices_settled_count": invoices_settled_count,
        "totals_by_currency": financial.get("totals_by_currency"),
        "total_invoiced": financial.get("total_invoiced"),
        "total_paid": financial.get("total_paid"),
        "open_balance": financial.get("consolidated_balance"),
        "open_balance_brl_equivalent": _open_balance_brl_equivalent(db, imp.id),
        **deadline_info,
        "next_etd": next_etd,
        "next_eta": next_eta,
        "active_modal": _active_modal(shipments),
        "to_dispatch": _compute_to_dispatch(chain),
        "quantity_ordered": qty_ordered,
        "supplier_credit_available": str(credit_avail) if credit_avail > Decimal("0") else None,
        "pending_actions_count": pending_actions_count,
        "fx_pnl": fx_pnl,
        **finance_ops,
    }


def build_order_central(db: Session, importation_id: int) -> dict:
    imp = (
        db.query(ImportationOrder)
        .filter(ImportationOrder.id == importation_id)
        .first()
    )
    if not imp:
        raise ValueError("Importação não encontrada")

    supplier = db.query(Supplier).filter(Supplier.id == imp.supplier_id).first()
    chain = quantity_chain(db, importation_id)
    financial = _financial_totals_by_currency(db, imp)
    planned, settled = _build_payments(db, importation_id)
    invoices = _build_invoices(db, importation_id)
    shipments = (
        db.query(Shipment)
        .filter(Shipment.importation_id == importation_id, Shipment.is_active.is_(True))
        .order_by(Shipment.created_at)
        .all()
    )
    discounts = (
        db.query(Discount)
        .join(Invoice, Discount.invoice_id == Invoice.id)
        .filter(Invoice.importation_id == importation_id, Discount.is_active.is_(True))
        .all()
    )
    credits = (
        db.query(Credit)
        .filter(Credit.supplier_id == imp.supplier_id, Credit.is_active.is_(True))
        .all()
    )
    brazil_accounts = (
        db.query(BrazilCurrentAccount)
        .filter(BrazilCurrentAccount.supplier_id == imp.supplier_id, BrazilCurrentAccount.is_active.is_(True))
        .all()
    )

    has_invoices = len(invoices) > 0
    has_payments = len(settled) > 0
    has_shipments = len(shipments) > 0
    shipment_in_transit = has_shipments and any(
        s.status in ("IN_TRANSIT", "SHIPPED", "DELIVERED") for s in shipments
    )
    has_customs = (
        db.query(CustomsDocument)
        .filter(
            CustomsDocument.importation_id == importation_id,
            CustomsDocument.is_active.is_(True),
            CustomsDocument.approved_at.isnot(None),
        )
        .count()
        > 0
    )
    has_stock = (
        db.query(StockEntry)
        .join(Nationalization, StockEntry.nationalization_id == Nationalization.id)
        .filter(Nationalization.importation_id == importation_id)
        .count()
        > 0
    )
    is_closed = imp.current_status == "CLOSED"
    pending = _pending_actions(db, imp)
    legacy = _build_legacy_summary(db, importation_id)
    legacy_versato = Decimal(legacy["versato_amount"]) if legacy and legacy.get("versato_amount") else None
    operational_header = _build_operational_header(
        db,
        imp,
        financial=financial,
        invoices=invoices,
        shipments=shipments,
        chain=chain,
        credits=credits,
        pending_actions_count=len(pending),
        legacy_versato=legacy_versato,
    )
    rail_context = {
        "invoices_count": operational_header["invoices_count"],
        "invoices_settled_count": operational_header["invoices_settled_count"],
        "total_paid": financial.get("total_paid"),
        "currency": financial.get("currency"),
        "next_eta": operational_header["next_eta"],
        "to_dispatch": operational_header["to_dispatch"],
        "quantity_ordered": operational_header["quantity_ordered"],
    }
    status_rail = build_status_rail(
        imp.current_status,
        has_invoices=has_invoices,
        has_payments=has_payments,
        has_shipments=has_shipments,
        shipment_in_transit=shipment_in_transit,
        has_customs=has_customs,
        has_stock=has_stock,
        is_closed=is_closed,
        rail_context=rail_context,
    )
    dispatch_pending = _build_dispatch_pending_list(db, importation_id)
    for alert in status_rail.get("alerts") or []:
        pending.append({"kind": "status_rail", "label": alert, "detail": None, "tone": "warning"})

    return {
        "order": imp,
        "supplier_name": supplier.name if supplier else None,
        "legacy_sheet_summary": legacy,
        "dispatch_pending": dispatch_pending,
        "status_rail": status_rail,
        "operational_header": operational_header,
        "kpis": {
            **financial,
            "to_dispatch": _compute_to_dispatch(chain),
            "versato_heroes": legacy.get("versato_amount") if legacy else None,
            "versato_heroes_currency": legacy.get("versato_currency") if legacy else None,
        },
        "invoices": invoices,
        "models": _build_models(db, importation_id),
        "payments_planned": planned,
        "payments_settled": settled,
        "discounts": discounts,
        "supplier_credits": credits,
        "brazil_accounts": brazil_accounts,
        "shipments": shipments,
        "pending_actions": pending,
    }


def _invoice_counts_for_queue(
    db: Session, imps: list[ImportationOrder]
) -> dict[int, tuple[int, int]]:
    """(total de faturas, faturas quitadas) por ordem — em lote, sem N+1."""
    imp_ids = [i.id for i in imps]
    if not imp_ids:
        return {}
    invoices = (
        db.query(
            Invoice.id,
            Invoice.importation_id,
            Invoice.amount,
            Invoice.discount_amount,
        )
        .filter(Invoice.importation_id.in_(imp_ids), Invoice.is_active.is_(True))
        .all()
    )
    inv_ids = [r.id for r in invoices]

    disc_map: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    paid_map: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    if inv_ids:
        for inv_id, total in (
            db.query(Discount.invoice_id, func.coalesce(func.sum(Discount.amount), 0))
            .filter(Discount.invoice_id.in_(inv_ids), Discount.is_active.is_(True))
            .group_by(Discount.invoice_id)
            .all()
        ):
            disc_map[inv_id] = _d(total)

        settled_cond = or_(
            Payment.payment_date.isnot(None),
            Payment.approved_without_receipt.is_(True),
            func.length(func.coalesce(Payment.receipt_reference, "")) > 0,
        )
        for inv_id, total in (
            db.query(Payment.invoice_id, func.coalesce(func.sum(Payment.amount_foreign), 0))
            .filter(
                Payment.invoice_id.in_(inv_ids),
                Payment.is_active.is_(True),
                settled_cond,
            )
            .group_by(Payment.invoice_id)
            .all()
        ):
            paid_map[inv_id] = _d(total)

    counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for r in invoices:
        bucket = counts[r.importation_id]
        bucket[0] += 1
        if r.amount is not None:
            balance = _d(r.amount) - disc_map[r.id] - paid_map[r.id]
            if balance == Decimal("0"):
                bucket[1] += 1
    return {iid: (counts[iid][0], counts[iid][1]) for iid in imp_ids}


def _batch_financial_for_queue(db: Session, imps: list[ImportationOrder]) -> dict[int, dict]:
    """Totais financeiros em lote — evita N+1 na fila operacional."""
    imp_ids = [i.id for i in imps]
    if not imp_ids:
        return {}

    invoices = (
        db.query(Invoice)
        .filter(Invoice.importation_id.in_(imp_ids), Invoice.is_active.is_(True))
        .all()
    )
    inv_ids = [i.id for i in invoices]
    inv_by_imp: dict[int, list[Invoice]] = defaultdict(list)
    for inv in invoices:
        inv_by_imp[inv.importation_id].append(inv)

    payments_by_inv: dict[int, list[Payment]] = defaultdict(list)
    if inv_ids:
        for p in db.query(Payment).filter(Payment.invoice_id.in_(inv_ids), Payment.is_active.is_(True)).all():
            payments_by_inv[p.invoice_id].append(p)

    discount_extra_by_inv: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    if inv_ids:
        for d in db.query(Discount).filter(Discount.invoice_id.in_(inv_ids), Discount.is_active.is_(True)).all():
            discount_extra_by_inv[d.invoice_id] += _d(d.amount)

    def _paid(inv: Invoice) -> Decimal:
        return sum(_d(p.amount_foreign) for p in payments_by_inv.get(inv.id, []) if _payment_is_settled(p))

    def _discount(inv: Invoice) -> Decimal:
        return _d(inv.discount_amount) + discount_extra_by_inv.get(inv.id, Decimal("0"))

    def _balance(bucket: dict) -> str | None:
        if bucket["has_null_amount"]:
            return None
        return str(bucket["invoiced"] - bucket["discounts"] - bucket["paid"])

    out: dict[int, dict] = {}
    for imp in imps:
        imp_invs = inv_by_imp.get(imp.id, [])
        buckets: dict[str, dict] = defaultdict(
            lambda: {
                "invoiced": Decimal("0"),
                "paid": Decimal("0"),
                "discounts": Decimal("0"),
                "has_null_amount": False,
            }
        )
        for inv in imp_invs:
            cur = normalize_import_currency(inv.currency or imp.currency)
            bucket = buckets[cur]
            if inv.amount is not None:
                bucket["invoiced"] += inv.amount
            else:
                bucket["has_null_amount"] = True
            bucket["paid"] += _paid(inv)
            bucket["discounts"] += _discount(inv)

        primary = normalize_import_currency(imp.currency)
        multi = len(buckets) > 1

        if multi:
            totals_by_currency = {
                cur: {
                    "total_invoiced": str(b["invoiced"]) if not b["has_null_amount"] else None,
                    "total_paid": str(b["paid"]),
                    "total_discounts": str(b["discounts"]),
                    "consolidated_balance": _balance(b),
                }
                for cur, b in buckets.items()
            }
            out[imp.id] = {
                "currency": primary,
                "total_invoiced": None,
                "total_paid": None,
                "consolidated_balance": None,
                "totals_by_currency": totals_by_currency,
            }
        elif not buckets:
            out[imp.id] = {
                "currency": primary,
                "total_invoiced": None,
                "total_paid": None,
                "consolidated_balance": None,
                "totals_by_currency": None,
            }
        else:
            cur = next(iter(buckets))
            b = buckets[cur]
            out[imp.id] = {
                "currency": cur,
                "total_invoiced": str(b["invoiced"]) if not b["has_null_amount"] else None,
                "total_paid": str(b["paid"]),
                "consolidated_balance": _balance(b),
                "totals_by_currency": None,
            }
    return out


def build_order_queue(db: Session, limit: int = 100) -> dict:
    imps = (
        db.query(ImportationOrder)
        .filter(
            ImportationOrder.is_active.is_(True),
            ImportationOrder.current_status != CLOSED_STATUS,
        )
        .order_by(ImportationOrder.updated_at.desc())
        .limit(limit)
        .all()
    )
    suppliers = {s.id: s.name for s in db.query(Supplier).filter(Supplier.is_active.is_(True)).all()}
    total = (
        db.query(ImportationOrder)
        .filter(
            ImportationOrder.is_active.is_(True),
            ImportationOrder.current_status != CLOSED_STATUS,
        )
        .count()
    )

    items: list[dict] = []
    financials = _batch_financial_for_queue(db, imps)
    invoice_counts = _invoice_counts_for_queue(db, imps)
    today = date.today()
    for imp in imps:
        financial = financials.get(imp.id) or _financial_totals_by_currency(db, imp)
        chain = quantity_chain(db, imp.id)
        actions = _pending_actions(db, imp)
        invoiced_map = _invoiced_qty_by_item(db, imp.id)

        qty_ordered = sum((c.get("quantity_ordered") or 0) for c in chain) if chain else None
        shipped_vals = [c.get("quantity_shipped") for c in chain] if chain else []
        qty_shipped = (
            None
            if not shipped_vals or all(v is None for v in shipped_vals)
            else sum(v or 0 for v in shipped_vals)
        )
        qty_invoiced = sum(invoiced_map.values()) if invoiced_map else None
        products_count = len(chain)

        invoices_count, invoices_settled_count = invoice_counts.get(imp.id, (0, 0))

        built_invoices = _build_invoices(db, imp.id)
        deadline_info = _invoice_open_deadlines(built_invoices, today)

        docs_pending = sum(1 for a in actions if a.get("kind") == "customs")

        items.append(
            {
                "id": imp.id,
                "po_number": imp.po_number,
                "supplier_id": imp.supplier_id,
                "supplier_name": suppliers.get(imp.supplier_id),
                "status": imp.current_status,
                "currency": normalize_import_currency(imp.currency),
                "total_invoiced": financial["total_invoiced"],
                "total_paid": financial["total_paid"],
                "consolidated_balance": financial["consolidated_balance"],
                "totals_by_currency": financial.get("totals_by_currency"),
                "to_dispatch": _compute_to_dispatch(chain),
                "qty_ordered": qty_ordered,
                "qty_invoiced": qty_invoiced,
                "qty_shipped": qty_shipped,
                "products_count": products_count,
                "invoices_count": invoices_count,
                "invoices_settled_count": invoices_settled_count,
                "docs_pending_count": docs_pending,
                **deadline_info,
                "priority": imp.priority,
                "responsible": imp.responsible,
                "internal_forecast_date": imp.internal_forecast_date,
                "brazil_operational_notes": imp.brazil_operational_notes,
                "pending_actions_count": len(actions),
                "updated_at": imp.updated_at,
                "created_at": imp.created_at,
            }
        )

    return {"items": items, "total": total}
