"""Contratos HTTP Reporting — painel (OpenAPI tipado)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetricCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    label: str
    unit_label: str
    short_description: str
    definition: str
    owner: str
    permission: str
    time_basis: str | None
    delta_policy: str
    currency_policy: str
    null_policy: str
    status: str
    limitation: str | None
    drill: str
    filters: list[str]
    ai_ready: bool


class WidgetCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    widget_id: str
    label: str
    short_description: str
    metric_ids: list[str]
    permissions: list[str]
    kind: str
    status: str
    limitation: str | None
    col: int
    span: int
    section: str = "detail"
    size: str = "panel"
    cta_label: str | None = None
    drill: str | None = None


class PresetOut(BaseModel):
    preset_id: str
    label: str
    widget_ids: list[str]
    hidden: bool = False
    filters: list[str] = Field(default_factory=list)


class MetricCatalogOut(BaseModel):
    generated_at: str
    metrics: list[MetricCatalogItem]
    widgets: list[WidgetCatalogItem]
    presets: list[PresetOut]
    attention_limit_default: int
    layout_schema_version: int


class DashboardFiltersOut(BaseModel):
    period: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    as_of: str | None = None
    currency: str | None = None
    supplier_id: int | None = None


class DashboardWidgetOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    widget_id: str
    metric_id: str
    label: str
    short_description: str
    kind: str
    status: str
    limitation: str | None = None
    display: dict[str, Any]
    drill: str
    currencies: list[str] = Field(default_factory=list)
    filters_applied: list[str] = Field(default_factory=list)
    filters_ignored: list[str] = Field(default_factory=list)
    time_field: str | None = None
    error: str | None = None
    col: int | None = None
    span: int | None = None
    section: str | None = None
    size: str | None = None
    cta_label: str | None = None


class DashboardLaneOut(BaseModel):
    lane: str
    includes_trial_mass: bool
    note: str | None = None


class DashboardSnapshotOut(BaseModel):
    generated_at: str
    view_id: str | None = None
    view_name: str | None = None
    base_preset: str
    filters: DashboardFiltersOut
    lane: DashboardLaneOut
    widgets: list[DashboardWidgetOut]
    home_ok: bool
    fallback_path: str
    default_preset: str


class ViewOut(BaseModel):
    id: int
    name: str
    base_preset: str
    layout_json: dict[str, Any]
    filters_json: dict[str, Any]
    is_default: bool
    schema_version: int
    version: int
    created_at: str | None = None
    updated_at: str | None = None
    system: bool = False


class ViewCreateIn(BaseModel):
    name: str
    base_preset: str
    layout_json: dict[str, Any] | None = None
    filters_json: dict[str, Any] | None = None
    is_default: bool = False


class ViewPatchIn(BaseModel):
    version: int
    name: str | None = None
    layout_json: dict[str, Any] | None = None
    filters_json: dict[str, Any] | None = None
    is_default: bool | None = None


class ViewRestoreIn(BaseModel):
    version: int


class CommercialAvailabilityOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    facets: dict[str, Any]
    totals: dict[str, Any]
    by_regime: list[dict[str, Any]] = Field(default_factory=list)
    by_category: list[dict[str, Any]] = Field(default_factory=list)
    footer: dict[str, Any] | None = None
    empty: bool = False
    state: str = "ok"
