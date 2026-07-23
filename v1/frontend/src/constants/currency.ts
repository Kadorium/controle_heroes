/** Moeda padrão das importações Epic (fornecedores / Heroes). */
export const DEFAULT_IMPORT_CURRENCY = "EUR";

/** Despesas locais BR (aduana, landed cost). */
export const LOCAL_CURRENCY = "BRL";

/** Importação/fornecedor: EUR; USD legado → EUR; BRL permanece BRL. */
export function normalizeImportCurrency(currency: string | null | undefined): string {
  if (!currency || !currency.trim()) return DEFAULT_IMPORT_CURRENCY;
  const c = currency.trim().toUpperCase();
  if (c === LOCAL_CURRENCY) return LOCAL_CURRENCY;
  if (c === "USD") return DEFAULT_IMPORT_CURRENCY;
  return c;
}
