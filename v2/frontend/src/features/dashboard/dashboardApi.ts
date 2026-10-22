/** API do painel gerencial — só apresenta snapshot. */

export type DashboardFilters = {
  view?: string;
  period?: string;
  date_from?: string;
  date_to?: string;
  as_of?: string;
  currency?: string;
  supplier_id?: string;
};

export type DashboardWidget = {
  widget_id: string;
  metric_id: string;
  label: string;
  short_description: string;
  kind: string;
  status: string;
  limitation?: string | null;
  display: Record<string, unknown>;
  drill: string;
  currencies: string[];
  filters_applied: string[];
  filters_ignored: string[];
  time_field?: string | null;
  error?: string | null;
  col?: number | null;
  span?: number | null;
  section?: string | null;
  size?: string | null;
  cta_label?: string | null;
};

export type DashboardSnapshot = {
  generated_at: string;
  view_id: string | null;
  view_name: string | null;
  base_preset: string;
  filters: {
    period?: string | null;
    date_from?: string | null;
    date_to?: string | null;
    as_of?: string | null;
    currency?: string | null;
    supplier_id?: number | null;
  };
  lane: { lane: string; includes_trial_mass: boolean; note?: string | null };
  widgets: DashboardWidget[];
  home_ok: boolean;
  fallback_path: string;
  default_preset: string;
};

export type MetricCatalog = {
  generated_at: string;
  metrics: Array<{
    metric_id: string;
    label: string;
    unit_label: string;
    short_description: string;
    limitation?: string | null;
  }>;
  widgets: Array<{
    widget_id: string;
    label: string;
    short_description: string;
    status: string;
    limitation?: string | null;
    col: number;
    span: number;
    section?: string;
    size?: string;
    cta_label?: string | null;
    drill?: string | null;
  }>;
  presets: Array<{
    preset_id: string;
    label: string;
    widget_ids: string[];
    hidden?: boolean;
    filters?: string[];
  }>;
};

export type DashboardView = {
  id: number;
  name: string;
  base_preset: string;
  layout_json: { schema_version: number; slots: Array<{ widget_id: string; col: number; span: number }> };
  filters_json: Record<string, unknown>;
  is_default: boolean;
  schema_version: number;
  version: number;
};

function qs(params: Record<string, string | number | undefined | null>) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as T;
}

export async function fetchDashboard(params: DashboardFilters) {
  return parse<DashboardSnapshot>(
    await fetch(`/api/reporting/dashboard${qs(params)}`, { credentials: "include" }),
  );
}

export async function fetchMetricCatalog() {
  return parse<MetricCatalog>(await fetch("/api/reporting/metric-catalog", { credentials: "include" }));
}

export async function fetchViews() {
  return parse<DashboardView[]>(await fetch("/api/reporting/views", { credentials: "include" }));
}

export async function createView(body: {
  name: string;
  base_preset: string;
  layout_json?: DashboardView["layout_json"];
  is_default?: boolean;
}) {
  return parse<DashboardView>(
    await fetch("/api/reporting/views", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function patchView(
  id: number,
  body: { version: number; name?: string; layout_json?: DashboardView["layout_json"]; is_default?: boolean },
) {
  return parse<DashboardView>(
    await fetch(`/api/reporting/views/${id}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function deleteView(id: number) {
  return parse<{ ok: boolean }>(
    await fetch(`/api/reporting/views/${id}`, { method: "DELETE", credentials: "include" }),
  );
}

export async function restoreView(id: number, version: number) {
  return parse<DashboardView>(
    await fetch(`/api/reporting/views/${id}/restore`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    }),
  );
}

export type CommercialAvailability = {
  rows: Array<{
    product_id: number;
    sku: string;
    commercial_name: string;
    category: string | null;
    product_type: string | null;
    available_qty: string;
    bonded_qty: string;
    quarantine_qty: string;
    cleared_not_received_qty: string;
    incoming_qty: string | null;
    next_eta: string | null;
    needs_attention: boolean;
    href: string;
    stock_href: string;
  }>;
  total: number;
  limit: number;
  offset: number;
  facets: Record<string, unknown>;
  totals: Record<string, unknown>;
  by_regime: Array<Record<string, unknown>>;
  by_category: Array<Record<string, unknown>>;
  footer?: { label: string; qty: string } | null;
  empty: boolean;
  state: string;
};

export async function fetchCommercialAvailability(params: {
  q?: string;
  category?: string;
  product_type?: string;
  status?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}) {
  return parse<CommercialAvailability>(
    await fetch(`/api/reporting/commercial-availability${qs(params)}`, { credentials: "include" }),
  );
}
