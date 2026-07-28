"""Rotas HTTP Reporting — owner do summary da ordem e da fila AP rica."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.foundation.deps import enforce_permission, get_current_user, get_db
from app.foundation.errors import AppError
from app.orders.public import OrdersError
from app.reporting import public as reporting_public

router = APIRouter(tags=["reporting"])


def _map_orders_error(exc: OrdersError) -> AppError:
    code = getattr(exc, "code", "orders_error")
    status = 404 if str(code).endswith("not_found") else 400
    return AppError(getattr(exc, "message", str(exc)), code=code, status_code=status)


@router.get("/reporting/ap-queue")
def get_ap_queue(
    due_before: date | None = None,
    due_after: date | None = None,
    supplier_id: int | None = None,
    order_id: int | None = None,
    invoice_id: int | None = None,
    currency: str | None = None,
    status: str | None = None,
    pending: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    enforce_permission(user, "billing:read")
    return reporting_public.ap_queue(
        db,
        due_before=due_before,
        due_after=due_after,
        supplier_id=supplier_id,
        order_id=order_id,
        invoice_id=invoice_id,
        currency=currency,
        status=status,
        pending=pending,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/{order_id}/summary")
def get_order_summary(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Cockpit read model — ownership Reporting (não Orders). Path funcional sob /orders."""
    enforce_permission(user, "reporting:read")
    enforce_permission(user, "orders:read")
    try:
        return reporting_public.order_cockpit(db, order_id)
    except OrdersError as e:
        raise _map_orders_error(e) from e
