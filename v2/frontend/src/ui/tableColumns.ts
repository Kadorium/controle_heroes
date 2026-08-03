import type { ReactNode } from "react";

/** always = compact+; standard = standard+wide; wide = só wide */
export type ColumnVisibility = "always" | "standard" | "wide";
export type ColumnPriority = 0 | 1 | 2 | 3;
export type LayoutMode = "compact" | "standard" | "wide";

export type OperationalColumnDef<T> = {
  id: string;
  header: ReactNode;
  visibility: ColumnVisibility;
  priority: ColumnPriority;
  minWidth: string;
  maxWidth?: string;
  truncate?: boolean;
  align?: "start" | "end";
  sticky?: boolean;
  headerClassName?: string;
  cellClassName?: string;
  cell: (row: T) => ReactNode;
};

const VISIBILITY_RANK: Record<ColumnVisibility, number> = {
  always: 0,
  standard: 1,
  wide: 2,
};

const MODE_RANK: Record<LayoutMode, number> = {
  compact: 0,
  standard: 1,
  wide: 2,
};

/** Colunas visíveis no modo atual — derivar uma vez no nível da tabela. */
export function filterVisibleColumns<T>(
  columns: readonly OperationalColumnDef<T>[],
  mode: LayoutMode,
): OperationalColumnDef<T>[] {
  const rank = MODE_RANK[mode];
  return columns.filter((col) => VISIBILITY_RANK[col.visibility] <= rank);
}

/** Resolve modo semântico a partir da largura inline do host (px). */
export function layoutModeFromWidth(
  widthPx: number,
  compactMaxPx: number,
  standardMaxPx: number,
): LayoutMode {
  if (widthPx <= compactMaxPx) return "compact";
  if (widthPx <= standardMaxPx) return "standard";
  return "wide";
}
