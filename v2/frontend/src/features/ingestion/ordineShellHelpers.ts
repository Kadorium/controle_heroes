/** Helpers UI-only para workspace Ordine (compromisso por padrão). */

export type CellMap = Record<string, { raw?: string | null; normalized?: string | null }>;

export function parseRowCells(cellsJson: string | null | undefined): CellMap {
  if (!cellsJson) return {};
  try {
    return JSON.parse(cellsJson) as CellMap;
  } catch {
    return {};
  }
}

export function cellText(cells: CellMap, key: string): string {
  const c = cells[key];
  return String(c?.normalized ?? c?.raw ?? "").trim();
}

/** EAN típico: só dígitos, comprimento 8/12/13/14. */
export function looksLikeEan(code: string): boolean {
  const d = code.replace(/\s/g, "");
  return /^\d{8}$|^\d{12,14}$/.test(d);
}

export function isProductResolved(cells: CellMap): boolean {
  const id = cellText(cells, "product_id_catalog");
  return Boolean(id && id !== "None" && /^\d+$/.test(id));
}

/** Linha de compromisso = padrão Ordine PDF, exceto EAN não resolvido (vínculo) ou já resolvido. */
export function isCommitmentLine(cells: CellMap): boolean {
  if (isProductResolved(cells)) return false;
  const sku = cellText(cells, "sku");
  if (looksLikeEan(sku)) return false;
  return true;
}

export function formatQty(raw: string): string {
  if (!raw) return "—";
  const n = Number(raw.replace(",", "."));
  if (!Number.isFinite(n)) return raw;
  return n.toLocaleString("pt-BR");
}

export function formatMoneyEur(raw: string): string {
  if (!raw) return "—";
  const s = String(raw).trim();
  let n: number;
  if (/,/.test(s)) {
    // Italian thousands: 830.000,00
    n = Number(s.replace(/\./g, "").replace(",", "."));
  } else {
    n = Number(s);
  }
  if (!Number.isFinite(n)) return `€ ${raw}`;
  return n.toLocaleString("pt-BR", { style: "currency", currency: "EUR" });
}
