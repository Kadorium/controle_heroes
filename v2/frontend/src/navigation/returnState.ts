/**
 * Retorno contextual (FLW-007 / I9-9).
 * Preserva search + scrollY + selectedId por pathname.
 * Sem inventar filtros: se storage ausente/stale → fallback explícito (caller).
 */

const PREFIX = "epic:return:";

export type ReturnSnapshot = {
  search: string;
  scrollY: number;
  selectedId: string | null;
  savedAt: number;
};

export function returnKey(pathname: string): string {
  return `${PREFIX}${pathname}`;
}

export function saveReturnState(
  pathname: string,
  partial: Partial<Omit<ReturnSnapshot, "savedAt">> & { search?: string },
): void {
  try {
    const prev = loadReturnState(pathname);
    const next: ReturnSnapshot = {
      search: partial.search ?? prev?.search ?? "",
      scrollY: partial.scrollY ?? prev?.scrollY ?? 0,
      selectedId: partial.selectedId !== undefined ? partial.selectedId : (prev?.selectedId ?? null),
      savedAt: Date.now(),
    };
    sessionStorage.setItem(returnKey(pathname), JSON.stringify(next));
  } catch {
    /* quota / private mode — ignore */
  }
}

export function loadReturnState(pathname: string): ReturnSnapshot | null {
  try {
    const raw = sessionStorage.getItem(returnKey(pathname));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ReturnSnapshot;
    if (typeof parsed.search !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearReturnState(pathname: string): void {
  try {
    sessionStorage.removeItem(returnKey(pathname));
  } catch {
    /* ignore */
  }
}

/** Monta path de retorno com search salvo (ou fallbackSearch). */
export function buildReturnTo(
  pathname: string,
  fallbackSearch = "",
): string {
  const snap = loadReturnState(pathname);
  const search = snap?.search ?? fallbackSearch;
  return search ? `${pathname}${search.startsWith("?") ? search : `?${search}`}` : pathname;
}
