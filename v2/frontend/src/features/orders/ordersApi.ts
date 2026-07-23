import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Order = components["schemas"]["OrderResponse"];
export type OrderListItem = components["schemas"]["OrderListItem"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
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
  notes?: string;
}) {
  const { data, error } = await api.POST("/api/orders", {
    body: { currency: "EUR", ...body },
  });
  if (error) throw new Error(errMsg(error, "Erro ao criar ordem"));
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
  },
) {
  const { data, error } = await api.POST("/api/orders/{order_id}/items", {
    params: { path: { order_id: orderId } },
    body,
  });
  if (error) throw new Error(errMsg(error, "Erro ao adicionar item"));
  return data!;
}

export async function confirmOrder(orderId: number, expected_version: number) {
  const { data, error } = await api.POST("/api/orders/{order_id}/confirm", {
    params: { path: { order_id: orderId } },
    body: { expected_version },
  });
  if (error) throw new Error(errMsg(error, "Erro ao confirmar"));
  return data!;
}

export async function cancelOrder(
  orderId: number,
  expected_version: number,
  reason_code?: string,
) {
  const { data, error } = await api.POST("/api/orders/{order_id}/cancel", {
    params: { path: { order_id: orderId } },
    body: { expected_version, reason_code },
  });
  if (error) throw new Error(errMsg(error, "Erro ao cancelar"));
  return data!;
}
