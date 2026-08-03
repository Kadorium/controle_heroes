import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Invoice = components["schemas"]["InvoiceResponse"];
export type InvoiceListItem = components["schemas"]["InvoiceListItem"];
export type Payable = components["schemas"]["PayableResponse"];
export type OrderQtyRow = components["schemas"]["OrderQtyRow"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

function throwApi(error: unknown, response: Response | undefined, fallback: string): never {
  const err = new Error(errMsg(error, fallback)) as Error & { status?: number };
  err.status = response?.status;
  throw err;
}

export async function listOrderInvoices(orderId: number) {
  const { data, error } = await api.GET("/api/orders/{order_id}/invoices", {
    params: { path: { order_id: orderId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar faturas"));
  return data ?? [];
}

export async function listInvoices(query?: { order_id?: number; status?: string }) {
  const { data, error } = await api.GET("/api/invoices", {
    params: { query: { limit: 100, ...query } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar faturas"));
  return data ?? [];
}

export async function getInvoice(invoiceId: number) {
  const { data, error } = await api.GET("/api/invoices/{invoice_id}", {
    params: { path: { invoice_id: invoiceId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar fatura"));
  return data!;
}

export async function createInvoice(
  orderId: number,
  body: {
    invoice_number: string;
    invoice_type?: string;
    invoice_date?: string;
    order_item_ids?: number[];
  },
) {
  const { data, error } = await api.POST("/api/orders/{order_id}/invoices", {
    params: { path: { order_id: orderId } },
    body: { invoice_type: "FINAL", ...body },
  });
  if (error) throw new Error(errMsg(error, "Erro ao criar fatura"));
  return data!;
}

export async function updateInvoice(
  invoiceId: number,
  body: {
    expected_version: number;
    invoice_number?: string | null;
    invoice_type?: string | null;
    invoice_date?: string | null;
    notes?: string | null;
  },
) {
  const { data, error, response } = await api.PATCH("/api/invoices/{invoice_id}", {
    params: { path: { invoice_id: invoiceId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar fatura");
  return data!;
}

export async function replaceItems(
  invoiceId: number,
  expected_version: number,
  items: {
    order_item_id: number;
    quantity: string;
    unit_price_gross?: string | null;
    unit?: string | null;
    discount_type?: string | null;
    discount_unit_amount?: string | null;
    discount_percent?: string | null;
  }[],
) {
  const { data, error, response } = await api.PUT("/api/invoices/{invoice_id}/items", {
    params: { path: { invoice_id: invoiceId } },
    body: { expected_version, items },
  });
  if (error) throwApi(error, response, "Erro ao salvar itens");
  return data!;
}

export async function setTerms(
  invoiceId: number,
  expected_version: number,
  mode: string,
  terms: { due_date: string; percent?: string | null; amount?: string | null }[],
) {
  const { data, error, response } = await api.PUT("/api/invoices/{invoice_id}/terms", {
    params: { path: { invoice_id: invoiceId } },
    body: { expected_version, mode, terms },
  });
  if (error) throwApi(error, response, "Erro ao salvar scadenze");
  return data!;
}

export async function issueInvoice(
  invoiceId: number,
  expected_version: number,
  opts?: { issue_without_document?: boolean; reason_code?: string },
) {
  const { data, error, response } = await api.POST("/api/invoices/{invoice_id}/issue", {
    params: { path: { invoice_id: invoiceId } },
    body: {
      expected_version,
      issue_without_document: opts?.issue_without_document ?? false,
      reason_code: opts?.reason_code,
    },
  });
  if (error) throwApi(error, response, "Erro ao emitir");
  return data!;
}

export async function cancelInvoice(
  invoiceId: number,
  expected_version: number,
  reason_code?: string,
) {
  const { data, error, response } = await api.POST("/api/invoices/{invoice_id}/cancel", {
    params: { path: { invoice_id: invoiceId } },
    body: { expected_version, reason_code },
  });
  if (error) throwApi(error, response, "Erro ao cancelar fatura");
  return data!;
}

export async function listPayables(query?: {
  order_id?: number;
  invoice_id?: number;
  status?: string;
}) {
  const { data, error } = await api.GET("/api/payables", {
    params: { query: { limit: 100, ...query } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar payables"));
  return data ?? [];
}

export async function getPayable(payableId: number) {
  const { data, error } = await api.GET("/api/payables/{payable_id}", {
    params: { path: { payable_id: payableId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar obrigação"));
  return data!;
}

export async function invoicedQuantities(orderId: number) {
  const { data, error } = await api.GET("/api/orders/{order_id}/invoiced-quantities", {
    params: { path: { order_id: orderId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar quantidades"));
  return data ?? [];
}

export async function uploadInvoiceDocument(invoiceId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", "invoice");
  form.append("entity_id", String(invoiceId));
  form.append("role", "official");
  const res = await fetch("/api/documents", { method: "POST", body: form, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "Erro ao anexar documento");
  }
  return res.json();
}
