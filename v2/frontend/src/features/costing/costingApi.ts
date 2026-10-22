const jsonHeaders = { "Content-Type": "application/json" };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    credentials: "include",
    ...init,
    headers: { ...jsonHeaders, ...(init?.headers ?? {}) },
  });
  if (!r.ok) {
    const j = (await r.json().catch(() => ({}))) as { message?: string; error?: string; details?: unknown };
    const err = new Error(j.message || r.statusText) as Error & {
      status?: number;
      code?: string;
      details?: unknown;
    };
    err.status = r.status;
    err.code = j.error;
    err.details = j.details;
    throw err;
  }
  if (r.status === 204) return undefined as T;
  return r.json() as Promise<T>;
}

export type CostingQueueRow = {
  id: number | null;
  import_process_id: number;
  process_code: string;
  process_reference: string | null;
  process_status: string;
  current_kind: string | null;
  current_status: string | null;
  included_total_brl: string | null;
  partial_coverage: boolean | null;
  costing_status?: string;
  updated_at: string | null;
};

export type CostingPair = {
  id: number;
  pair_type: string;
  left_label: string;
  left_value: string | null;
  right_label: string;
  right_value: string | null;
  delta: string | null;
  severity: string;
  blocks_publish: boolean;
  status: string;
  reason: string | null;
};

export type CostingExpense = {
  id: number;
  category: string;
  description: string;
  amount: string;
  currency: string;
  expense_date: string | null;
  payee_snapshot: string | null;
  document_id: number | null;
  allocation_method: string;
  status: string;
};

export type CostingVersionSummary = {
  id: number;
  kind: string;
  status: string;
  version_number: number;
  included_total_brl?: string | null;
  published_at?: string | null;
  created_at?: string | null;
  partial_coverage?: boolean;
};

export type CostingVersion = {
  id: number;
  case_id: number;
  kind: string;
  status: string;
  version_number: number;
  partial_coverage: boolean;
  included_total_brl: string | null;
  gross_total_brl: string | null;
  title: string;
  subtitle: string;
  pairs: CostingPair[];
  products: Array<{
    sku_snapshot: string;
    description_snapshot?: string;
    qty: string;
    merchandise_brl?: string | null;
    freight_brl?: string | null;
    tax_brl?: string | null;
    expense_brl?: string | null;
    total_brl: string | null;
    unit_brl: string | null;
  }>;
  components: Array<{
    id: number;
    component_type: string;
    source_kind: string;
    amount_brl: string | null;
    included: boolean;
    status: string;
    notes: string | null;
    allocation_method: string;
  }>;
  expenses?: CostingExpense[];
  lines: Array<{
    id: number;
    sku_snapshot: string;
    qty: string;
    foreign_net: string | null;
    merchandise_brl: string | null;
    fx_status: string;
  }>;
  snapshot: {
    coverage?: {
      coverage?: string;
      reasons?: string[];
      process_invoice_numbers?: string[];
      mentioned_invoice_refs?: string[];
      extra_refs?: string[];
      invoice_count?: number;
      mentioned_count?: number;
      fob_amount?: string | null;
      fob_currency?: string | null;
      merchandise_foreign?: string | null;
      merchandise_currency?: string | null;
      freight_conflict?: boolean;
      freight_basis?: { amount?: string; currency?: string; label?: string; code?: string } | null;
      international_freight_count?: number;
      domestic_freight_count?: number;
      funding_included?: boolean;
    };
    invoices?: Array<{ invoice_number?: string; net_amount?: string | null; fx?: { initial_rate?: string } }>;
    fx?: { kind?: string; statuses?: string[]; documentary_rate?: string | null };
  };
  freight_choice?: string | null;
  published_at?: string | null;
  created_at?: string | null;
};

export type CostingCase = {
  id: number;
  import_process_id: number;
  process_code: string;
  process_reference: string | null;
  process_status: string;
  freight_choice: string | null;
  title: string;
  subtitle: string;
  versions?: CostingVersionSummary[];
};

export type CostingCompare = {
  left: CostingVersionSummary & {
    case_id?: number;
    included_total_brl: string | null;
    kind: string;
    status: string;
    version_number: number;
    published_at?: string | null;
  };
  right: CostingVersionSummary & {
    case_id?: number;
    included_total_brl: string | null;
    kind: string;
    status: string;
    version_number: number;
    published_at?: string | null;
  };
  products: Array<{
    sku_snapshot: string;
    product_id: number | null;
    description_snapshot?: string | null;
    left_qty?: string | null;
    right_qty?: string | null;
    left_total_brl: string | null;
    right_total_brl: string | null;
    left_unit_brl: string | null;
    right_unit_brl: string | null;
  }>;
  components: Array<{
    component_type: string;
    source_kind: string;
    left_amount_brl: string | null;
    right_amount_brl: string | null;
    left_included: boolean | null;
    right_included: boolean | null;
  }>;
};

export function listCostingQueue() {
  return api<CostingQueueRow[]>("/api/costing/queue");
}

export function ensureCostingCase(processId: number) {
  return api<CostingCase>("/api/costing/cases", {
    method: "POST",
    body: JSON.stringify({ process_id: processId }),
  });
}

export function getCostingCase(caseId: number) {
  return api<CostingCase>(`/api/costing/cases/${caseId}`);
}

export function recalculateCosting(caseId: number, kind: string) {
  return api<CostingVersion>(`/api/costing/cases/${caseId}/recalculate`, {
    method: "POST",
    body: JSON.stringify({ kind }),
  });
}

export function publishCosting(versionId: number, body: { reason?: string; allow_partial?: boolean }) {
  return api<CostingVersion>(`/api/costing/versions/${versionId}/publish`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getCostingVersion(versionId: number) {
  return api<CostingVersion>(`/api/costing/versions/${versionId}`);
}

export function reviseCosting(versionId: number, kind = "REVISED") {
  return api<CostingVersion>(`/api/costing/versions/${versionId}/revise`, {
    method: "POST",
    body: JSON.stringify({ kind }),
  });
}

export function compareCostingVersions(leftId: number, rightId: number) {
  return api<CostingCompare>(`/api/costing/versions/${leftId}/compare/${rightId}`);
}

export function setFreightChoice(caseId: number, choice: string, reason: string) {
  return api<CostingCase>(`/api/costing/cases/${caseId}/freight-choice`, {
    method: "POST",
    body: JSON.stringify({ choice, reason }),
  });
}

export type AddExpenseBody = {
  category: string;
  description: string;
  amount: string;
  currency?: string;
  expense_date?: string | null;
  payee_snapshot?: string | null;
  document_id?: number | null;
  allocation_method?: string;
};

export function addCostingExpense(caseId: number, body: AddExpenseBody) {
  return api<{ id: number; status: string; amount: string }>(`/api/costing/cases/${caseId}/expenses`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function uploadCostingDocument(caseId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", "costing_case");
  form.append("entity_id", String(caseId));
  form.append("role", "supporting");
  const res = await fetch("/api/documents", { method: "POST", body: form, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "Erro ao anexar documento");
  }
  return res.json() as Promise<{ id: number; original_filename?: string }>;
}

export function resolvePair(pairId: number, reason: string) {
  return api(`/api/reconciliation/pairs/${pairId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ reason, resolution: "ACCEPTED" }),
  });
}
