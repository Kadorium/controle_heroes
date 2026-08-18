"""Fatos de Billing usados na composição HTTP de Orders — sem ciclo de domínio.

Orders ↛ Billing (ADR-11). A rota de bind consulta qty emitida daqui.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import public as billing_public


def issued_qty_for_order_item(db: Session, order_id: int, order_item_id: int) -> Decimal:
    return billing_public.issued_qty_for_order_item(db, order_id, order_item_id)
