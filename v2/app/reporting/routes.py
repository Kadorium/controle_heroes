"""Rotas HTTP Reporting — owner do summary da ordem, da fila AP rica e do painel."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.foundation.deps import enforce_permission, get_current_user, get_db, permission_set
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
from app.orders.public import OrdersError
from app.inventory import public as inventory_public
from typing import Literal
from app.reporting import dashboard as dash
from app.reporting import public as reporting_public
from app.reporting import views as view_cmds
from app.reporting import commercial as commercial_mod
from app.reporting.registry import ROLE_DEFAULT_PRESET, default_layout, presets_by_id
from app.reporting.schemas import (
    CommercialAvailabilityOut,
    DashboardSnapshotOut,
    MetricCatalogOut,
    ViewCreateIn,
    ViewOut,
    ViewPatchIn,
    ViewRestoreIn,
)

router = APIRouter(tags=["reporting"])


@router.get("/reporting/stock-positions", response_model=inventory_public.StockPositionsResponse)
def get_stock_positions(
    q: str | None = None, regime: Literal["DOMESTIC", "BONDED", "QUARANTINE"] | None = None,
    location_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    status: Literal["positive", "zero", "all"] = "positive",
    sort: Literal["name", "-name", "sku", "-sku", "DOMESTIC", "-DOMESTIC", "BONDED", "-BONDED", "QUARANTINE", "-QUARANTINE"] = "name",
    limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user), db: Session = Depends(get_db),
):
    enforce_permission(user, "inventory:read")
    return inventory_public.positions(db, q=q, product_id=product_id, regime=regime, location_id=location_id,
                                      status=status, sort=sort, limit=limit, offset=offset)


def _map_orders_error(exc: OrdersError) -> AppError:
    code = getattr(exc, "code", "orders_error")
    status = 404 if str(code).endswith("not_found") else 400
    return AppError(getattr(exc, "message", str(exc)), code=code, status_code=status)


def _perms(user) -> tuple[set[str], bool, str, str]:
    role = user.role.name
    is_admin = role == "admin"
    perms = permission_set(user)
    return perms, is_admin, role, str(user.id)


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


@router.get("/reporting/orders-list")
def get_orders_list(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Fila Pedidos enriquecida. Permissão orders:read (superfície Pedidos; RM em Reporting)."""
    enforce_permission(user, "orders:read")
    return reporting_public.orders_list(db, status=status, limit=limit, offset=offset)


@router.get("/reporting/metric-catalog", response_model=MetricCatalogOut)
def get_metric_catalog(
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    perms, is_admin, _role, _actor = _perms(user)
    return dash.catalog_payload(perms, is_admin=is_admin)


def _parse_view_token(view: str | None) -> tuple[str | None, int | None]:
    if not view:
        return None, None
    if view.isdigit():
        return None, int(view)
    return view, None


def _filters_from_view(raw: dict | None) -> dict:
    raw = raw or {}
    out: dict = {}
    for key in ("date_from", "date_to", "as_of", "currency", "period"):
        val = raw.get(key)
        out[key] = val if val not in ("", None) else None
    sid = raw.get("supplier_id")
    out["supplier_id"] = int(sid) if sid not in (None, "") else None
    return out


@router.get("/reporting/commercial-availability", response_model=CommercialAvailabilityOut)
def get_commercial_availability(
    q: str | None = None,
    category: str | None = None,
    product_type: str | None = None,
    status: str | None = None,
    sort: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    enforce_permission(user, "catalog:read")
    return commercial_mod.availability(
        db,
        q=q,
        category=category,
        product_type=product_type,
        status=status,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/reporting/dashboard", response_model=DashboardSnapshotOut)
def get_dashboard(
    view: str | None = None,
    period: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    as_of: date | None = None,
    currency: str | None = None,
    supplier_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    perms, is_admin, role, actor_id = _perms(user)
    settings = get_settings()
    lane = dash.lane_from_settings(settings.app_env, settings.database_url)

    preset_slug, view_id = _parse_view_token(view)
    layout = None
    view_name = None
    base_preset = ROLE_DEFAULT_PRESET.get(role, "executiva")
    stored_filters: dict = {}
    view_token = base_preset

    if view_id is not None:
        row = view_cmds.get_view(db, actor_id, view_id)
        layout = row.layout_json
        view_name = row.name
        base_preset = row.base_preset
        stored_filters = _filters_from_view(row.filters_json)
        view_token = str(row.id)
    elif preset_slug:
        if preset_slug not in presets_by_id():
            raise AppError("preset desconhecido", code="invalid_preset", status_code=400)
        base_preset = preset_slug
        layout = default_layout(base_preset)
        view_name = presets_by_id()[base_preset].label
        view_token = base_preset
    else:
        default_id = view_cmds.default_view_id(db, actor_id)
        if default_id is not None:
            row = view_cmds.get_view(db, actor_id, default_id)
            layout = row.layout_json
            view_name = row.name
            base_preset = row.base_preset
            stored_filters = _filters_from_view(row.filters_json)
            view_token = str(row.id)
        else:
            layout = default_layout(base_preset)
            view_name = presets_by_id()[base_preset].label
            view_token = base_preset

    def pick_date(query_val, stored_key):
        if query_val is not None:
            return query_val
        raw = stored_filters.get(stored_key)
        if not raw:
            return None
        return date.fromisoformat(str(raw))

    merged_from = pick_date(date_from, "date_from")
    merged_to = pick_date(date_to, "date_to")
    merged_as_of = pick_date(as_of, "as_of")
    merged_cur = currency or stored_filters.get("currency")
    merged_sup = supplier_id if supplier_id is not None else stored_filters.get("supplier_id")
    period_token = period or stored_filters.get("period")
    resolved_period, merged_from, merged_to, merged_as_of = dash.resolve_period(
        period_token,
        merged_from,
        merged_to,
        merged_as_of,
    )

    return dash.snapshot(
        db,
        permissions=perms,
        is_admin=is_admin,
        role=role,
        layout=layout,
        view_id=view_token,
        view_name=view_name,
        base_preset=base_preset,
        date_from=merged_from,
        date_to=merged_to,
        as_of=merged_as_of,
        currency=merged_cur.upper() if isinstance(merged_cur, str) and merged_cur else None,
        supplier_id=int(merged_sup) if merged_sup is not None else None,
        lane=lane,
        period=resolved_period,
    )


@router.get("/reporting/views", response_model=list[ViewOut])
def list_dashboard_views(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    _perms_set, _admin, _role, actor_id = _perms(user)
    return view_cmds.list_views(db, actor_id)


@router.post("/reporting/views", response_model=ViewOut)
def create_dashboard_view(
    body: ViewCreateIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    _p, _a, _r, actor_id = _perms(user)
    with UnitOfWork(session=db) as uow:
        out = view_cmds.create_view(
            uow.session,
            actor_id=actor_id,
            name=body.name,
            base_preset=body.base_preset,
            layout_json=body.layout_json,
            filters_json=body.filters_json,
            is_default=body.is_default,
        )
        uow.commit()
        return out


@router.patch("/reporting/views/{view_id}", response_model=ViewOut)
def patch_dashboard_view(
    view_id: int,
    body: ViewPatchIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    _p, _a, _r, actor_id = _perms(user)
    with UnitOfWork(session=db) as uow:
        out = view_cmds.patch_view(
            uow.session,
            actor_id=actor_id,
            view_id=view_id,
            expected_version=body.version,
            name=body.name,
            layout_json=body.layout_json,
            filters_json=body.filters_json,
            is_default=body.is_default,
        )
        uow.commit()
        return out


@router.delete("/reporting/views/{view_id}")
def delete_dashboard_view(
    view_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    _p, _a, _r, actor_id = _perms(user)
    with UnitOfWork(session=db) as uow:
        view_cmds.delete_view(uow.session, actor_id=actor_id, view_id=view_id)
        uow.commit()
    return {"ok": True}


@router.post("/reporting/views/{view_id}/restore", response_model=ViewOut)
def restore_dashboard_view(
    view_id: int,
    body: ViewRestoreIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "reporting:read")
    _p, _a, _r, actor_id = _perms(user)
    with UnitOfWork(session=db) as uow:
        out = view_cmds.restore_view(
            uow.session, actor_id=actor_id, view_id=view_id, expected_version=body.version
        )
        uow.commit()
        return out
