import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Order = components["schemas"]["OrderResponse"];
export type OrderListItem = components["schemas"]["OrderListItem"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

function throwApi(error: unknown, response: Response | undefined, fallback: string): never {
  const err = new Error(errMsg(error, fallback)) as Error & { status?: number };
  err.status = response?.status;
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
