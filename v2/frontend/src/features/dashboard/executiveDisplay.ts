import type { DashboardSnapshot, DashboardWidget } from "./dashboardApi";

// Presentation only: no totals, balances or currency conversion are calculated here.
export type Fields = Record<string, unknown>;
export const fields = (value: unknown): Fields => value && typeof value === "object" && !Array.isArray(value) ? value as Fields : {};
export const rows = (value: unknown): Fields[] => Array.isArray(value) ? value.filter(v => v && typeof v === "object") as Fields[] : [];
export const text = (value: unknown, fallback = "—") => value == null || value === "" ? fallback : String(value);
export const amount = (value: unknown) => typeof value === "string" || typeof value === "number" ? value : null;
export const isSystemExecutive = (snapshot: DashboardSnapshot | null) => snapshot?.base_preset === "executiva" && snapshot.view_id === "executiva";
export const hasFailure = (w: DashboardWidget) => Boolean(w.error) || ["error", "unavailable", "forbidden"].includes(text(w.display.state));
export function monthRange(display: Fields) {
  const labels = fields(display.labels);
  return labels.m0 && labels.m2 ? `${labels.m0}–${labels.m2}` : "meses civis consultados";
}
export function incomplete(display: Fields) {
  return ["errors", "unavailable", "forbidden"].some(k => Array.isArray(display[k]) && (display[k] as unknown[]).length > 0);
}
export const moduleLabel: Record<string, string> = { customs: "Aduana", billing: "Contas a pagar", catalog: "Catálogo", costing: "Custos", treasury: "Tesouro", orders: "Pedidos", inventory: "Estoque", ingestion: "Ingestão" };
export const severityLabel: Record<string, string> = { blocker: "Bloqueio", overdue: "Vencido", due_today: "Vence hoje", warning: "Atenção" };
