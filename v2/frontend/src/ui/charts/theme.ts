/** Cores de gráfico a partir dos tokens CSS — sem hex no componente. */

function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function chartColors() {
  return {
    overdue: cssVar("--color-data-overdue", "#b42318"),
    today: cssVar("--color-data-today", "#b54708"),
    week: cssVar("--color-data-week", "#175cd3"),
    rest: cssVar("--color-data-rest", "#667085"),
    m0: cssVar("--color-data-m0", "#175cd3"),
    m1: cssVar("--color-data-m1", "#3e7bbd"),
    m2: cssVar("--color-data-m2", "#98a2b3"),
    accent: cssVar("--color-accent", "#1f4e79"),
    muted: cssVar("--color-muted", "#5b6b7c"),
    text: cssVar("--color-text", "#1a2332"),
    grid: cssVar("--color-border-decorative", "#d5dce5"),
    positive: cssVar("--color-data-positive", "#067647"),
  };
}

export const CHART_MARGIN = { top: 8, right: 12, left: 4, bottom: 4 };
