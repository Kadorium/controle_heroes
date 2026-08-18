import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Order = components["schemas"]["OrderResponse"];
export type OrderListItem = components["schemas"]["OrderListItem"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

function throwApi(error: unknown, response: Response | undefined, fallback: string): never {
  const err = new Error(errMsg(error, fallback)) as Error & { status?: number; code?: string };
  err.status = response?.status;
  err.code = (error as { error?: string } | undefined)?.error;
  throw err;
}

export async function listOrders() {
  const { data, error } = await api.GET("/api/orders", { params: { query: { limit: 50 } } });
  if (error) throw new Error(errMsg(error, "Erro ao listar ordens"));
  return data ?? [];
}

export async function getOrder(orderId: number) {
  const { data, error } = await api.GET("/api/orders/{order_id}", {
    params: { path: { order_id: orderId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar ordem"));
  return data!;
}

export async function createOrder(body: {
  code: string;
  supplier_id: number;
  currency?: string;
  order_date?: string | null;
  notes?: string | null;
}) {
  const { data, error } = await api.POST("/api/orders", {
    body: { currency: "EUR", ...body },
  });
  if (error) throw new Error(errMsg(error, "Erro ao criar ordem"));
  return data!;
}

export async function updateOrder(
  orderId: number,
  body: {
    expected_version: number;
    order_date?: string | null;
    notes?: string | null;
    supplier_id?: number | null;
    currency?: string | null;
  },
) {
  const { data, error, response } = await api.PATCH("/api/orders/{order_id}", {
    params: { path: { order_id: orderId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar pedido");
  return data!;
}

export async function addOrderItem(
  orderId: number,
  body: {
    expected_version: number;
    product_id?: number;
    sku?: string;
    quantity: string;
    unit_price?: string | null;
    unit?: string | null;
  },
) {
  const { data, error } = await api.POST("/api/orders/{order_id}/items", {
    params: { path: { order_id: orderId } },
    body,
  });
  if (error) throw new Error(errMsg(error, "Erro ao adicionar item"));
  return data!;
}

export async function updateOrderItem(
  orderId: number,
  itemId: number,
  body: {
    expected_version: number;
    quantity?: string | null;
    unit_price?: string | null;
    unit?: string | null;
  },
) {
  const { data, error, response } = await api.PATCH("/api/orders/{order_id}/items/{item_id}", {
    params: { path: { order_id: orderId, item_id: itemId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar item");
  return data!;
}

export async function uploadOrderDocument(orderId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", "order");
  form.append("entity_id", String(orderId));
  form.append("role", "official");
  const res = await fetch("/api/documents", { method: "POST", body: form, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "Erro ao anexar documento do pedido");
  }
  return res.json();
}

export async function confirmOrder(orderId: number, expected_version: number) {
  const { data, error, response } = await api.POST("/api/orders/{order_id}/confirm", {
    params: { path: { order_id: orderId } },
    body: { expected_version },
  });
  if (error) throwApi(error, response, "Erro ao confirmar");
  return data!;
}

export async function cancelOrder(
  orderId: number,
  expected_version: number,
  reason_code?: string,
) {
  const { data, error, response } = await api.POST("/api/orders/{order_id}/cancel", {
    params: { path: { order_id: orderId } },
    body: { expected_version, reason_code },
  });
  if (error) throwApi(error, response, "Erro ao cancelar");
  return data!;
}

export async function bindCommitmentProduct(
  orderId: number,
  itemId: number,
  body: { expected_version: number; product_id: number },
) {
  const { data, error, response } = await api.POST(
    "/api/orders/{order_id}/items/{item_id}/bind-product",
    {
      params: { path: { order_id: orderId, item_id: itemId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao vincular produto");
  return data!;
}

export type PaymentScheduleLine = {
  id?: number;
  sequence: number;
  due_date: string | null;
  condition_text: string | null;
  percent: string | null;
  amount: string | null;
  derived_amount: string | null;
};

export type PaymentScheduleView = {
  order_id: number;
  order_version: number;
  order_status: string;
  currency: string;
  mode: "PERCENT" | "AMOUNT" | null;
  commercial_total: string | null;
  amount_sum: string | null;
  delta: string | null;
  coherence: "aligned" | "divergent" | "unverifiable" | null;
  lines: PaymentScheduleLine[];
};

export async function getPaymentSchedule(orderId: number) {
  const res = await fetch(`/api/orders/${orderId}/payment-schedule`, { credentials: "include" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throwApi(body, res, "Erro ao carregar cronograma");
  return body as PaymentScheduleView;
}

export async function setPaymentSchedule(
  orderId: number,
  body: {
    expected_version: number;
    mode: "PERCENT" | "AMOUNT" | null;
    lines: Array<{
      due_date?: string | null;
      condition_text?: string | null;
      percent?: string | null;
      amount?: string | null;
    }>;
    reason_code?: string | null;
  },
) {
  const res = await fetch(`/api/orders/${orderId}/payment-schedule`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throwApi(payload, res, "Erro ao gravar cronograma");
  return payload as PaymentScheduleView;
}
