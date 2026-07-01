import type { OrderCentralModel } from "../../api";

export interface ModelTotals {
  qty: number | null;
  value: string | null;
}

export interface OpSummary {
  ordered: number;
  invoiced: number;
  shipped: number;
  toDispatch: number;
}

export interface ItemsFilterState {
  search: string;
  toDispatch: boolean;
  unmapped: boolean;
  needsReview: boolean;
}

export const EMPTY_ITEMS_FILTER: ItemsFilterState = {
  search: "",
  toDispatch: false,
  unmapped: false,
  needsReview: false,
};

export function modelLineValue(m: Pick<OrderCentralModel, "quantity_ordered" | "price_fattura">): string | null {
  const qty = m.quantity_ordered;
  const price = m.price_fattura;
  if (qty == null || price == null || price === "") return null;
  const n = Number(price);
  if (Number.isNaN(n)) return null;
  return String(qty * n);
}

export function summarizeModels(models: OrderCentralModel[]): ModelTotals {
  let qty = 0;
  let hasQty = false;
  let valueSum = 0;
  let hasValue = false;
  for (const m of models) {
    if (m.quantity_ordered != null) {
      qty += m.quantity_ordered;
      hasQty = true;
    }
    const v = modelLineValue(m);
    if (v != null && !Number.isNaN(Number(v))) {
      valueSum += Number(v);
      hasValue = true;
    }
  }
  return {
    qty: hasQty ? qty : null,
    value: hasValue ? String(valueSum) : null,
  };
}

export function computeOpSummary(models: OrderCentralModel[]): OpSummary {
  return models.reduce(
    (acc, m) => ({
      ordered: acc.ordered + (m.quantity_ordered ?? 0),
      invoiced: acc.invoiced + (m.quantity_invoiced ?? 0),
      shipped: acc.shipped + (m.quantity_shipped ?? 0),
      toDispatch: acc.toDispatch + (m.to_dispatch ?? 0),
    }),
    { ordered: 0, invoiced: 0, shipped: 0, toDispatch: 0 },
  );
}

function modelSearchText(m: OrderCentralModel): string {
  return [
    m.model_label,
    m.description,
    m.product_sku,
    m.supplier_sku,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function filterModels(models: OrderCentralModel[], filter: ItemsFilterState): OrderCentralModel[] {
  const q = filter.search.trim().toLowerCase();
  return models.filter((m) => {
    if (filter.toDispatch && (m.to_dispatch ?? 0) <= 0) return false;
    if (filter.unmapped && m.product_id != null) return false;
    if (filter.needsReview && !m.dispatch_needs_review) return false;
    if (q && !modelSearchText(m).includes(q)) return false;
    return true;
  });
}
