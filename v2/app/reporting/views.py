"""CRUD de visões pessoais do painel."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.reporting.errors import ReportingError
from app.reporting.models import ReportingDashboardView
from app.reporting.registry import (
    LAYOUT_SCHEMA_VERSION,
    default_layout,
    presets_by_id,
    selectable_widget_ids,
    widgets_by_id,
)


def _validate_layout(layout: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(layout, dict):
        raise ReportingError("layout inválido", code="invalid_layout", status_code=400)
    version = int(layout.get("schema_version") or LAYOUT_SCHEMA_VERSION)
    if version != LAYOUT_SCHEMA_VERSION:
        raise ReportingError("schema_version não suportado", code="invalid_schema", status_code=400)
    slots = layout.get("slots")
    if not isinstance(slots, list) or not slots:
        raise ReportingError("layout sem widgets", code="invalid_layout", status_code=400)
    allowed = selectable_widget_ids()
    wmap = widgets_by_id()
    clean = []
    seen: set[str] = set()
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        wid = slot.get("widget_id")
        if wid not in allowed or wid in seen:
            raise ReportingError(f"widget não permitido: {wid}", code="invalid_widget", status_code=400)
        w = wmap[wid]
        if w.status == "NOT_AVAILABLE":
            raise ReportingError(f"widget não disponível: {wid}", code="invalid_widget", status_code=400)
        seen.add(wid)
        col = int(slot.get("col") or w.col)
        span = int(slot.get("span") or w.span)
        if span < 1 or span > 12:
            raise ReportingError("span inválido", code="invalid_layout", status_code=400)
        clean.append({"widget_id": wid, "col": col, "span": span})
    return {"schema_version": LAYOUT_SCHEMA_VERSION, "slots": clean}


def _to_dict(row: ReportingDashboardView) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "base_preset": row.base_preset,
        "layout_json": row.layout_json,
        "filters_json": row.filters_json or {},
        "is_default": row.is_default,
        "schema_version": row.schema_version,
        "version": row.version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "system": False,
    }


def list_views(db: Session, actor_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(ReportingDashboardView)
        .filter(ReportingDashboardView.actor_id == actor_id)
        .order_by(ReportingDashboardView.id.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def get_view(db: Session, actor_id: str, view_id: int) -> ReportingDashboardView:
    row = (
        db.query(ReportingDashboardView)
        .filter(ReportingDashboardView.actor_id == actor_id, ReportingDashboardView.id == view_id)
        .first()
    )
    if not row:
        raise ReportingError("Visão não encontrada", code="view_not_found", status_code=404)
    return row


def _clear_default(db: Session, actor_id: str) -> None:
    db.query(ReportingDashboardView).filter(
        ReportingDashboardView.actor_id == actor_id,
        ReportingDashboardView.is_default.is_(True),
    ).update({"is_default": False}, synchronize_session=False)


def create_view(
    db: Session,
    *,
    actor_id: str,
    name: str,
    base_preset: str,
    layout_json: dict[str, Any] | None,
    filters_json: dict[str, Any] | None,
    is_default: bool,
) -> dict[str, Any]:
    presets = presets_by_id()
    if base_preset not in presets:
        raise ReportingError("preset desconhecido", code="invalid_preset", status_code=400)
    name = (name or "").strip()
    if not name:
        raise ReportingError("nome obrigatório", code="invalid_name", status_code=400)
    layout = _validate_layout(layout_json or default_layout(base_preset))
    if is_default:
        _clear_default(db, actor_id)
    row = ReportingDashboardView(
        actor_id=actor_id,
        name=name[:128],
        base_preset=base_preset,
        layout_json=layout,
        filters_json=filters_json or {},
        is_default=is_default,
        schema_version=LAYOUT_SCHEMA_VERSION,
        version=1,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ReportingError("Já existe uma visão com este nome", code="duplicate_name", status_code=409) from exc
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="reporting_view",
        entity_id=str(row.id),
        action="create",
        details=name,
    )
    return _to_dict(row)


def patch_view(
    db: Session,
    *,
    actor_id: str,
    view_id: int,
    expected_version: int,
    name: str | None = None,
    layout_json: dict[str, Any] | None = None,
    filters_json: dict[str, Any] | None = None,
    is_default: bool | None = None,
) -> dict[str, Any]:
    row = get_view(db, actor_id, view_id)
    if row.version != expected_version:
        raise ReportingError(
            "A visão foi alterada. Recarregue e tente de novo.",
            code="version_conflict",
            status_code=409,
            details={"current_version": row.version},
        )
    if name is not None:
        name = name.strip()
        if not name:
            raise ReportingError("nome obrigatório", code="invalid_name", status_code=400)
        row.name = name[:128]
    if layout_json is not None:
        row.layout_json = _validate_layout(layout_json)
    if filters_json is not None:
        row.filters_json = filters_json
    if is_default is True:
        _clear_default(db, actor_id)
        row.is_default = True
    elif is_default is False:
        row.is_default = False
    row.version = row.version + 1
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="reporting_view",
        entity_id=str(row.id),
        action="update",
        details=row.name,
    )
    return _to_dict(row)


def delete_view(db: Session, *, actor_id: str, view_id: int) -> None:
    row = get_view(db, actor_id, view_id)
    db.delete(row)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="reporting_view",
        entity_id=str(view_id),
        action="delete",
    )


def restore_view(db: Session, *, actor_id: str, view_id: int, expected_version: int) -> dict[str, Any]:
    row = get_view(db, actor_id, view_id)
    if row.version != expected_version:
        raise ReportingError(
            "A visão foi alterada. Recarregue e tente de novo.",
            code="version_conflict",
            status_code=409,
            details={"current_version": row.version},
        )
    row.layout_json = default_layout(row.base_preset)
    row.schema_version = LAYOUT_SCHEMA_VERSION
    row.version = row.version + 1
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="reporting_view",
        entity_id=str(row.id),
        action="restore",
        details=row.base_preset,
    )
    return _to_dict(row)


def default_view_id(db: Session, actor_id: str) -> int | None:
    row = (
        db.query(ReportingDashboardView)
        .filter(
            ReportingDashboardView.actor_id == actor_id,
            ReportingDashboardView.is_default.is_(True),
        )
        .first()
    )
    return row.id if row else None
