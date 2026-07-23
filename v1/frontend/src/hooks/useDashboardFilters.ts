import { useMemo, useState } from "react";
import type { DashboardRow } from "./useDashboardMetrics";

export type DashboardView =
  | "all"
  | "in_transit"
  | "in_stock"
  | "awaiting_payment"
  | "divergent";

export type ModalFilter = "all" | "OCEAN" | "AIR";
export type PeriodFilter = "7d" | "30d" | "quarter";

export const VIEW_OPTIONS: Array<{ id: DashboardView; label: string }> = [
  { id: "all", label: "Tudo" },
  { id: "in_transit", label: "Em trânsito" },
  { id: "in_stock", label: "Em estoque" },
  { id: "awaiting_payment", label: "Aguardando pagamento" },
  { id: "divergent", label: "Com divergência" },
];

export const MODAL_OPTIONS: Array<{ id: ModalFilter; label: string }> = [
  { id: "OCEAN", label: "Marítimo" },
  { id: "all", label: "Todos" },
  { id: "AIR", label: "Aéreo" },
];

export const PERIOD_OPTIONS: Array<{ id: PeriodFilter; label: string; days: number }> = [
  { id: "7d", label: "7 dias", days: 7 },
  { id: "30d", label: "30 dias", days: 30 },
  { id: "quarter", label: "Trimestre", days: 90 },
];

export interface DashboardFiltersState {
  view: DashboardView;
  modal: ModalFilter;
  period: PeriodFilter;
}

export function useDashboardFilters() {
  const [view, setView] = useState<DashboardView>("all");
  const [modal, setModal] = useState<ModalFilter>("all");
  const [period, setPeriod] = useState<PeriodFilter>("30d");

  return { view, setView, modal, setModal, period, setPeriod };
}

export function filterRows(
  rows: DashboardRow[],
  filters: DashboardFiltersState
): DashboardRow[] {
  const days = PERIOD_OPTIONS.find((p) => p.id === filters.period)?.days ?? 30;
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;

  return rows.filter((row) => {
    // Período (por created_at).
    if (new Date(row.createdAt).getTime() < cutoff) return false;

    // Modal.
    if (filters.modal !== "all" && row.modal !== filters.modal) return false;

    // Visão rápida.
    switch (filters.view) {
      case "in_transit":
        return row.inTransit;
      case "in_stock":
        return row.stockedQty > 0;
      case "awaiting_payment":
        return row.pendingPayments.length > 0;
      case "divergent":
        return row.hasDivergence;
      default:
        return true;
    }
  });
}
