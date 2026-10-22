/** Rótulos de apresentação Costing — sem regra de domínio. */

export const EXPENSE_CATEGORIES = [
  { value: "OUTRAS", label: "Outras" },
  { value: "SEGURO", label: "Seguro" },
  { value: "ARMAZENAGEM", label: "Armazenagem" },
  { value: "DESPACHANTE", label: "Despachante" },
  { value: "FRETE_NACIONAL", label: "Frete nacional" },
  { value: "HONORARIOS", label: "Honorários" },
] as const;

export const ALLOCATION_METHODS = [
  { value: "VALUE", label: "Valor da mercadoria" },
  { value: "QUANTITY", label: "Quantidade" },
  { value: "WEIGHT", label: "Peso líquido" },
  { value: "VOLUME", label: "Volume" },
] as const;

export function expenseCategoryLabel(code: string | null | undefined): string {
  const hit = EXPENSE_CATEGORIES.find((c) => c.value === code);
  return hit?.label ?? (code || "—");
}

export function allocationMethodLabel(code: string | null | undefined): string {
  const hit = ALLOCATION_METHODS.find((c) => c.value === code);
  return hit?.label ?? (code || "—");
}

export function expenseStatusLabel(status: string | null | undefined): string {
  if (status === "ACTIVE") return "Ativa";
  if (status === "CANCELLED") return "Cancelada";
  return status || "—";
}

export function versionStatusLabel(status: string | null | undefined): string {
  if (status === "DRAFT") return "Rascunho";
  if (status === "PUBLISHED") return "Publicada";
  if (status === "SUPERSEDED") return "Substituída";
  return status || "—";
}

export function componentTypeLabel(code: string | null | undefined): string {
  if (!code) return "—";
  if (code === "MERCADORIA") return "Mercadoria";
  if (code === "FRETE_INTERNACIONAL") return "Frete internacional";
  if (code === "FRETE_REMOCAO") return "Frete (remoção)";
  if (code === "FRETE_ENTREGA") return "Frete (entrega)";
  if (code.startsWith("EXPENSE_COSTING_")) {
    return `Despesa · ${expenseCategoryLabel(code.replace(/^EXPENSE_COSTING_/, ""))}`;
  }
  return code.replace(/_/g, " ");
}

export function versionKindLabel(kind: string | null | undefined): string {
  if (kind === "ESTIMATED") return "Estimado";
  if (kind === "REVISED") return "Revisado";
  if (kind === "REALIZED") return "Realizado (câmbio bancário)";
  return kind || "—";
}

export function sourceKindLabel(code: string | null | undefined): string {
  if (code === "INVOICE") return "Fatura";
  if (code === "TAX_LINE") return "Tributo (Numerário)";
  if (code === "EXPENSE_LINE") return "Despesa (Numerário)";
  if (code === "VALUE_BASIS") return "Base aduaneira";
  if (code === "COSTING_EXPENSE") return "Despesa adicional";
  return code || "—";
}
