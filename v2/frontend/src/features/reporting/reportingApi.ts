/** API Reporting — fila AP e cockpit. */

export type ApQueueResponse = {
  items: Array<Record<string, unknown>>;
  total: number;
  limit: number;
  offset: number;
  kpis: Record<string, string | number>;
  market_quote?: Record<string, unknown> | null;
  unallocated_candidates?: Array<Record<string, unknown>>;
  sort?: string;
  note?: string;
};

export type OrderCockpit = {
  order_id: number;
  commercial: Record<string, unknown>;
  billing: Record<string, unknown>;
  treasury: Record<string, unknown>;
  fx: Record<string, unknown>;
  documents: Record<string, unknown>;
  audit: Record<string, unknown>;
  alerts: Array<{ code: string; message: string; href?: string }>;
  kpis: Record<string, string | null | undefined>;
};

function qs(params: Record<string, string | number | undefined | null>) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export async function fetchApQueue(params: Record<string, string | number | undefined | null>) {
  const res = await fetch(`/api/reporting/ap-queue${qs(params)}`, { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as ApQueueResponse;
}

export async function fetchOrderSummary(orderId: number) {
  const res = await fetch(`/api/orders/${orderId}/summary`, { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as OrderCockpit;
}

export type OrderListRow = {
  id: number;
  code: string;
  supplier_id: number;
  supplier_name?: string | null;
  status: string;
  currency: string;
  order_date?: string | null;
  commercial_total?: string | null;
  unpriced_item_count?: number;
  invoiced_amount?: string | null;
  open_balance?: string | null;
  next_due_date?: string | null;
  pendencies?: string | null;
};

export async function fetchOrdersList(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const res = await fetch(`/api/reporting/orders-list${qs(params ?? {})}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as OrderListRow[];
}
