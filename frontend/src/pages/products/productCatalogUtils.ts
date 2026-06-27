import type { Product } from "../api";

export const PENDING_LABELS: Record<string, string> = {
  ncm_pending: "NCM pendente",
  no_photo: "Sem foto",
  no_supplier: "Sem fornecedor",
  no_weight_volume: "Sem peso/volume",
  fiscal_review: "Fiscal a revisar",
};

export const STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Ativo",
  DISCONTINUED: "Descontinuado",
  ARCHIVED: "Arquivado",
  DRAFT: "Rascunho",
};

export type Visibility = "active" | "archived" | "cancelled" | "all";
export type QuickFilter =
  | "all"
  | "ncm_pending"
  | "no_photo"
  | "no_weight_volume"
  | "no_supplier"
  | "fiscal_review"
  | "discontinued";

export type BulkAction =
  | "archive"
  | "restore"
  | "discontinue"
  | "reactivate"
  | "cancel"
  | "export";

export interface BulkEligibility {
  eligible: Product[];
  ineligible: Product[];
}

export function canArchive(p: Product): boolean {
  return p.is_active && p.lifecycle_status !== "ARCHIVED";
}

export function canRestore(p: Product): boolean {
  return p.lifecycle_status === "ARCHIVED";
}

export function canDiscontinue(p: Product): boolean {
  return p.is_active && p.lifecycle_status === "ACTIVE";
}

export function canReactivate(p: Product): boolean {
  return p.is_active && p.lifecycle_status === "DISCONTINUED";
}

export function canCancel(p: Product): boolean {
  return p.is_active;
}

export function bulkEligible(products: Product[], action: BulkAction): BulkEligibility {
  if (action === "export") {
    return { eligible: [...products], ineligible: [] };
  }
  const check =
    action === "archive"
      ? canArchive
      : action === "restore"
        ? canRestore
        : action === "discontinue"
          ? canDiscontinue
          : action === "reactivate"
            ? canReactivate
            : action === "cancel"
              ? canCancel
              : () => false;
  const eligible: Product[] = [];
  const ineligible: Product[] = [];
  for (const p of products) {
    (check(p) ? eligible : ineligible).push(p);
  }
  return { eligible, ineligible };
}

export function formatBulkResult(result: {
  succeeded: number[];
  skipped: Array<{ id: number; reason: string }>;
  failed: Array<{ id: number; error: string }>;
}): string {
  const parts: string[] = [];
  if (result.succeeded.length) parts.push(`${result.succeeded.length} ok`);
  if (result.skipped.length) parts.push(`${result.skipped.length} ignorado(s)`);
  if (result.failed.length) parts.push(`${result.failed.length} falha(s)`);
  return parts.join(" · ") || "Nenhuma alteração";
}

export const BULK_ACTION_LABELS: Record<BulkAction, string> = {
  archive: "Arquivar",
  restore: "Restaurar",
  discontinue: "Descontinuar",
  reactivate: "Reativar",
  cancel: "Excluir",
  export: "Exportar CSV",
};

export const BULK_ACTION_HINTS: Partial<Record<BulkAction, string>> = {
  cancel: "Remove da operação (histórico preservado)",
};

export function exportProductsCsv(rows: Product[]) {
  const header = [
    "sku_code", "description", "product_group", "lifecycle_status", "ncm",
    "supplier_code", "default_supplier_name", "weight_kg", "volume_m3",
  ];
  const lines = rows.map((r) =>
    [
      r.sku_code, r.description, r.product_group ?? "", r.lifecycle_status ?? "",
      r.ncm ?? "", r.supplier_code ?? "", r.default_supplier_name ?? "",
      r.weight_kg ?? "", r.volume_m3 ?? "",
    ]
      .map((c) => `"${String(c).replace(/"/g, '""')}"`)
      .join(",")
  );
  const blob = new Blob([`\uFEFF${header.join(",")}\n${lines.join("\n")}`], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `produtos-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function sortProducts(rows: Product[], key: keyof Product, asc: boolean): Product[] {
  const copy = [...rows];
  copy.sort((a, b) => {
    const av = a[key] ?? "";
    const bv = b[key] ?? "";
    const cmp = String(av).localeCompare(String(bv), "pt-BR", { numeric: true });
    return asc ? cmp : -cmp;
  });
  return copy;
}
