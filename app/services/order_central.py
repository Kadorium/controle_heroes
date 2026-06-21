"""Agregação da central da ordem e fila operacional — Fase 6."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.config import DEFAULT_IMPORT_CURRENCY

from app.models import (
    BrazilCurrentAccount,
    Credit,
    Discount,
    ImportationItem,
    ImportationOrder,
    Invoice,
    InvoiceItem,
    Payment,
    Product,
    Shipment,
    Supplier,
)
from app.services.dashboard import (
    CLOSED_STATUS,
    _build_action_items,
    _count_closure_pending,
    _divergent_by_importation,
)
from app.services.finance import (
    _payment_is_settled,
    invoice_balance,
    invoice_discount_total,
    invoice_paid_total,
)
from app.services.nationalization import quantity_chain


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
        cur = inv.currency or importation.currency or DEFAULT_IMPORT_CURRENCY
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

    totals_by_currency = {
        cur: {
            "total_invoiced": str(b["invoiced"]) if not b["has_null_amount"] else None,
            "total_paid": str(b["paid"]),
            "total_discounts": str(b["discounts"]),
            "consolidated_balance": _balance(b),
        }
        for cur, b in buckets.items()
    }

    primary = importation.currency or DEFAULT_IMPORT_CURRENCY
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

        ordered = row.get("quantity_ordered")
        shipped = row.get("quantity_shipped")
        to_dispatch = max(0, ordered - shipped) if ordered is not None and shipped is not None else None

        qty_invoiced = invoiced_map.get(item_id)
        models.append(
            {
                "importation_item_id": item_id,
                "product_id": item.product_id if item else None,
                "supplier_sku": item.supplier_sku if item else None,
                "model_label": label,
                "quantity_ordered": ordered,
                "quantity_shipped": shipped,
                "quantity_nationalized": row.get("quantity_nationalized"),
                "quantity_stocked": row.get("quantity_stocked"),
                "quantity_invoiced": invoiced_map.get(item_id),
                "to_dispatch": to_dispatch,
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
                "amount": inv.amount,
                "currency": inv.currency,
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
            "currency_foreign": p.currency_foreign,
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

    discounts = (
        db.query(Discount)
        .join(Invoice, Discount.invoice_id == Invoice.id)
        .filter(Invoice.importation_id == importation_id, Discount.is_active.is_(True))
        .all()
    )
    credits = (
        db.query(Credit)
        .filter(
            Credit.supplier_id == imp.supplier_id,
            Credit.is_active.is_(True),
        )
        .all()
    )
    brazil_accounts = (
        db.query(BrazilCurrentAccount)
        .filter(
            BrazilCurrentAccount.supplier_id == imp.supplier_id,
            BrazilCurrentAccount.is_active.is_(True),
        )
        .all()
    )
    shipments = (
        db.query(Shipment)
        .filter(Shipment.importation_id == importation_id, Shipment.is_active.is_(True))
        .order_by(Shipment.created_at)
        .all()
    )

    return {
        "order": imp,
        "supplier_name": supplier.name if supplier else None,
        "kpis": {
            **financial,
            "to_dispatch": _compute_to_dispatch(chain),
        },
        "invoices": _build_invoices(db, importation_id),
        "models": _build_models(db, importation_id),
        "payments_planned": planned,
        "payments_settled": settled,
        "discounts": discounts,
        "supplier_credits": credits,
        "brazil_accounts": brazil_accounts,
        "shipments": shipments,
        "pending_actions": _pending_actions(db, imp),
    }


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
    for imp in imps:
        financial = _financial_totals_by_currency(db, imp)
        chain = quantity_chain(db, imp.id)
        actions = _pending_actions(db, imp)
        items.append(
            {
                "id": imp.id,
                "po_number": imp.po_number,
                "supplier_id": imp.supplier_id,
                "supplier_name": suppliers.get(imp.supplier_id),
                "status": imp.current_status,
                "currency": imp.currency,
                "total_invoiced": financial["total_invoiced"],
                "total_paid": financial["total_paid"],
                "consolidated_balance": financial["consolidated_balance"],
                "totals_by_currency": financial.get("totals_by_currency"),
                "to_dispatch": _compute_to_dispatch(chain),
                "pending_actions_count": len(actions),
                "updated_at": imp.updated_at,
                "created_at": imp.created_at,
            }
        )

    return {"items": items, "total": total}
