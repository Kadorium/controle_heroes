import { api } from "../../api/generated/client";

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

export type Payment = {
  id: number;
  supplier_id: number;
  amount: string;
  currency: string;
  payment_date: string;
  external_reference: string | null;
  status: string;
  version: number;
  amount_allocated: string;
  amount_unallocated: string;
  allocations: { id: number; payable_id: number; amount: string }[];
  documents: { id: number; original_filename: string }[];
};

export type EligiblePayable = {
  id: number;
  invoice_id: number;
  order_id: number;
  due_date: string;
  amount: string;
  balance: string;
  allocated_amount: string;
  currency: string;
  status: string;
  version: number;
};

export async function listPayments() {
  const res = await fetch("/api/payments?limit=100", { credentials: "include" });
  if (!res.ok) throw new Error("Erro ao listar pagamentos");
  return (await res.json()) as Payment[];
}

export async function getPayment(id: number) {
  const res = await fetch(`/api/payments/${id}`, { credentials: "include" });
  if (!res.ok) throw new Error("Erro ao carregar pagamento");
  return (await res.json()) as Payment;
}

export async function registerPaymentJson(body: {
  supplier_id: number;
  amount: string;
  currency: string;
  payment_date: string;
  external_reference?: string;
  register_without_document?: boolean;
  reason_code?: string;
}) {
  const res = await fetch("/api/payments", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao registrar pagamento");
  }
  return (await res.json()) as Payment;
}

export async function registerPaymentWithFile(form: FormData) {
  const res = await fetch("/api/payments/with-document", {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao registrar pagamento");
  }
  return (await res.json()) as Payment;
}

export async function eligiblePayables(paymentId: number) {
  const res = await fetch(`/api/payments/${paymentId}/eligible-payables`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Erro ao listar payables elegíveis");
  return (await res.json()) as EligiblePayable[];
}

export async function allocatePayment(
  paymentId: number,
  body: {
    expected_version: number;
    idempotency_key: string;
    allocations: { payable_id: number; amount: string; expected_version: number }[];
  },
) {
  const res = await fetch(`/api/payments/${paymentId}/allocations`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.message || "Erro ao alocar");
  }
  return (await res.json()) as Payment;
}

export function canWriteTreasury(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("treasury:write");
}

export function canAllocateTreasury(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("treasury:allocate");
}

// silence unused api import until OpenAPI regen uses it
void api;
void errMsg;
