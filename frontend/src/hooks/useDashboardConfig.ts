import { useCallback, useEffect, useState } from "react";

export type WidgetId =
  | "in_transit"
  | "payments"
  | "overdue_payments"
  | "top_balances"
  | "divergence"
  | "close_ready"
  | "cost_variance"
  | "landed_cost"
  | "needs_action"
  | "stages"
  | "timeline";

export interface WidgetMeta {
  id: WidgetId;
  name: string;
  description: string;
  defaultOn: boolean;
}

// Ordem padrão dos widgets no grid (posição fixa nesta fase — sem drag-and-drop).
export const WIDGET_REGISTRY: WidgetMeta[] = [
  { id: "in_transit", name: "Em trânsito", description: "Embarques a caminho", defaultOn: true },
  { id: "payments", name: "Próximos pagamentos", description: "Saldos e vencimentos", defaultOn: true },
  { id: "overdue_payments", name: "Pagamentos vencidos", description: "Planejados em atraso", defaultOn: true },
  { id: "top_balances", name: "Maiores saldos", description: "Top 5 saldos em aberto", defaultOn: true },
  { id: "needs_action", name: "Precisa de ação", description: "Pendências bloqueantes", defaultOn: true },
  { id: "divergence", name: "Com divergência", description: "Conciliações abertas", defaultOn: true },
  { id: "close_ready", name: "Próximas de fechamento", description: "Checklist OK", defaultOn: false },
  { id: "cost_variance", name: "Variações de custo", description: "Landed cost est. vs real", defaultOn: false },
  { id: "landed_cost", name: "Landed cost", description: "Estimado vs realizado", defaultOn: true },
  { id: "stages", name: "Importações por etapa", description: "Distribuição no funil", defaultOn: true },
  { id: "timeline", name: "Timeline recente", description: "Últimos eventos legíveis", defaultOn: true },
];

type ConfigMap = Record<WidgetId, boolean>;

function defaults(): ConfigMap {
  return WIDGET_REGISTRY.reduce((acc, w) => {
    acc[w.id] = w.defaultOn;
    return acc;
  }, {} as ConfigMap);
}

// localStorage SÓ para preferência de layout do dashboard (não dados de negócio).
function storageKey(userId: number | string) {
  return `epic.dash.${userId}`;
}

function readConfig(userId: number | string): ConfigMap {
  const base = defaults();
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return base;
    const parsed = JSON.parse(raw) as Partial<ConfigMap>;
    WIDGET_REGISTRY.forEach((w) => {
      if (typeof parsed[w.id] === "boolean") base[w.id] = parsed[w.id] as boolean;
    });
  } catch {
    // Preferência corrompida → usa padrão.
  }
  return base;
}

export function useDashboardConfig(userId: number | string | undefined) {
  const [config, setConfig] = useState<ConfigMap>(() =>
    userId == null ? defaults() : readConfig(userId)
  );

  useEffect(() => {
    if (userId == null) return;
    setConfig(readConfig(userId));
  }, [userId]);

  const toggle = useCallback(
    (id: WidgetId) => {
      setConfig((prev) => {
        const next = { ...prev, [id]: !prev[id] };
        if (userId != null) {
          try {
            localStorage.setItem(storageKey(userId), JSON.stringify(next));
          } catch {
            // Ignora falha de persistência (modo privado etc.).
          }
        }
        return next;
      });
    },
    [userId]
  );

  const isEnabled = useCallback((id: WidgetId) => config[id], [config]);

  return { config, toggle, isEnabled };
}
