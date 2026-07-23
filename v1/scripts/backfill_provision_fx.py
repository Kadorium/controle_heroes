"""Backfill câmbio provisionado (OPENING_PROVISION + expected_exchange_rate nas faturas).

Uso:
  python scripts/backfill_provision_fx.py --po HEROES-132 --rate 5.90
  python scripts/backfill_provision_fx.py --po HEROES-132 --rate 5.90 --normalize-invoice-numbers
"""

from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.enums import ExchangeRateType
from app.database import SessionLocal
from app.models import ExchangeRate, ImportationOrder, Invoice
from app.services.auth import write_audit_log
from app.services.finance import register_exchange_rate


def _normalize_inv_num(val: str) -> str:
    try:
        d = Decimal(val)
        if d == d.to_integral_value():
            return str(int(d))
    except (InvalidOperation, ValueError):
        pass
    return val


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill câmbio provisionado por ordem")
    parser.add_argument("--po", required=True, help="po_number da ordem (ex.: HEROES-132)")
    parser.add_argument("--rate", required=True, help="Taxa EUR→BRL provisionada")
    parser.add_argument(
        "--normalize-invoice-numbers",
        action="store_true",
        help="Normaliza invoice_number 72.0 → 72 (preserva demais formatos)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        rate = Decimal(str(args.rate).replace(",", "."))
    except InvalidOperation as e:
        raise SystemExit(f"Taxa inválida: {args.rate}") from e
    if rate <= 0:
        raise SystemExit("Taxa deve ser positiva")

    db = SessionLocal()
    try:
        imp = (
            db.query(ImportationOrder)
            .filter(ImportationOrder.po_number == args.po, ImportationOrder.is_active.is_(True))
            .first()
        )
        if not imp:
            raise SystemExit(f"Ordem {args.po!r} não encontrada")

        existing = (
            db.query(ExchangeRate)
            .filter(
                ExchangeRate.importation_id == imp.id,
                ExchangeRate.rate_type == "OPENING_PROVISION",
            )
            .first()
        )
        if existing and existing.rate_value is not None:
            print(f"OPENING_PROVISION já existe: {existing.rate_value} (id={existing.id})")
        elif args.dry_run:
            print(f"[dry-run] Criaria OPENING_PROVISION={rate} para ordem id={imp.id}")
        else:
            register_exchange_rate(
                db,
                currency_from=imp.currency or "EUR",
                rate_type="OPENING_PROVISION",
                rate_value=rate,
                user_id=None,
                importation_id=imp.id,
                comment=f"Backfill provisão --po {args.po}",
            )
            print(f"OPENING_PROVISION={rate} registrado para {args.po}")

        invoices = (
            db.query(Invoice)
            .filter(Invoice.importation_id == imp.id, Invoice.is_active.is_(True))
            .all()
        )
        updated_inv = 0
        normalized = 0
        for inv in invoices:
            if args.normalize_invoice_numbers and inv.invoice_number:
                new_num = _normalize_inv_num(inv.invoice_number)
                if new_num != inv.invoice_number and re.match(r"^\d+\.0$", inv.invoice_number):
                    if args.dry_run:
                        print(f"[dry-run] invoice {inv.id}: {inv.invoice_number!r} → {new_num!r}")
                    else:
                        old = inv.invoice_number
                        inv.invoice_number = new_num
                        write_audit_log(
                            db,
                            user_id=None,
                            entity_type="invoice",
                            entity_id=str(inv.id),
                            action="backfill_normalize_invoice_number",
                            old_value=old,
                            new_value=new_num,
                        )
                    normalized += 1

            if inv.expected_exchange_rate is not None:
                continue
            if args.dry_run:
                print(f"[dry-run] invoice {inv.id} ({inv.invoice_number}): expected_exchange_rate={rate}")
            else:
                inv.expected_exchange_rate = rate
                register_exchange_rate(
                    db,
                    currency_from=inv.currency or "EUR",
                    rate_type=ExchangeRateType.ESTIMATED.value,
                    rate_value=rate,
                    user_id=None,
                    importation_id=imp.id,
                    invoice_id=inv.id,
                    comment=f"Backfill provisão fatura --po {args.po}",
                )
            updated_inv += 1

        if not args.dry_run:
            db.commit()

        print(f"Faturas atualizadas com provisão: {updated_inv}/{len(invoices)}")
        if args.normalize_invoice_numbers:
            print(f"Números de fatura normalizados: {normalized}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
