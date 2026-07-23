"""Corrige pagamento duplicado da fatura 561 na HEROES-132 (ordem id=167)."""

from __future__ import annotations

from decimal import Decimal

from app.database import SessionLocal
from app.models import ImportationOrder, Invoice, Payment
from app.services.auth import write_audit_log
from app.services.order_central import build_order_central


def main() -> None:
    db = SessionLocal()
    try:
        imp = (
            db.query(ImportationOrder)
            .filter(ImportationOrder.po_number == "HEROES-132", ImportationOrder.is_active.is_(True))
            .first()
        )
        if not imp:
            print("HEROES-132 nao encontrada.")
            return

        inv = (
            db.query(Invoice)
            .filter(
                Invoice.importation_id == imp.id,
                Invoice.invoice_number == "561.0",
                Invoice.is_active.is_(True),
            )
            .first()
        )
        if not inv:
            print("Fatura 561.0 nao encontrada.")
            return

        pay = (
            db.query(Payment)
            .filter(
                Payment.invoice_id == inv.id,
                Payment.receipt_reference == "ACCONTO-561.0",
                Payment.is_active.is_(True),
            )
            .first()
        )
        if not pay:
            print("Pagamento ACCONTO-561.0 nao encontrado.")
            return

        old_amount = pay.amount_foreign
        if old_amount == Decimal("48000"):
            print("Pagamento 561 ja esta correto (48000).")
        else:
            pay.amount_foreign = Decimal("48000")
            write_audit_log(
                db,
                user_id=None,
                entity_type="payment",
                entity_id=str(pay.id),
                action="heroes_132_acconto_correction",
                old_value=str(old_amount),
                new_value="48000",
            )
            print(f"Pagamento {pay.id}: {old_amount} -> 48000")

        if imp.estimated_total != Decimal("198500"):
            old_total = imp.estimated_total
            imp.estimated_total = Decimal("198500")
            write_audit_log(
                db,
                user_id=None,
                entity_type="importation_order",
                entity_id=str(imp.id),
                action="heroes_132_versato_estimated_total",
                old_value=str(old_total) if old_total is not None else None,
                new_value="198500",
            )
            print(f"estimated_total: {old_total} -> 198500")

        db.commit()

        oc = build_order_central(db, imp.id)
        oh = oc["operational_header"]
        print("Pos-correcao:")
        print(f"  settled_eur: {oh.get('settled_eur')}")
        print(f"  settled_brl: {oh.get('settled_brl')}")
        print(f"  order_total_eur: {oh.get('order_total_eur')}")
        print(f"  financial_alerts: {oh.get('financial_alerts')}")
        print(f"  quantity_ordered: {oh.get('quantity_ordered')}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
