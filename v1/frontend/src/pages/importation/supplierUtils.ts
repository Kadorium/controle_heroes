import type { Supplier } from "../../api";

function normalizeName(name: string): string {
  return name.trim().toLowerCase();
}

/** Remove duplicatas por nome (mantém menor id) — corrige QA-LOW-002 na UI. */
export function dedupeSuppliersByName(suppliers: Supplier[]): Supplier[] {
  const byName = new Map<string, Supplier>();
  for (const s of suppliers) {
    const key = normalizeName(s.name);
    const existing = byName.get(key);
    if (!existing || s.id < existing.id) {
      byName.set(key, s);
    }
  }
  return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
}

/** Fornecedor Heroes padrão (primeiro match após dedupe). */
export function pickHeroesSupplierId(suppliers: Supplier[]): string {
  const deduped = dedupeSuppliersByName(suppliers);
  const heroes = deduped.find((s) => /^heroes$/i.test(s.name.trim()));
  if (heroes) return String(heroes.id);
  return deduped[0] ? String(deduped[0].id) : "";
}
