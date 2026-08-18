/** FX Inc-4 — API helpers (três visões). */

export type FxMarketQuote = {
  id?: number;
  rate: string | null;
  status: string;
  stale: boolean;
  source: string | null;
  observed_at?: string | null;
  retrieved_at?: string | null;
};

export type PayableFxView = {
  payable_id: number;
  currency: string;
  open_foreign: string;
  initial_planned_rate: string | null;
  current_forecast_rate: string | null;
  market: FxMarketQuote;
  projected_open_brl: string | null;
  market_open_brl: string | null;
  online_result_vs_current: string | null;
  online_result_vs_initial: string | null;
  settled_foreign: string;
  cost_brl?: string | null;
  realized_brl: string | null;
  realized_result_vs_reference: string | null;
  realized_result_vs_initial: string | null;
  total_vs_current: string | null;
  total_vs_initial: string | null;
  benchmarks: Record<string, string>;
  plan_history: {
    id: number;
    kind: string;
    rate: string;
    version: number;
    is_current: boolean;
    effective_from: string;
  }[];
};

export type PaymentFxView = {
  payment_id: number;
  currency: string;
  amount: string;
  executions: {
    id: number;
    foreign_amount: string;
    brl_amount: string;
    rate: string;
    execution_date: string;
  }[];
  allocations: {
    allocation_id: number;
    payable_id: number;
    foreign_amount: string;
    valuation: {
      id: number;
      planned_rate_used_at_realization: string | null;
      realized_rate: string | null;
      realized_brl: string | null;
      realized_result_vs_reference: string | null;
      realized_result_vs_initial: string | null;
      reference_kind: string;
    } | null;
    execution_links: {
      id: number;
      fx_execution_id: number;
      foreign_amount: string;
      brl_amount: string;
    }[];
  }[];
};

function err(res: Response, fallback: string) {
  return res.json().then((j) => new Error(j.message || fallback)).catch(() => new Error(fallback));
}

export async function getLatestQuote(foreign = "EUR"): Promise<FxMarketQuote> {
  const res = await fetch(`/api/fx/quotes/latest?foreign=${foreign}&base=BRL`, {
    credentials: "include",
  });
  if (!res.ok) throw await err(res, "Erro ao ler cotação");
  return (await res.json()) as FxMarketQuote;
}

export type QuoteForDate = FxMarketQuote & {
  as_of?: string;
  message?: string | null;
};

/** Cotação no dia `as_of` (YYYY-MM-DD). Sem vizinho — status missing se não houver. */
export async function getQuoteForDate(asOf: string, foreign = "EUR"): Promise<QuoteForDate> {
  const q = new URLSearchParams({ as_of: asOf, foreign, base: "BRL" });
  const res = await fetch(`/api/fx/quotes/for-date?${q}`, { credentials: "include" });
  if (!res.ok) throw await err(res, "Erro ao ler cotação do dia");
  return (await res.json()) as QuoteForDate;
}

export async function refreshQuote(foreign = "EUR"): Promise<FxMarketQuote> {
  const res = await fetch(`/api/fx/quotes/refresh?foreign=${foreign}&base=BRL`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) throw await err(res, "Falha ao atualizar cotação");
  return (await res.json()) as FxMarketQuote;
}

export async function postManualQuote(rate: string, foreign = "EUR") {
  const res = await fetch("/api/fx/quotes", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ foreign_currency: foreign, rate, source: "MANUAL" }),
  });
  if (!res.ok) throw await err(res, "Erro ao gravar cotação manual");
  return res.json();
}

export async function getPayableFxView(payableId: number): Promise<PayableFxView> {
  const res = await fetch(`/api/payables/${payableId}/fx-view`, { credentials: "include" });
  if (!res.ok) throw await err(res, "Erro ao carregar visão FX");
  return (await res.json()) as PayableFxView;
}

export async function postFxPlan(
  payableId: number,
  body: {
    kind: string;
    rate: string;
    effective_from: string;
    reason_code?: string;
  },
) {
  const res = await fetch(`/api/payables/${payableId}/fx-plan`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await err(res, "Erro ao registrar taxa projetada");
  return res.json();
}

export async function getPaymentFxView(paymentId: number): Promise<PaymentFxView> {
  const res = await fetch(`/api/payments/${paymentId}/fx-view`, { credentials: "include" });
  if (!res.ok) throw await err(res, "Erro ao carregar FX do pagamento");
  return (await res.json()) as PaymentFxView;
}

export async function registerFxExecutionWithDoc(
  paymentId: number,
  form: FormData,
) {
  const res = await fetch(`/api/payments/${paymentId}/fx-executions/with-document`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) throw await err(res, "Erro ao registrar execução FX");
  return res.json();
}

export async function linkExecutionAllocation(body: {
  fx_execution_id: number;
  payment_allocation_id: number;
  foreign_amount?: string;
}) {
  const res = await fetch("/api/fx/execution-allocations", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await err(res, "Erro ao vincular execução×alocação");
  return res.json();
}

export async function completeValuation(payment_allocation_id: number) {
  const res = await fetch("/api/fx/valuations/complete", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_allocation_id }),
  });
  if (!res.ok) throw await err(res, "Erro ao congelar valuation");
  return res.json();
}

export function canReadFx(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("treasury:fx_read");
}

export function canWriteFx(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("treasury:fx_write");
}

export function canRefreshFxQuote(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("treasury:fx_quote_refresh");
}

export function fmtFx(value: string | null | undefined) {
  if (value == null || value === "") return "—";
  return value;
}
