"""Exceções acionáveis — merge read-only no Reporting a partir dos donos."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.catalog import public as catalog_public
from app.costing import public as costing_public
from app.customs import public as customs_public
from app.ingestion import public as ingestion_public
from app.orders import public as orders_public
from app.treasury import public as treasury_public

SEV_RANK = {"blocker": 0, "overdue": 1, "due_today": 2, "warning": 3}


def _from_payables(db: Session, *, limit: int) -> list[dict[str, Any]]:
    queue = billing_public.payables_queue(db, pending="OVERDUE", limit=limit, offset=0)
    items = []
    for row in queue.get("items") or []:
        items.append(
            {
                "kind": "ap_overdue",
                "severity": "overdue",
                "title": row.get("supplier_name") or row.get("invoice_number") or "Obrigação vencida",
                "reason": "Obrigação vencida",
                "entity_id": row.get("id"),
                "href": f"/payables?payable_id={row.get('id')}",
                "since": row.get("due_date"),
                "module": "billing",
            }
        )
    return items


def collect(
    db: Session,
    *,
    permissions: set[str],
    is_admin: bool,
    limit: int = 40,
    severity: str | None = None,
    module: str | None = None,
) -> dict[str, Any]:
    buckets: list[list[dict[str, Any]]] = []
    errors: list[str] = []

    def take(perm: str, fn, *a, **kw):
        if not is_admin and perm not in permissions:
            return
        try:
            buckets.append(fn(*a, **kw) or [])
        except Exception as exc:  # noqa: BLE001 — isolamento por dono
            errors.append(f"{perm}: {exc.__class__.__name__}")

    take("billing:read", _from_payables, db, limit=limit)
    take("catalog:read", catalog_public.exceptions, db, limit=limit)
    take("ingestion:read", ingestion_public.exceptions, db, limit=limit)
    take("ingestion:read", ingestion_public.review_exceptions, db, limit=limit)
    take("customs:read", customs_public.blocked_exceptions, db, limit=limit)
    take("costing:read", costing_public.publish_blockers, db, limit=limit)
    take("treasury:read", treasury_public.unallocated_registered_list, db, limit=limit)
    take("orders:read", orders_public.unpriced_exceptions, db, limit=limit)

    items: list[dict[str, Any]] = []
    for group in buckets:
        items.extend(group)
    if severity:
        items = [i for i in items if i.get("severity") == severity]
    if module:
        items = [i for i in items if i.get("module") == module]
    items.sort(key=lambda i: (SEV_RANK.get(str(i.get("severity")), 9), i.get("since") or ""))
    items = items[:limit]

    by_severity: dict[str, int] = {}
    by_module: dict[str, int] = {}
    for i in items:
        sev = str(i.get("severity") or "warning")
        mod = str(i.get("module") or "other")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_module[mod] = by_module.get(mod, 0) + 1

    return {
        "items": items,
        "total_count": len(items),
        "by_severity": [{"severity": k, "count": v} for k, v in sorted(by_severity.items(), key=lambda x: SEV_RANK.get(x[0], 9))],
        "by_module": [{"module": k, "count": v} for k, v in sorted(by_module.items())],
        "errors": errors,
        "empty": len(items) == 0,
        "empty_copy": "Nada precisa da sua decisão agora.",
        "state": "empty" if not items else "ok",
    }
