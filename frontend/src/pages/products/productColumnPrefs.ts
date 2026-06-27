export type ProductColumnId =
  | "photo"
  | "sku"
  | "supplier_code"
  | "name"
  | "group"
  | "subgroup"
  | "status"
  | "ncm"
  | "supplier"
  | "launch_date"
  | "pending"
  | "orders"
  | "qty_ordered"
  | "qty_in_transit"
  | "qty_nationalization"
  | "qty_stock";

export const PRODUCT_COLUMN_ORDER: ProductColumnId[] = [
  "photo",
  "sku",
  "supplier_code",
  "name",
  "group",
  "subgroup",
  "status",
  "ncm",
  "supplier",
  "launch_date",
  "pending",
  "orders",
  "qty_ordered",
  "qty_in_transit",
  "qty_nationalization",
  "qty_stock",
];

export const PRODUCT_COLUMN_LABELS: Record<ProductColumnId, string> = {
  photo: "Foto",
  sku: "SKU",
  supplier_code: "Cód. fornecedor",
  name: "Nome",
  group: "Grupo",
  subgroup: "Subgrupo",
  status: "Status",
  ncm: "NCM",
  supplier: "Fornecedor",
  launch_date: "Lançamento",
  pending: "Pendências",
  orders: "Ordens",
  qty_ordered: "Pedido",
  qty_in_transit: "Trânsito",
  qty_nationalization: "Nacionalização",
  qty_stock: "Estoque",
};

const DEFAULT_VISIBLE: ProductColumnId[] = [
  "photo",
  "sku",
  "supplier_code",
  "name",
  "group",
  "status",
  "ncm",
  "supplier",
];

const STORAGE_PREFIX = "epic.products.columns.v1";

function storageKey(userId: number | undefined): string {
  return `${STORAGE_PREFIX}:${userId ?? "anon"}`;
}

export function defaultVisibleColumns(): ProductColumnId[] {
  return [...DEFAULT_VISIBLE];
}

export function loadVisibleColumns(userId: number | undefined): ProductColumnId[] {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return defaultVisibleColumns();
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return defaultVisibleColumns();
    const valid = parsed.filter(
      (id): id is ProductColumnId =>
        typeof id === "string" && PRODUCT_COLUMN_ORDER.includes(id as ProductColumnId),
    );
    return valid.length > 0 ? valid : defaultVisibleColumns();
  } catch {
    return defaultVisibleColumns();
  }
}

export function saveVisibleColumns(userId: number | undefined, columns: ProductColumnId[]): void {
  localStorage.setItem(storageKey(userId), JSON.stringify(columns));
}

export function toggleColumn(
  visible: ProductColumnId[],
  column: ProductColumnId,
): ProductColumnId[] {
  if (visible.includes(column)) {
    const next = visible.filter((c) => c !== column);
    return next.length > 0 ? next : visible;
  }
  const next = [...visible, column];
  next.sort((a, b) => PRODUCT_COLUMN_ORDER.indexOf(a) - PRODUCT_COLUMN_ORDER.indexOf(b));
  return next;
}
