"""Snapshot do painel — composição read-only, isolada por widget."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.costing import public as costing_public
from app.customs import public as customs_public
from app.ingestion import public as ingestion_public
from app.inventory import public as inventory_public
from app.logistics import public as logistics_public
from app.orders import public as orders_public
from app.reporting.registry import (
    ATTENTION_LIMIT_DEFAULT,
    LAYOUT_SCHEMA_VERSION,
    ROLE_DEFAULT_PRESET,
    ROLE_FALLBACK_PATH,
    WidgetDef,
    metric_to_public,
    metrics_by_id,
    presets_by_id,
    selectable_widget_ids,
    widget_to_public,
    widgets_by_id,
)
from app.reporting import commercial as commercial_mod
from app.reporting import exceptions as exceptions_mod
from app.treasury import public as treasury_public

SEV_RANK = {"blocker": 0, "overdue": 1, "due_today": 2, "warning": 3}
VALID_PERIODS = ("next_90", "next_30", "this_month", "custom")
_MONEY_Q = Decimal("0.01")


def _q2(value: Decimal) -> str:
    return f"{value.quantize(_MONEY_Q):.2f}"


def resolve_period(
    period: str | None,
    date_from: date | None,
    date_to: date | None,
    as_of: date | None,
) -> tuple[str, date | None, date | None, date | None]:
    """DEC-J7-PERIOD: relativo por omissão; custom revela as datas."""
    from calendar import monthrange

    raw = (period or "").strip()
    if raw and raw not in VALID_PERIODS:
        raw = "next_90"
    if not raw:
        if date_from or date_to or as_of:
            return "custom", date_from, date_to, as_of
        raw = "next_90"
    if raw == "custom":
        return "custom", date_from, date_to, as_of
    today = date.today()
    if raw == "next_30":
        return "next_30", None, today + timedelta(days=30), None
    if raw == "this_month":
        last = date(today.year, today.month, monthrange(today.year, today.month)[1])
        return "this_month", None, last, None
    return "next_90", None, today + timedelta(days=90), None


def _human_payable_title(row: dict[str, Any]) -> str:
    party = str(row.get("supplier_name") or row.get("payee_display_name") or "").strip()
    doc = str(row.get("invoice_number") or "").strip()
    if party and doc and party != doc:
        return f"{party} · {doc}"
    return party or doc or "Obrigação sem identificação"


def _relative_due_copy(row: dict[str, Any], *, due_today: bool) -> str:
    days = int(row.get("days_overdue") or 0)
    if days > 0:
        if days == 1:
            return "Vencida há 1 dia"
        return f"Vencida há {days} dias"
    if due_today:
        return "Vence hoje"
    return "A vencer"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def lane_from_settings(app_env: str, database_url: str) -> dict[str, Any]:
    test = app_env == "test" or "epic_v2_test" in (database_url or "")
    if test:
        return {
            "lane": "test",
            "includes_trial_mass": True,
            "note": "Ambiente de teste. Os números podem incluir massa de ensaio.",
        }
    return {
        "lane": "ops",
        "includes_trial_mass": False,
        "note": None,
    }


def user_can(permissions: set[str], *, is_admin: bool, required: str) -> bool:
    if is_admin:
        return True
    return required in permissions


def widget_allowed(w: WidgetDef, permissions: set[str], *, is_admin: bool) -> bool:
    if w.status == "NOT_AVAILABLE":
        return False
    if is_admin:
        return True
    return all(p in permissions for p in w.permissions if p != "reporting:read")


def catalog_payload(permissions: set[str], *, is_admin: bool) -> dict[str, Any]:
    mmap = metrics_by_id()
    metrics = []
    for m in mmap.values():
        if m.status == "NOT_AVAILABLE":
            continue
        if not user_can(permissions, is_admin=is_admin, required=m.permission):
            continue
        metrics.append(metric_to_public(m))
    widgets = [
        widget_to_public(w)
        for w in widgets_by_id().values()
        if widget_allowed(w, permissions, is_admin=is_admin)
    ]
    presets = [
        {
            "preset_id": p.preset_id,
            "label": p.label,
            "widget_ids": list(p.widget_ids),
            "hidden": p.hidden,
            "filters": list(p.filters),
        }
        for p in presets_by_id().values()
    ]
    return {
        "generated_at": _now().isoformat(),
        "metrics": metrics,
        "widgets": widgets,
        "presets": presets,
        "attention_limit_default": ATTENTION_LIMIT_DEFAULT,
        "layout_schema_version": LAYOUT_SCHEMA_VERSION,
    }


def _filter_meta(applied: list[str], ignored: list[str], time_field: str | None) -> dict[str, Any]:
    return {
        "filters_applied": applied,
        "filters_ignored": ignored,
        "time_field": time_field,
    }


def _ap_queue(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    currency: str | None,
    supplier_id: int | None,
    pending: str | None,
    limit: int,
) -> dict[str, Any]:
    return billing_public.payables_queue(
        db,
        due_after=date_from,
        due_before=date_to,
        currency=currency,
        supplier_id=supplier_id,
        pending=pending,
        limit=limit,
        offset=0,
    )


def _kpi_currency_display(kpis: dict[str, Any], field: str) -> dict[str, Any]:
    rows = []
    for row in kpis.get("kpis_by_currency") or []:
        rows.append(
            {
                "currency": row["currency"],
                "amount": row.get(field),
                "count": row.get("overdue_count") if field.startswith("overdue") else row.get("total_count"),
            }
        )
    return {
        "by_currency": rows,
        "mixed_currency": bool(kpis.get("mixed_currency")),
        "total_count": kpis.get("total_count"),
        "overdue_count": kpis.get("overdue_count"),
    }


def _build_attention(
    db: Session,
    *,
    permissions: set[str],
    is_admin: bool,
    date_from: date | None,
    date_to: date | None,
    currency: str | None,
    supplier_id: int | None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    consulted: list[str] = []
    unavailable: list[str] = []
    forbidden: list[str] = []
    errors: list[str] = []

    def add_error(owner: str, exc: Exception) -> None:
        errors.append(owner)
        items.append(
            {
                "item_type": "owner_error",
                "severity": "warning",
                "title": "Dados indisponíveis",
                "reason": f"Não foi possível consultar {owner}.",
                "due_at": None,
                "age": None,
                "owner_module": owner,
                "href": None,
                "permission": None,
                "currency": None,
                "amount": None,
                "source_updated_at": _now().isoformat(),
            }
        )

    if user_can(permissions, is_admin=is_admin, required="billing:read"):
        consulted.append("billing")
        try:
            overdue = _ap_queue(
                db,
                date_from=date_from,
                date_to=date_to,
                currency=currency,
                supplier_id=supplier_id,
                pending="OVERDUE",
                limit=20,
            )
            today = date.today()
            for row in overdue.get("items") or []:
                items.append(
                    {
                        "item_type": "ap_overdue",
                        "severity": "overdue",
                        "title": _human_payable_title(row),
                        "reason": _relative_due_copy(row, due_today=False),
                        "due_at": row.get("due_date"),
                        "age": row.get("days_overdue"),
                        "owner_module": "billing",
                        "href": f"/payables?pending=OVERDUE&currency={row.get('currency') or ''}",
                        "permission": "billing:read",
                        "currency": row.get("currency"),
                        "amount": row.get("balance"),
                        "source_updated_at": _now().isoformat(),
                    }
                )
            due_today = billing_public.payables_queue(
                db,
                due_after=today,
                due_before=today,
                currency=currency,
                supplier_id=supplier_id,
                pending="OPEN_BALANCE",
                limit=20,
                offset=0,
            )
            for row in due_today.get("items") or []:
                items.append(
                    {
                        "item_type": "ap_due_today",
                        "severity": "due_today",
                        "title": _human_payable_title(row),
                        "reason": _relative_due_copy(row, due_today=True),
                        "due_at": row.get("due_date"),
                        "age": 0,
                        "owner_module": "billing",
                        "href": "/payables?pending=OPEN_BALANCE",
                        "permission": "billing:read",
                        "currency": row.get("currency"),
                        "amount": row.get("balance"),
                        "source_updated_at": _now().isoformat(),
                    }
                )
        except Exception as exc:  # noqa: BLE001 — isolamento do widget
            add_error("billing", exc)
        if user_can(permissions, is_admin=is_admin, required="treasury:fx_read"):
            try:
                open_q = _ap_queue(
                    db,
                    date_from=date_from,
                    date_to=date_to,
                    currency=currency,
                    supplier_id=supplier_id,
                    pending="OPEN_BALANCE",
                    limit=50,
                )
                pids = [int(r["id"]) for r in (open_q.get("items") or [])]
                plans = treasury_public.fx.get_current_plans_bulk(db, pids) if pids else {}
                missing = 0
                example_href = "/payables?pending=OPEN_BALANCE"
                for row in open_q.get("items") or []:
                    if int(row["id"]) not in plans:
                        missing += 1
                if missing:
                    items.append(
                        {
                            "item_type": "missing_fx",
                            "severity": "warning",
                            "title": f"{missing} obrigação(ões) sem taxa projetada",
                            "reason": "Não há plano cambial vigente na amostra em aberto.",
                            "due_at": None,
                            "age": None,
                            "owner_module": "treasury",
                            "href": example_href,
                            "permission": "treasury:fx_read",
                            "currency": None,
                            "amount": None,
                            "source_updated_at": _now().isoformat(),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                add_error("treasury", exc)
    else:
        forbidden.append("billing")

    if user_can(permissions, is_admin=is_admin, required="catalog:read"):
        consulted.append("catalog")
        try:
            summary = catalog_public.product_list_summary(db)
            n = int(summary.get("needs_review") or 0)
            if n:
                items.append(
                    {
                        "item_type": "catalog_review",
                        "severity": "warning",
                        "title": f"{n} produto(s) para revisar",
                        "reason": "Decisão de importação = revisar.",
                        "due_at": None,
                        "age": None,
                        "owner_module": "catalog",
                        "href": "/catalog/products?needs_review=1",
                        "permission": "catalog:read",
                        "currency": None,
                        "amount": None,
                        "source_updated_at": _now().isoformat(),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            add_error("catalog", exc)
    else:
        forbidden.append("catalog")

    items.sort(
        key=lambda it: (
            SEV_RANK.get(str(it.get("severity")), 9),
            it.get("due_at") or "9999-12-31",
            str(it.get("source_updated_at") or ""),
        )
    )
    total = len(items)
    limit = ATTENTION_LIMIT_DEFAULT
    empty_kind = "none"
    empty_copy = "Nada precisa da sua decisão agora."
    if errors:
        empty_kind = "error"
        empty_copy = "Alguns módulos falharam; as demais pendências aparecem abaixo."
    elif forbidden and not consulted:
        empty_kind = "forbidden"
        empty_copy = "Sem permissão para as pendências desta visão."
    elif unavailable:
        empty_kind = "unavailable"
        empty_copy = "Há módulos sem fato nesta visão."
    elif total == 0:
        empty_kind = "none"
        empty_copy = "Nada precisa da sua decisão agora."

    return {
        "items": items[:limit],
        "all_items": items,
        "total_count": total,
        "limit": limit,
        "empty_kind": empty_kind,
        "empty_copy": empty_copy,
        "consulted": consulted,
        "forbidden": forbidden,
        "unavailable": unavailable,
        "errors": errors,
    }


def _wrap_widget(
    w: WidgetDef,
    *,
    display: dict[str, Any],
    drill: str,
    currencies: list[str],
    applied: list[str],
    ignored: list[str],
    time_field: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    state = display.get("state")
    if not state:
        if error:
            state = "error"
        elif display.get("empty_kind") == "forbidden":
            state = "forbidden"
        elif display.get("unavailable") or display.get("absence"):
            state = "absent"
        elif display.get("empty") or display.get("empty_kind") in ("none", "empty"):
            state = "empty"
        else:
            state = "ok"
        display = {**display, "state": state}
    return {
        "widget_id": w.widget_id,
        "metric_id": w.metric_ids[0],
        "label": w.label,
        "short_description": w.short_description,
        "kind": w.kind,
        "status": w.status,
        "limitation": w.limitation,
        "display": display,
        "drill": w.drill or drill,
        "cta_label": w.cta_label,
        "section": w.section,
        "size": w.size,
        "currencies": currencies,
        **_filter_meta(applied, ignored, time_field),
        "error": error,
    }


def _ap_filters(
    date_from: date | None,
    date_to: date | None,
    currency: str | None,
    supplier_id: int | None,
    extra_ignored: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    applied = []
    ignored = list(extra_ignored or [])
    if date_from:
        applied.append("date_from")
    if date_to:
        applied.append("date_to")
    if currency:
        applied.append("currency")
    if supplier_id:
        applied.append("supplier_id")
    return applied, ignored


def build_widget(
    db: Session,
    w: WidgetDef,
    *,
    permissions: set[str],
    is_admin: bool,
    date_from: date | None,
    date_to: date | None,
    as_of: date | None,
    currency: str | None,
    supplier_id: int | None,
) -> dict[str, Any]:
    if not widget_allowed(w, permissions, is_admin=is_admin):
        return _wrap_widget(
            w,
            display={"empty_kind": "forbidden", "message": "Sem permissão para este bloco."},
            drill="",
            currencies=[],
            applied=[],
            ignored=["date_from", "date_to", "as_of", "currency", "supplier_id"],
            time_field=None,
            error=None,
        )

    as_of_ignored = ["as_of"] if as_of else []

    if w.widget_id == "ap.cash_due":
        data = billing_public.cash_committed_by_month(
            db, due_before=date_to, currency=currency, supplier_id=supplier_id
        )
        by = []
        for row in data.get("by_currency") or []:
            buckets = row.get("buckets") or {}
            amt = sum(Decimal(str(buckets.get(k) or "0")) for k in ("m0", "m1", "m2"))
            by.append({"currency": row.get("currency"), "amount": _q2(amt)})
        empty = not by or all(Decimal(str(r["amount"])) == 0 for r in by)
        applied, ignored = _ap_filters(date_from, date_to, currency, supplier_id, as_of_ignored)
        return _wrap_widget(
            w,
            display={
                "by_currency": by,
                "mixed_currency": len({r["currency"] for r in by}) > 1,
                "empty": empty,
                "message": "Nada a vencer neste recorte." if empty else None,
            },
            drill="/payables",
            currencies=[r["currency"] for r in by],
            applied=applied,
            ignored=ignored,
            time_field="due_date",
        )

    if w.widget_id == "orders.to_invoice":
        data = billing_public.order_billing_progress_by_currency(db)
        rows = data.get("by_currency") or []
        if currency:
            rows = [r for r in rows if r.get("currency") == currency.upper()]
        by = [{"currency": r.get("currency"), "amount": r.get("to_invoice")} for r in rows]
        empty = not by or all(Decimal(str(r.get("amount") or "0")) == 0 for r in by)
        applied = ["currency"] if currency else []
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display={
                "by_currency": by,
                "mixed_currency": len({r["currency"] for r in by}) > 1,
                "empty": empty,
                "message": "Nada a faturar." if empty else None,
            },
            drill="/orders",
            currencies=[r["currency"] for r in by],
            applied=applied,
            ignored=ignored,
            time_field="order_date",
        )

    if w.widget_id == "treasury.fx_trend":
        series = treasury_public.fx.fx_quote_series(db, foreign="EUR", base="BRL", days=30)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("currency", currency), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display={
                **series,
                "message": "Sem cotações no período." if series.get("empty") else None,
            },
            drill="",
            currencies=["EUR"],
            applied=["as_of"] if as_of else [],
            ignored=ignored,
            time_field="as_of",
        )

    if w.widget_id == "commercial.availability":
        data = commercial_mod.availability(db, limit=50, offset=0)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("currency", currency), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display=data,
            drill="/catalog/products",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "control.exceptions":
        data = exceptions_mod.collect(db, permissions=permissions, is_admin=is_admin, limit=40)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("currency", currency), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display=data,
            drill="",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "attention.inbox":
        data = _build_attention(
            db,
            permissions=permissions,
            is_admin=is_admin,
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            supplier_id=supplier_id,
        )
        applied, ignored = _ap_filters(date_from, date_to, currency, supplier_id, as_of_ignored)
        return _wrap_widget(
            w,
            display=data,
            drill="/payables",
            currencies=[],
            applied=applied,
            ignored=ignored,
            time_field="due_date",
        )

    if w.kind in ("kpi_currency", "aging_bar", "table") and w.widget_id.startswith("ap."):
        pending = "OVERDUE" if w.widget_id == "ap.overdue" else "OPEN_BALANCE"
        core = _ap_queue(
            db,
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            supplier_id=supplier_id,
            pending=pending,
            limit=8 if w.kind == "table" else 1,
        )
        kpis = core.get("kpis") or {}
        applied, ignored = _ap_filters(date_from, date_to, currency, supplier_id, as_of_ignored)
        field = {
            "ap.next_7d": "next_7d_balance",
            "ap.overdue": "overdue_balance",
            "ap.open_balance": "open_balance",
        }.get(w.widget_id, "open_balance")
        currencies = [r["currency"] for r in (kpis.get("kpis_by_currency") or [])]
        if w.kind == "table":
            rows = []
            for r in core.get("items") or []:
                item = dict(r)
                item["display_title"] = _human_payable_title(item)
                rows.append(item)
            display: dict[str, Any] = {
                "rows": rows,
                "total": core.get("total"),
                "kpis": kpis,
            }
            drill = "/payables?pending=OPEN_BALANCE"
        elif w.kind == "aging_bar":
            display = {"kpis_by_currency": kpis.get("kpis_by_currency") or [], "mixed_currency": kpis.get("mixed_currency")}
            drill = "/payables"
        else:
            display = _kpi_currency_display(kpis, field)
            drill = "/payables?pending=OVERDUE" if w.widget_id == "ap.overdue" else "/payables"
        return _wrap_widget(
            w,
            display=display,
            drill=drill,
            currencies=currencies,
            applied=applied,
            ignored=ignored,
            time_field="due_date",
        )

    if w.widget_id == "catalog.quality":
        summary = catalog_public.product_list_summary(db)
        display = {
            "total": summary.get("total"),
            "needs_review": summary.get("needs_review"),
            "classification_review": summary.get("needs_classification_review"),
            "missing_ncm": summary.get("missing_ncm"),
            "universe": "catálogo completo, inclusive histórico importado",
        }
        ignored = []
        if date_from:
            ignored.append("date_from")
        if date_to:
            ignored.append("date_to")
        if as_of:
            ignored.append("as_of")
        if currency:
            ignored.append("currency")
        if supplier_id:
            ignored.append("supplier_id")
        return _wrap_widget(
            w,
            display=display,
            drill="/catalog/products?needs_review=1",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "treasury.fx_quote":
        quote = treasury_public.fx.get_latest_quote(db, "EUR", "BRL")
        if not quote:
            display = {"unavailable": True, "message": "Cotação indisponível"}
        else:
            stale = quote.stale_after < _now()
            display = {
                "unavailable": False,
                "rate": str(quote.rate),
                "source": quote.source,
                "status": treasury_public.fx.quote_status(quote),
                "stale": stale,
                "observed_at": quote.observed_at.isoformat() if quote.observed_at else None,
                "pair": "EUR/BRL",
            }
        ignored = []
        applied = ["as_of"] if as_of else []
        if date_from:
            ignored.append("date_from")
        if date_to:
            ignored.append("date_to")
        if currency:
            ignored.append("currency")
        if supplier_id:
            ignored.append("supplier_id")
        return _wrap_widget(
            w,
            display=display,
            drill="/payables",
            currencies=["EUR", "BRL"],
            applied=applied,
            ignored=ignored,
            time_field="as_of",
        )

    if w.widget_id == "treasury.unallocated":
        bulk = treasury_public.unallocated_registered_bulk(db)
        ignored = []
        if date_from:
            ignored.append("date_from")
        if date_to:
            ignored.append("date_to")
        if as_of:
            ignored.append("as_of")
        applied = []
        if currency:
            applied.append("currency")
            bulk = {
                **bulk,
                "by_currency": [r for r in bulk.get("by_currency") or [] if r["currency"] == currency.upper()],
                "mixed_currency": False,
            }
        if supplier_id:
            ignored.append("supplier_id")
        return _wrap_widget(
            w,
            display=bulk,
            drill="/payments?unallocated_only=1",
            currencies=[r["currency"] for r in bulk.get("by_currency") or []],
            applied=applied,
            ignored=ignored,
            time_field="payment_date",
        )

    if w.widget_id == "orders.status":
        counts = orders_public.order_status_counts(db)
        pend = orders_public.order_line_pendencies(db)
        ignored = []
        applied = []
        if date_from:
            ignored.append("date_from")
        if date_to:
            ignored.append("date_to")
        if as_of:
            ignored.append("as_of")
        if currency:
            ignored.append("currency")
        if supplier_id:
            ignored.append("supplier_id")
        return _wrap_widget(
            w,
            display={"by_status": counts, **pend},
            drill="/orders",
            currencies=[],
            applied=applied,
            ignored=ignored,
            time_field="order_date",
        )

    if w.widget_id == "orders.qty_residual":
        residual = billing_public.qty_to_invoice_residual(db)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("currency", currency), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display=residual,
            drill="/orders",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "logistics.shipments":
        counts = logistics_public.shipment_counts_by_status(db)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("currency", currency), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display={"by_status": counts, "in_course": int(counts.get("PLANNED", 0) + counts.get("BOOKED", 0) + counts.get("IN_TRANSIT", 0))},
            drill="/shipments",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "inventory.overview":
        overview = inventory_public.stock_overview_by_location_type(db)
        applied = ["as_of"] if as_of else []
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("currency", currency), ("supplier_id", supplier_id)) if v]
        empty = overview.get("sku_with_balance", 0) == 0
        return _wrap_widget(
            w,
            display={**overview, "empty": empty, "message": "Nenhum saldo com quantidade" if empty else None},
            drill="/inventory/movements",
            currencies=[],
            applied=applied,
            ignored=ignored,
            time_field="as_of",
        )

    if w.widget_id == "ingestion.queue":
        summary = ingestion_public.staging_queue_summary(db)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("currency", currency), ("supplier_id", supplier_id)) if v]
        empty = int(summary.get("total_open") or 0) == 0
        return _wrap_widget(
            w,
            display={
                **summary,
                "empty": empty,
                "message": "Nenhum documento em revisão" if empty else None,
            },
            drill="/ingestion",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "billing.invoices_split":
        counts = billing_public.invoice_status_counts(db)
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("as_of", as_of), ("currency", currency), ("supplier_id", supplier_id)) if v]
        return _wrap_widget(
            w,
            display={"by_status": counts},
            drill="/invoices",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field="invoice_date",
        )

    if w.widget_id == "ap.cash_committed":
        data = billing_public.cash_committed_by_month(
            db,
            due_before=date_to,
            currency=currency,
            supplier_id=supplier_id,
        )
        quote = None
        if user_can(permissions, is_admin=is_admin, required="treasury:fx_read"):
            quote = treasury_public.fx.get_latest_quote(db, "EUR", "BRL")
        rate = Decimal(str(quote.rate)) if quote else None
        enriched = []
        for row in data.get("by_currency") or []:
            item = dict(row)
            cur = item.get("currency")
            if cur == "EUR" and rate is not None:
                buckets = item.get("buckets") or {}
                item["brl_equivalent"] = {
                    k: _q2(Decimal(str(v or "0")) * rate) for k, v in buckets.items()
                }
                item["eq_refused"] = False
            elif cur and cur != "BRL":
                item["brl_equivalent"] = None
                item["eq_refused"] = True
            else:
                item["brl_equivalent"] = None
                item["eq_refused"] = False
            enriched.append(item)
        empty = not any(
            Decimal(str((r.get("buckets") or {}).get(k) or "0")) > 0
            for r in enriched
            for k in ("overdue", "m0", "m1", "m2")
        )
        applied, ignored = _ap_filters(date_from, date_to, currency, supplier_id, as_of_ignored)
        return _wrap_widget(
            w,
            display={
                **data,
                "by_currency": enriched,
                "empty": empty,
                "message": "Nada a vencer neste recorte." if empty else None,
                "includes_overdue_chip": "inclui vencidas",
                "quote": None
                if not quote
                else {
                    "rate": str(quote.rate),
                    "source": quote.source,
                    "observed_at": quote.observed_at.isoformat() if quote.observed_at else None,
                    "pair": "EUR/BRL",
                },
            },
            drill="/payables",
            currencies=[r["currency"] for r in enriched],
            applied=applied,
            ignored=ignored,
            time_field="due_date",
        )

    if w.widget_id == "treasury.fx_exposure":
        core = _ap_queue(
            db,
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            supplier_id=supplier_id,
            pending="OPEN_BALANCE",
            limit=1,
        )
        kpis = core.get("kpis") or {}
        quote = treasury_public.fx.get_latest_quote(db, "EUR", "BRL")
        foreign = []
        for row in kpis.get("kpis_by_currency") or []:
            cur = str(row.get("currency") or "")
            if cur == "BRL":
                continue
            amt = Decimal(str(row.get("open_balance") or "0"))
            if amt <= 0:
                continue
            entry: dict[str, Any] = {"currency": cur, "open_balance": _q2(amt)}
            if cur == "EUR" and quote is not None:
                rate = Decimal(str(quote.rate))
                entry["brl_equivalent"] = _q2(amt * rate)
                entry["shock_1pct_brl"] = _q2(amt * rate * Decimal("0.01"))
                entry["eq_refused"] = False
            else:
                entry["brl_equivalent"] = None
                entry["shock_1pct_brl"] = None
                entry["eq_refused"] = True
            foreign.append(entry)
        eur = next((x for x in foreign if x["currency"] == "EUR"), None)
        message = None
        if not foreign:
            message = "Sem saldo em moeda estrangeira."
        elif eur is not None and quote is None:
            message = "Cotação indisponível"
        applied, ignored = _ap_filters(date_from, date_to, currency, supplier_id, [])
        if as_of:
            applied = [*applied, "as_of"]
        return _wrap_widget(
            w,
            display={
                "foreign": foreign,
                "eur": eur,
                "hero_brl": None if not eur else eur.get("brl_equivalent"),
                "shock_1pct_brl": None if not eur else eur.get("shock_1pct_brl"),
                "empty": not foreign,
                "message": message,
                "quote": None
                if not quote
                else {
                    "rate": str(quote.rate),
                    "rate_surface": _q2(Decimal(str(quote.rate))),
                    "rate_full": f"{Decimal(str(quote.rate)):.6f}",
                    "source": quote.source,
                    "observed_at": quote.observed_at.isoformat() if quote.observed_at else None,
                    "stale": quote.stale_after < _now() if quote.stale_after else False,
                    "pair": "EUR/BRL",
                },
            },
            drill="/payables",
            currencies=[r["currency"] for r in foreign],
            applied=applied,
            ignored=ignored,
            time_field="as_of",
        )

    if w.widget_id == "goods.flow":
        segments: list[dict[str, Any]] = []
        if user_can(permissions, is_admin=is_admin, required="orders:read"):
            counts = orders_public.order_status_counts(db)
            segments.append(
                {
                    "key": "confirmed",
                    "label": "Confirmados",
                    "value": int(counts.get("CONFIRMED") or 0),
                    "href": "/orders",
                }
            )
        if user_can(permissions, is_admin=is_admin, required="billing:read"):
            residual = billing_public.qty_to_invoice_residual(db)
            segments.append(
                {
                    "key": "to_invoice",
                    "label": "A faturar",
                    "value": int(residual.get("line_count") or 0),
                    "qty": residual.get("residual_qty"),
                    "href": "/orders",
                }
            )
        if user_can(permissions, is_admin=is_admin, required="logistics:read"):
            sc = logistics_public.shipment_counts_by_status(db)
            in_course = int(sc.get("PLANNED") or 0) + int(sc.get("BOOKED") or 0) + int(sc.get("IN_TRANSIT") or 0)
            segments.append(
                {
                    "key": "shipments",
                    "label": "Embarques em curso",
                    "value": in_course,
                    "href": "/shipments",
                }
            )
        if user_can(permissions, is_admin=is_admin, required="customs:read"):
            pc = customs_public.process_counts_by_status(db)
            segments.append(
                {
                    "key": "customs",
                    "label": "Aduana",
                    "value": int(pc.get("operational_total") or 0),
                    "href": "/customs",
                }
            )
        if user_can(permissions, is_admin=is_admin, required="inventory:read"):
            ov = inventory_public.stock_overview_by_location_type(db)
            segments.append(
                {
                    "key": "stock",
                    "label": "Estoque",
                    "value": int(ov.get("sku_with_balance") or 0),
                    "href": "/inventory/movements",
                }
            )
        ignored = [
            k
            for k, v in (
                ("date_from", date_from),
                ("date_to", date_to),
                ("as_of", as_of),
                ("currency", currency),
                ("supplier_id", supplier_id),
            )
            if v
        ]
        return _wrap_widget(
            w,
            display={
                "segments": segments,
                "disclaimer": "Não é o mesmo conjunto de peças.",
                "not_a_funnel": True,
            },
            drill="/shipments",
            currencies=[],
            applied=[],
            ignored=ignored,
            time_field=None,
        )

    if w.widget_id == "orders.billing_progress":
        data = billing_public.order_billing_progress_by_currency(db)
        ignored = [
            k
            for k, v in (
                ("date_from", date_from),
                ("date_to", date_to),
                ("as_of", as_of),
                ("supplier_id", supplier_id),
            )
            if v
        ]
        applied = []
        rows = data.get("by_currency") or []
        if currency:
            applied.append("currency")
            rows = [r for r in rows if r.get("currency") == currency.upper()]
        empty = not rows or all(
            Decimal(str(r.get("confirmed") or "0")) == 0 and Decimal(str(r.get("invoiced") or "0")) == 0
            for r in rows
        )
        return _wrap_widget(
            w,
            display={
                **data,
                "by_currency": rows,
                "empty": empty,
                "message": "Nenhum pedido confirmado." if empty else None,
            },
            drill="/orders",
            currencies=[r["currency"] for r in rows],
            applied=applied,
            ignored=ignored,
            time_field="order_date",
        )

    if w.widget_id == "costing.operational_published":
        cs = costing_public.operational_summary(db)
        pub = int(cs.get("published_cases") or 0)
        ignored = [
            k
            for k, v in (
                ("date_from", date_from),
                ("date_to", date_to),
                ("currency", currency),
                ("supplier_id", supplier_id),
            )
            if v
        ]
        applied = ["as_of"] if as_of else []
        return _wrap_widget(
            w,
            display={
                "published_cases": pub,
                "included_total_brl": cs.get("included_total_brl") if pub else None,
                "absence": pub == 0,
                "empty": pub == 0,
                "message": "Nenhum custo operacional publicado" if pub == 0 else None,
            },
            drill="/costing",
            currencies=["BRL"] if pub else [],
            applied=applied,
            ignored=ignored,
            time_field="as_of",
        )

    if w.widget_id == "import.situation":
        lines = []
        if user_can(permissions, is_admin=is_admin, required="customs:read"):
            pc = customs_public.process_counts_by_status(db)
            op = int(pc.get("operational_total") or 0)
            lines.append(
                {
                    "key": "processes",
                    "label": "Processos de importação",
                    "value": op,
                    "absence": op == 0,
                    "message": "Nenhuma importação em andamento" if op == 0 else None,
                    "href": "/customs",
                }
            )
        ignored = [k for k, v in (("date_from", date_from), ("date_to", date_to), ("currency", currency), ("supplier_id", supplier_id)) if v]
        applied = ["as_of"] if as_of else []
        return _wrap_widget(
            w,
            display={"lines": lines},
            drill="/customs",
            currencies=[],
            applied=applied,
            ignored=ignored,
            time_field="as_of",
        )

    return _wrap_widget(
        w,
        display={"message": "Widget não implementado"},
        drill="",
        currencies=[],
        applied=[],
        ignored=[],
        time_field=None,
        error="not_implemented",
    )


def snapshot(
    db: Session,
    *,
    permissions: set[str],
    is_admin: bool,
    role: str,
    layout: dict[str, Any],
    view_id: str | None,
    view_name: str | None,
    base_preset: str,
    date_from: date | None,
    date_to: date | None,
    as_of: date | None,
    currency: str | None,
    supplier_id: int | None,
    lane: dict[str, Any],
    period: str = "next_90",
) -> dict[str, Any]:
    wmap = widgets_by_id()
    widgets_out: list[dict[str, Any]] = []
    for slot in layout.get("slots") or []:
        wid = slot.get("widget_id")
        w = wmap.get(wid)
        if not w or wid not in selectable_widget_ids():
            continue
        if w.status == "PARTIAL":
            continue
        try:
            payload = build_widget(
                db,
                w,
                permissions=permissions,
                is_admin=is_admin,
                date_from=date_from,
                date_to=date_to,
                as_of=as_of,
                currency=currency,
                supplier_id=supplier_id,
            )
        except Exception as exc:  # noqa: BLE001
            payload = _wrap_widget(
                w,
                display={"empty_kind": "error", "message": "Não foi possível montar este bloco."},
                drill="",
                currencies=[],
                applied=[],
                ignored=[],
                time_field=None,
                error=type(exc).__name__,
            )
        payload["col"] = slot.get("col", w.col)
        payload["span"] = slot.get("span", w.span)
        payload["size"] = slot.get("size") or w.size
        payload["section"] = slot.get("section") or w.section
        widgets_out.append(payload)

    useful = [x for x in widgets_out if x.get("display", {}).get("empty_kind") != "forbidden"]
    home_ok = bool(useful)
    return {
        "generated_at": _now().isoformat(),
        "view_id": view_id,
        "view_name": view_name,
        "base_preset": base_preset,
        "filters": {
            "period": period,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "as_of": as_of.isoformat() if as_of else None,
            "currency": currency,
            "supplier_id": supplier_id,
        },
        "lane": lane,
        "widgets": widgets_out,
        "home_ok": home_ok,
        "fallback_path": ROLE_FALLBACK_PATH.get(role, "/orders"),
        "default_preset": ROLE_DEFAULT_PRESET.get(role, "executiva"),
    }
