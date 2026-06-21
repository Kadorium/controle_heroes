import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, KpiStat, LoadingState } from "../components";
import { useAuth } from "../context/AuthContext";
import { useDashboardMetrics } from "../hooks/useDashboardMetrics";
import { filterRows, useDashboardFilters } from "../hooks/useDashboardFilters";
import { useDashboardConfig } from "../hooks/useDashboardConfig";
import { DashboardFilters } from "./dashboard/DashboardFilters";
import { ConfigDrawer } from "./dashboard/ConfigDrawer";
import { compactMoney, dominantCurrency } from "./dashboard/format";
import { AlertIcon, CalendarIcon, DollarIcon, PlusIcon, WarehouseIcon } from "./dashboard/icons";
import { InTransitWidget } from "./dashboard/widgets/InTransitWidget";
import {
  CloseToClosureWidget,
  CostVarianceWidget,
  DivergenceWidget,
} from "./dashboard/widgets/ClosureAndDivergenceWidgets";
import { DemoGuideWidget } from "./dashboard/widgets/DemoGuideWidget";
import { LandedCostWidget } from "./dashboard/widgets/LandedCostWidget";
import { NeedsActionWidget } from "./dashboard/widgets/NeedsActionWidget";
import { OverduePaymentsWidget } from "./dashboard/widgets/OverduePaymentsWidget";
import { RecentTimelineWidget } from "./dashboard/widgets/RecentTimelineWidget";
import { StageDistributionWidget } from "./dashboard/widgets/StageDistributionWidget";
import { TopOpenBalancesWidget } from "./dashboard/widgets/TopOpenBalancesWidget";
import { UpcomingPaymentsWidget } from "./dashboard/widgets/UpcomingPaymentsWidget";

const WIDGET_LIST_LIMIT = 8;

function resolveGlobalOpenValue(values: Record<string, string | null>): {
  total: number | null;
  currency: string | null;
} {
  const entries = Object.entries(values);
  if (entries.length === 0) return { total: null, currency: null };
  if (entries.length > 1) return { total: null, currency: null };
  const [cur, val] = entries[0];
  if (val == null) return { total: null, currency: cur };
  return { total: Number(val), currency: cur };
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const metrics = useDashboardMetrics();
  const filters = useDashboardFilters();
  const { config, toggle, isEnabled } = useDashboardConfig(user?.id);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const filtered = useMemo(
    () => filterRows(metrics.rows, filters),
    [metrics.rows, filters.view, filters.modal, filters.period]
  );

  const summary = metrics.summary;
  const openCount = summary?.open_importations_count ?? metrics.totalOpen;
  const openValueGlobal = summary ? resolveGlobalOpenValue(summary.open_value_by_currency) : { total: null, currency: null };
  const currency = openValueGlobal.currency ?? dominantCurrency(filtered.map((r) => r.currency));
  const globalOpenValue = openValueGlobal.total;
  const globalStock = summary?.stocked_units_total ?? null;
  const globalDivergence = summary?.divergence_importations_count ?? null;
  const dueWindow = summary?.payments_due_window_days ?? 7;
  const dueCount = summary?.payments_due_count ?? 0;
  const overdueCount = summary?.payments_overdue_count ?? 0;
  const dueAmountEntries = Object.entries(summary?.payments_due_amount_by_currency ?? {});
  const dueAmount =
    dueAmountEntries.length === 1 ? Number(dueAmountEntries[0][1]) : null;
  const dueCurrency = dueAmountEntries.length === 1 ? dueAmountEntries[0][0] : currency;
  const paymentsDueAvailable = summary?.data_availability.payments_due ?? false;

  if (metrics.loading) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>Painel de controle</h1>
            <div className="page-head__sub">Carregando métricas...</div>
          </div>
        </div>
        <LoadingState label="Carregando painel..." />
      </div>
    );
  }

  const today = new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  });

  const filteredOpenValue = filtered.reduce((acc, r) => {
    if (r.openValue == null) return acc;
    return acc + r.openValue;
  }, 0);
  const hasFilteredNullBalance = filtered.some((r) => r.openValue == null);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Painel de controle</h1>
          <div className="page-head__sub">
            {today} · {openCount} ordens em andamento
          </div>
        </div>
        <div className="page-head__actions">
          <Button variant="ghost" onClick={() => navigate("/importacoes")}>
            <PlusIcon className="ico-inline" /> Nova importação
          </Button>
        </div>
      </div>

      <DashboardFilters
        view={filters.view}
        modal={filters.modal}
        period={filters.period}
        onView={filters.setView}
        onModal={filters.setModal}
        onPeriod={filters.setPeriod}
        onCustomize={() => setDrawerOpen(true)}
      />

      <div className="kpis">
        <KpiStat
          accent="blue"
          label="Valor em aberto"
          icon={<DollarIcon className="ico" />}
          value={
            globalOpenValue != null && globalOpenValue > 0
              ? compactMoney(globalOpenValue, currency)
              : globalOpenValue === 0
                ? compactMoney(0, currency)
                : "—"
          }
          footer={
            <span className="meta">
              {openCount} abertas · global
              {Object.keys(summary?.open_value_by_currency ?? {}).length > 1 ? " · múltiplas moedas" : ""}
              {filtered.length !== metrics.rows.length
                ? ` · filtrado: ${hasFilteredNullBalance ? "—" : compactMoney(filteredOpenValue, currency)}`
                : ""}
            </span>
          }
        />
        <KpiStat
          accent="amber"
          label={`Pagamentos a vencer (${dueWindow}d)`}
          icon={<CalendarIcon className="ico" />}
          value={
            paymentsDueAvailable
              ? dueCount > 0
                ? String(dueCount)
                : "0"
              : "—"
          }
          footer={
            <span className="meta">
              próximos {dueWindow} dias
              {dueAmount != null && dueCount > 0 ? ` · ${compactMoney(dueAmount, dueCurrency)}` : ""}
              {overdueCount > 0 ? ` · ${overdueCount} vencido(s)` : ""}
              {!paymentsDueAvailable ? " · sem vencimentos cadastrados" : ""}
            </span>
          }
        />
        <KpiStat
          accent="green"
          label="Em estoque"
          icon={<WarehouseIcon className="ico" />}
          value={globalStock != null && globalStock > 0 ? globalStock.toLocaleString("pt-BR") : globalStock === 0 ? "0" : "—"}
          unit={globalStock != null && globalStock > 0 ? "un" : undefined}
          footer={
            <span className="meta">
              unidades nacionalizadas · vs. mês {summary?.data_availability.monthly_stock_trend ? "" : "—"}
            </span>
          }
        />
        <KpiStat
          accent="red"
          label="Divergências abertas"
          icon={<AlertIcon className="ico" />}
          value={globalDivergence != null ? globalDivergence : "—"}
          footer={
            <span className="meta">
              importações · {summary?.divergence_reconciliations_count ?? 0} conciliação(ões)
            </span>
          }
        />
      </div>

      <DemoGuideWidget />

      <h2 className="dashboard-section-title">O que resolver hoje?</h2>

      <div className="grid">
        {isEnabled("needs_action") && (
          <NeedsActionWidget rows={metrics.rows.slice(0, WIDGET_LIST_LIMIT)} />
        )}
        {isEnabled("overdue_payments") && <OverduePaymentsWidget rows={metrics.rows} />}
        {isEnabled("payments") && (
          <UpcomingPaymentsWidget rows={metrics.rows.slice(0, WIDGET_LIST_LIMIT)} />
        )}
        {isEnabled("top_balances") && <TopOpenBalancesWidget rows={metrics.rows} />}
        {isEnabled("divergence") && <DivergenceWidget rows={metrics.rows} />}
        {isEnabled("close_ready") && <CloseToClosureWidget rows={metrics.rows} />}
        {isEnabled("in_transit") && (
          <InTransitWidget rows={filtered.slice(0, WIDGET_LIST_LIMIT)} totalCount={filtered.filter((r) => r.inTransit).length} />
        )}
        {isEnabled("cost_variance") && <CostVarianceWidget rows={metrics.rows} />}
        {isEnabled("landed_cost") && (
          <LandedCostWidget rows={filtered.slice(0, WIDGET_LIST_LIMIT)} />
        )}
        {isEnabled("stages") && (
          <StageDistributionWidget rows={filtered} globalStageCounts={metrics.stageCounts} />
        )}
        {isEnabled("timeline") && (
          <RecentTimelineWidget rows={metrics.rows.slice(0, WIDGET_LIST_LIMIT)} />
        )}
      </div>

      <ConfigDrawer
        open={drawerOpen}
        config={config}
        onToggle={toggle}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
