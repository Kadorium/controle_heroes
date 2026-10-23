import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  Button,
  DateInput,
  DetailDrawer,
  ExplainerDialog,
  FilterBar,
  FormField,
  Notice,
  PageHeader,
  SelectField,
  Skeleton,
  TextInput,
} from "../../ui";
import { formatUpdatedAgo, formatRate, formatDateTime, formatDateOnly } from "../../ui/format";
import { ExecutiveOverview } from "./ExecutiveOverview";
import { isSystemExecutive } from "./executiveDisplay";
import { useListReturn } from "../../navigation/useListReturn";
import { DashboardWidgetCard } from "./DashboardWidgets";
import {
  createView,
  deleteView,
  fetchDashboard,
  fetchMetricCatalog,
  fetchViews,
  patchView,
  restoreView,
  type DashboardSnapshot,
  type DashboardView,
  type DashboardWidget,
  type MetricCatalog,
} from "./dashboardApi";

type Props = { user: User };

const PERIOD_OPTIONS = [
  { value: "next_90", label: "Próximos 90 dias" },
  { value: "this_month", label: "Este mês" },
  { value: "next_30", label: "Próximos 30 dias" },
  { value: "custom", label: "Personalizado" },
];

const VIEW_COPY: Record<string, string> = {
  executiva: "Quanto pagar, o câmbio, a mercadoria e o que decidir.",
  comercial: "O que há para oferecer, o que está chegando e o que pede atenção.",
  controle: "Exceções da operação, por gravidade e módulo.",
};

const VIEW_TITLE: Record<string, string> = {
  executiva: "Executiva",
  comercial: "Comercial",
  controle: "Controle",
  financeiro: "Financeiro",
  compras: "Compras",
  operacao: "Operação",
  aduana: "Aduana",
  estoque: "Estoque",
  produtos: "Produtos",
  custos: "Custos",
};

function visiblePresets(catalog: MetricCatalog | null, current: string) {
  const fromCat = (catalog?.presets ?? []).filter((p) => !p.hidden || p.preset_id === current);
  if (fromCat.length) return fromCat.map((p) => ({ value: p.preset_id, label: p.label }));
  return [
    { value: "executiva", label: "Executiva" },
    { value: "comercial", label: "Comercial" },
    { value: "controle", label: "Controle" },
  ];
}

function presetFilters(catalog: MetricCatalog | null, preset: string): string[] {
  return catalog?.presets.find((p) => p.preset_id === preset)?.filters ?? [];
}

function readParam(params: URLSearchParams, key: string) {
  return params.get(key) ?? "";
}

export function DashboardPage({ user: _user }: Props) {
  const [params, setParams] = useSearchParams();
  useListReturn("/dashboard");
  const view = readParam(params, "view");
  const periodParam = readParam(params, "period");
  const dateFrom = readParam(params, "date_from");
  const dateTo = readParam(params, "date_to");
  const asOf = readParam(params, "as_of");
  const currency = readParam(params, "currency");
  const supplierId = readParam(params, "supplier_id");
  const period = periodParam || (dateFrom || dateTo || asOf ? "custom" : "next_90");
  const isCustom = period === "custom";

  const [snap, setSnap] = useState<DashboardSnapshot | null>(null);
  const [catalog, setCatalog] = useState<MetricCatalog | null>(null);
  const [views, setViews] = useState<DashboardView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [explainer, setExplainer] = useState<DashboardWidget | null>(null);
  const [inboxAll, setInboxAll] = useState<DashboardWidget | null>(null);
  const [customize, setCustomize] = useState(false);
  const [copyName, setCopyName] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const request = useRef<AbortController | null>(null);
  const previousQuery = useRef("");

  const setFilter = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(params);
      if (!value) next.delete(key);
      else next.set(key, value);
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    const query = JSON.stringify([view, period, isCustom, dateFrom, dateTo, asOf, currency, supplierId]);
    if (previousQuery.current !== query) setSnap(null);
    previousQuery.current = query;
    setLoading(true);
    setError(null);
    setRefreshKey(n => n + 1);
    try {
      const data = await fetchDashboard({
        view: view || undefined,
        period,
        date_from: isCustom ? dateFrom || undefined : undefined,
        date_to: isCustom ? dateTo || undefined : undefined,
        as_of: isCustom ? asOf || undefined : undefined,
        currency: currency || undefined,
        supplier_id: supplierId || undefined,
      }, controller.signal);
      if (!controller.signal.aborted) setSnap(data);
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Falha ao carregar o painel");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [view, period, isCustom, dateFrom, dateTo, asOf, currency, supplierId]);

  useEffect(() => {
    void load();
    return () => request.current?.abort();
  }, [load]);

  useEffect(() => {
    void fetchMetricCatalog().then(setCatalog).catch(() => undefined);
    void fetchViews().then(setViews).catch(() => undefined);
  }, []);

  const mixed = (snap?.widgets ?? []).some((w) => Boolean(w.display?.mixed_currency));
  const explainerMetric = catalog?.metrics.find((m) => m.metric_id === explainer?.metric_id);
  const basePreset = snap?.base_preset ?? (view || "executiva");
  const shownFilters = presetFilters(catalog, basePreset);
  const showPeriod = shownFilters.includes("period");
  const showCurrency = shownFilters.includes("currency") && (mixed || !!currency);
  const executive = isSystemExecutive(snap);
  const showSupplier = shownFilters.includes("supplier_id");
  const chips = useMemo(() => {
    const out: { id: string; label: string; onRemove: () => void }[] = [];
    if (showPeriod && period && period !== "next_90") {
      const lab = PERIOD_OPTIONS.find((p) => p.value === period)?.label ?? period;
      out.push({ id: "period", label: lab, onRemove: () => setFilter("period", "") });
    }
    if (showPeriod && isCustom && dateFrom) out.push({ id: "date_from", label: `De ${dateFrom}`, onRemove: () => setFilter("date_from", "") });
    if (showPeriod && isCustom && dateTo) out.push({ id: "date_to", label: `Até ${dateTo}`, onRemove: () => setFilter("date_to", "") });
    if (showPeriod && isCustom && asOf) out.push({ id: "as_of", label: `Na data ${asOf}`, onRemove: () => setFilter("as_of", "") });
    if (currency) out.push({ id: "currency", label: currency, onRemove: () => setFilter("currency", "") });
    if (supplierId) out.push({ id: "supplier_id", label: `Fornecedor ${supplierId}`, onRemove: () => setFilter("supplier_id", "") });
    return out;
  }, [showPeriod, showCurrency, showSupplier, period, isCustom, dateFrom, dateTo, asOf, currency, supplierId, setFilter]);
  const subtitle =
    (executive ? "Compromissos financeiros, operação e próxima ação." : VIEW_COPY[basePreset] ?? "Resumo para decidir e ir à fila.") +
    (snap && !error && !loading && !executive ? ` ${formatUpdatedAgo(snap.generated_at)}` : "");

  async function saveCopy() {
    const base = snap?.base_preset || "executiva";
    const created = await createView({
      name: copyName.trim() || `${snap?.view_name ?? "Visão"} (cópia)`,
      base_preset: base,
      layout_json: {
        schema_version: 1,
        slots: (snap?.widgets ?? []).map((w, i) => ({
          widget_id: w.widget_id,
          col: w.col ?? i + 1,
          span: w.span ?? 4,
        })),
      },
      is_default: false,
    });
    setViews((prev) => [...prev, created]);
    setFilter("view", String(created.id));
    setCustomize(false);
  }

  const personal = views.find((v) => String(v.id) === view);

  async function move(idx: number, dir: -1 | 1) {
    if (!personal) return;
    const slots = [...personal.layout_json.slots];
    const j = idx + dir;
    if (j < 0 || j >= slots.length) return;
    const tmp = slots[idx];
    slots[idx] = slots[j];
    slots[j] = tmp;
    const updated = await patchView(personal.id, { version: personal.version, layout_json: { ...personal.layout_json, slots } });
    setViews((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    await load();
  }

  async function hide(idx: number) {
    if (!personal) return;
    const slots = personal.layout_json.slots.filter((_, i) => i !== idx);
    const updated = await patchView(personal.id, { version: personal.version, layout_json: { ...personal.layout_json, slots } });
    setViews((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    await load();
  }

  if (!loading && snap && !snap.home_ok) {
    return <Navigate to={snap.fallback_path || "/orders"} replace />;
  }

  return (
    <div className={`dashboard-page${executive ? " dashboard-page--executive" : ""}`} data-testid="dashboard-page" data-demo-ready={!loading && !!snap && !error ? "true" : "false"}>
      <PageHeader
        title={executive ? "Painel executivo" : snap?.view_name ?? VIEW_TITLE[view] ?? "Painel"}
        subtitle={subtitle}
        actions={
          <>
            <Button type="button" variant="secondary" onClick={() => void load()}>
              Atualizar
            </Button>
            <Button type="button" variant="ghost" onClick={() => setCustomize(true)}>
              Personalizar
            </Button>
          </>
        }
      />
      <FilterBar
        moreAlways
        activeFilters={chips}
        onClearAll={() => {
          const next = new URLSearchParams(params);
          ["period", "date_from", "date_to", "as_of", "currency", "supplier_id"].forEach((k) => next.delete(k));
          setParams(next, { replace: true });
        }}
        primary={
          <>
            <FormField label="Visão">
              <SelectField
                value={view}
                onChange={(e) => setFilter("view", e.target.value)}
                options={[
                  { value: "", label: "Minha visão" },
                  ...visiblePresets(catalog, view || basePreset),
                  ...views.map((v) => ({ value: String(v.id), label: v.name })),
                ]}
              />
            </FormField>
            {showPeriod ? (
              <>
                <FormField label={executive ? "Janela financeira" : "Período"}>
                  <SelectField
                    value={period}
                    onChange={(e) => {
                      const next = new URLSearchParams(params);
                      const value = e.target.value;
                      if (!value || value === "next_90") next.delete("period");
                      else next.set("period", value);
                      if (value !== "custom") {
                        next.delete("date_from");
                        next.delete("date_to");
                        next.delete("as_of");
                      }
                      setParams(next, { replace: true });
                    }}
                    options={PERIOD_OPTIONS}
                  />
                </FormField>
                {isCustom ? (
                  <>
                    <FormField label="De">
                      <DateInput value={dateFrom} onChange={(e) => setFilter("date_from", e.target.value)} />
                    </FormField>
                    <FormField label="Até">
                      <DateInput value={dateTo} onChange={(e) => setFilter("date_to", e.target.value)} />
                    </FormField>
                    <FormField label="Na data">
                      <DateInput value={asOf} onChange={(e) => setFilter("as_of", e.target.value)} />
                    </FormField>
                  </>
                ) : null}
              </>
            ) : null}
            {showCurrency ? (
              <FormField label="Moeda">
                <TextInput value={currency} onChange={(e) => setFilter("currency", e.target.value.toUpperCase())} />
              </FormField>
            ) : null}
          </>
        }
        secondary={
          showSupplier ? (
            <FormField label="Fornecedor (id)">
              <TextInput value={supplierId} onChange={(e) => setFilter("supplier_id", e.target.value)} />
            </FormField>
          ) : null
        }
      />
      {executive && <div className="exec-context">
        {snap?.lane.includes_trial_mass && <span>Ambiente de demonstração / teste</span>}
        <span>{loading ? "Consultando…" : error ? "Leitura não atualizada" : "Leitura"}{snap ? ` · ${formatDateTime(snap.generated_at)}` : ""}</span>
        <details><summary>Escopo dos filtros</summary><p>Janela financeira: {snap?.filters.date_from ? `de ${formatDateOnly(snap.filters.date_from)} ` : ""}{snap?.filters.date_to ? `até ${formatDateOnly(snap.filters.date_to)}` : "sem limite de data"}. Os blocos indicam seu recorte próprio.</p><p>Vencidos e saldo em moeda estrangeira aplicam o recorte de vencimentos. Compromissos e agenda usam meses civis e o limite Até, não o limite De. Pedidos e posição operacional mostram a posição atual. Câmbio usa a última referência e os dias observados, não a janela financeira. “Na data” não reconstrói uma posição histórica completa.</p><p>Moeda/fornecedor só se aplicam aos blocos que oferecem esse filtro; detalhes em ⓘ. Links “Abrir fila completa” não transportam automaticamente estes filtros.</p></details>
      </div>}
      {!executive && snap?.lane.includes_trial_mass ? (
        <Notice>Ambiente de teste. Os números podem incluir massa de ensaio.</Notice>
      ) : null}
      {error ? <Notice tone="danger">Não foi possível atualizar o painel. {snap ? `Última leitura: ${formatDateTime(snap.generated_at)}. Os valores abaixo não foram atualizados.` : "Nenhum resultado confirmado."} <Button variant="ghost" onClick={() => void load()}>Tentar novamente</Button></Notice> : null}
      {loading ? (
        <div className="dash-grid" data-testid="dash-skeleton">
          <div className="dash-slot dash-slot--stat"><Skeleton kind="kpi" /></div>
          <div className="dash-slot dash-slot--stat"><Skeleton kind="kpi" /></div>
          <div className="dash-slot dash-slot--stat"><Skeleton kind="kpi" /></div>
          <div className="dash-slot dash-slot--stat"><Skeleton kind="kpi" /></div>
          <div className="dash-slot dash-slot--panel"><Skeleton kind="block" /></div>
          <div className="dash-slot dash-slot--panel"><Skeleton kind="block" /></div>
          <div className="dash-slot dash-slot--wide"><Skeleton kind="inbox" /></div>
        </div>
      ) : executive && snap ? <ExecutiveOverview snapshot={snap} refreshKey={refreshKey} onExplain={setExplainer} onSeeAll={setInboxAll} /> : (
        <div className="dash-grid" data-demo-summary>
          {(snap?.widgets ?? []).map((w) => (
            <div key={w.widget_id} className={`dash-slot dash-slot--${w.size || "panel"}`}>
              <DashboardWidgetCard
                widget={w}
                onExplain={setExplainer}
                onSeeAll={setInboxAll}
                compactMoney
              />
            </div>
          ))}
        </div>
      )}

      <ExplainerDialog
        open={!!explainer}
        title={explainer?.label ?? ""}
        description={explainerMetric?.short_description || explainer?.short_description || ""}
        unitLabel={explainerMetric?.unit_label}
        limitation={explainer?.limitation}
        onClose={() => setExplainer(null)}
      >
        {explainer?.widget_id === "treasury.fx_exposure"
          ? (() => {
              const q = explainer.display.quote as Record<string, unknown> | undefined;
              if (!q) return null;
              return (
                <p className="muted">
                  Taxa {formatRate(String(q.rate_full ?? q.rate), 6)} · fonte {String(q.source ?? "—")}
                  {q.observed_at ? ` · ${String(q.observed_at)}` : ""}
                </p>
              );
            })()
          : null}
      </ExplainerDialog>

      <DetailDrawer open={!!inboxAll} title="Todas as pendências" onClose={() => setInboxAll(null)}>
        {(() => {
          const all = (inboxAll?.display.all_items as Array<Record<string, unknown>> | undefined) ?? [];
          return (
            <ul className="dash-inbox">
              {all.map((it, idx) => (
                <li key={`${it.item_type}-${idx}`}>
                  {it.href ? <Link to={String(it.href)}>{String(it.title)}</Link> : String(it.title)}
                  <span className="muted"> {String(it.reason)}</span>
                </li>
              ))}
            </ul>
          );
        })()}
      </DetailDrawer>

      <DetailDrawer open={customize} title="Personalizar visão" onClose={() => setCustomize(false)}>
        <FormField label="Nome da cópia">
          <TextInput value={copyName} onChange={(e) => setCopyName(e.target.value)} />
        </FormField>
        <Button type="button" onClick={() => void saveCopy()}>
          Duplicar visão atual
        </Button>
        {personal ? (
          <>
            <h3>Ordem (setas)</h3>
            <ol className="dash-customize-list">
              {personal.layout_json.slots.map((slot, idx) => (
                <li key={slot.widget_id}>
                  <span>
                    {snap?.widgets.find((w) => w.widget_id === slot.widget_id)?.label
                      ?? catalog?.widgets.find((w) => w.widget_id === slot.widget_id)?.label
                      ?? "Bloco"}
                  </span>
                  <Button type="button" variant="ghost" onClick={() => void move(idx, -1)} aria-label="Subir">
                    ↑
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => void move(idx, 1)} aria-label="Descer">
                    ↓
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => void hide(idx)}>
                    Ocultar
                  </Button>
                </li>
              ))}
            </ol>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void restoreView(personal.id, personal.version).then((u) => {
                setViews((prev) => prev.map((v) => (v.id === u.id ? u : v)));
                return load();
              })}
            >
              Restaurar preset
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void patchView(personal.id, { version: personal.version, is_default: true }).then((u) => {
                setViews((prev) => prev.map((v) => ({ ...v, is_default: v.id === u.id })));
              })}
            >
              Definir como padrão
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={() => void deleteView(personal.id).then(() => {
                setViews((prev) => prev.filter((v) => v.id !== personal.id));
                setFilter("view", personal.base_preset);
              })}
            >
              Excluir visão pessoal
            </Button>
          </>
        ) : (
          <p className="muted">Para reordenar, duplique o preset. Presets de sistema não se editam.</p>
        )}
      </DetailDrawer>
    </div>
  );
}
