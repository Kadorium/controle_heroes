/** API Reporting — fila AP e cockpit. */

export type ApQueueCurrencyKpis = {
  currency: string;
  open_balance: string;
  overdue_balance: string;
  due_today_balance: string;
  next_7d_balance: string;
  overdue_count: number;
  total_count: number;
};

export type ApQueueResponse = {
  items: Array<Record<string, unknown>>;
  total: number;
  limit: number;
  offset: number;
  kpis: {
    mixed_currency?: boolean;
    total_count?: number;
    overdue_count?: number;
    kpis_by_currency?: ApQueueCurrencyKpis[];
    unallocated_by_currency?: Array<{
      currency: string;
      unallocated_candidates_count: number;
      unallocated_candidates_total: string;
    }>;
  };
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
  schedule?: {
    mode?: string | null;
    commercial_total?: string | null;
    amount_sum?: string | null;
    delta?: string | null;
    coherence?: string | null;
    currency?: string;
    lines?: Array<{
      sequence?: number;
      due_date?: string | null;
      condition_text?: string | null;
      percent?: string | null;
      amount?: string | null;
      derived_amount?: string | null;
    }>;
  };
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
