"""Diagnóstico rápido HEROES-132 — qty, pagamentos, versato."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models import (
    HeroesImportRun,
    HeroesLegacySheetSummary,
    ImportationItem,
    ImportationOrder,
    Invoice,
    Payment,
    Product,
)
from app.services.finance import invoice_paid_total
from app.services.order_central import build_order_central
from app.services.nationalization import quantity_chain


def main() -> None:
    db = SessionLocal()
    try:
        imp = (
            db.query(ImportationOrder)
            .filter(
                ImportationOrder.po_number.ilike("%132%"),
                ImportationOrder.is_active.is_(True),
            )
            .order_by(ImportationOrder.id.desc())
            .all()
        )
        print("=== Ordens com 132 no PO ===")
        for o in imp:
            print(f"  id={o.id} po={o.po_number} estimated_total={o.estimated_total}")

        target = next((o for o in imp if "HEROES-132" in (o.po_number or "").upper() or o.po_number.endswith("-132")), imp[0] if imp else None)
        if not target:
            print("Nenhuma ordem 132 encontrada.")
            return

        imp_id = target.id
        print(f"\n=== Diagnóstico ordem id={imp_id} po={target.po_number} ===")

        legacy = (
            db.query(HeroesLegacySheetSummary)
            .filter(
                HeroesLegacySheetSummary.importation_id == imp_id,
                HeroesLegacySheetSummary.is_active.is_(True),
            )
            .first()
        )
        if legacy:
            print(f"versato: {legacy.versato_amount} {legacy.versato_currency} sheet={legacy.sheet_name}")

        chain = quantity_chain(db, imp_id)
        qty_total = sum(c.get("quantity_ordered") or 0 for c in chain)
        print(f"quantity_chain total: {qty_total} ({len(chain)} itens)")

        items = (
            db.query(ImportationItem)
            .options(joinedload(ImportationItem.product))
            .filter(ImportationItem.importation_id == imp_id, ImportationItem.is_active.is_(True))
            .all()
        )
        print("\n--- ImportationItem ---")
        for it in sorted(items, key=lambda x: (x.product.sku_code if x.product else x.description or "")):
            sku = it.product.sku_code if it.product else "?"
            print(f"  {sku}: qty={it.quantity_ordered} id={it.id}")

        invoices = (
            db.query(Invoice)
            .filter(Invoice.importation_id == imp_id, Invoice.is_active.is_(True))
            .order_by(Invoice.invoice_number)
            .all()
        )
        paid_total = Decimal("0")
        print("\n--- Faturas e pagamentos ---")
        for inv in invoices:
            paid = invoice_paid_total(db, inv)
            paid_total += paid
            pays = (
                db.query(Payment)
                .filter(Payment.invoice_id == inv.id, Payment.is_active.is_(True))
                .all()
            )
            print(f"  inv {inv.invoice_number}: paid={paid} payments={len(pays)}")
            for p in pays:
                print(f"    pay id={p.id} {p.amount_foreign} ref={p.receipt_reference}")

        print(f"\nTotal pagamentos liquidados: {paid_total}")

        run = (
            db.query(HeroesImportRun)
            .filter(HeroesImportRun.importation_id == imp_id)
            .order_by(HeroesImportRun.id.desc())
            .first()
        )
        if run:
            print(f"\nHeroes run: id={run.id} status={run.status} sheet={run.sheet_name}")

        oc = build_order_central(db, imp_id)
        oh = oc["operational_header"]
        print("\n--- Operational header ---")
        print(f"  quantity_ordered: {oh.get('quantity_ordered')}")
        print(f"  order_total_eur: {oh.get('order_total_eur')}")
        print(f"  settled_eur: {oh.get('settled_eur')}")
        print(f"  settled_brl: {oh.get('settled_brl')}")
        print(f"  brl_is_estimated: {oh.get('brl_is_estimated')}")
        print(f"  financial_alerts: {oh.get('financial_alerts')}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
