/** J4-FIN FIN-1 — adiantamentos do pedido (crédito, não Payable). */

export type OrderAdvance = {
  payment_id: number;
  amount: string;
  currency: string;
  payment_date: string;
  external_reference: string | null;
  status: string;
  version: number;
  fx_execution_id: number | null;
  foreign_amount: string | null;
  brl_amount: string | null;
  rate: string | null;
  execution_date: string | null;
  amount_unallocated?: string | null;
  fx_documents: { id: number; original_filename: string }[];
};

export type OrderAdvancesResponse = {
  order_id: number;
  order_code: string;
  currency: string;
  advances: OrderAdvance[];
  consolidated: {
    total_eur: string;
    total_brl: string;
    weighted_avg_rate: string | null;
    count: number;
  };
};

export type AdvanceRegisterResult = {
  payment_id: number;
  order_id: number;
  amount: string;
  currency: string;
  payment_date: string;
  fx_execution_id: number;
  foreign_amount: string;
  brl_amount: string;
  rate: string;
  execution_date: string;
  fx_documents: { id: number; original_filename: string }[];
};

export async function listOrderAdvances(orderId: number): Promise<OrderAdvancesResponse> {
  const res = await fetch(`/api/orders/${orderId}/advances`, { credentials: "include" });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao listar adiantamentos");
  }
  return (await res.json()) as OrderAdvancesResponse;
}

export async function registerOrderAdvanceJson(
  orderId: number,
  body: {
    amount: string;
    payment_date: string;
    execution_date: string;
    rate?: string;
    brl_amount?: string;
    currency?: string;
    external_reference?: string;
    register_without_fx_document?: boolean;
    reason_code?: string;
  },
): Promise<AdvanceRegisterResult> {
  const res = await fetch(`/api/orders/${orderId}/advances`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao registrar adiantamento");
  }
  return (await res.json()) as AdvanceRegisterResult;
}

export async function registerOrderAdvanceWithFile(
  orderId: number,
  form: FormData,
): Promise<AdvanceRegisterResult> {
  const res = await fetch(`/api/orders/${orderId}/advances/with-document`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao registrar adiantamento");
  }
  return (await res.json()) as AdvanceRegisterResult;
}

export async function cancelOrderAdvance(
  orderId: number,
  paymentId: number,
  body: { expected_version: number; reason: string },
): Promise<OrderAdvancesResponse> {
  const res = await fetch(`/api/orders/${orderId}/advances/${paymentId}/cancel`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao cancelar adiantamento");
  }
  return (await res.json()) as OrderAdvancesResponse;
}
