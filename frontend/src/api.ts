export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  permissions: string[];
  last_login: string | null;
}

export interface Supplier {
  id: number;
  name: string;
  country: string | null;
  currency_default: string | null;
  is_active: boolean;
}

export interface Product {
  id: number;
  sku_code: string;
  description: string;
  ncm: string | null;
  category?: string | null;
  is_active: boolean;
}

export interface Importation {
  id: number;
  po_number: string;
  supplier_id: number;
  currency: string;
  incoterm: string | null;
  estimated_total: string | null;
  current_status: string;
  brazil_operational_notes?: string | null;
  priority?: string | null;
  responsible?: string | null;
  internal_forecast_date?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface BrazilFieldsUpdate {
  brazil_operational_notes?: string | null;
  priority?: string | null;
  responsible?: string | null;
  internal_forecast_date?: string | null;
}

export interface OrderQueueRow {
  id: number;
  po_number: string;
  supplier_id: number;
  supplier_name: string | null;
  status: string;
  currency: string;
  total_invoiced: string | null;
  total_paid: string | null;
  consolidated_balance: string | null;
  totals_by_currency?: Record<string, { total_invoiced: string | null; total_paid: string | null; consolidated_balance: string | null }> | null;
  to_dispatch: number | null;
  qty_ordered?: number | null;
  qty_invoiced?: number | null;
  qty_shipped?: number | null;
  products_count?: number;
  invoices_count?: number;
  invoices_settled_count?: number;
  docs_pending_count?: number;
  next_due_date?: string | null;
  overdue_count?: number;
  priority?: string | null;
  responsible?: string | null;
  internal_forecast_date?: string | null;
  brazil_operational_notes?: string | null;
  pending_actions_count: number;
  updated_at: string | null;
  created_at: string;
}

export interface OrderQueueResponse {
  items: OrderQueueRow[];
  total: number;
}

export interface OrderCentralInvoiceItem {
  id: number;
  importation_item_id: number | null;
  product_id: number | null;
  product_sku: string | null;
  description: string | null;
  quantity: number | null;
  unit_price: string | null;
  amount: string | null;
}

export interface OrderCentralInvoice {
  id: number;
  invoice_type: string;
  invoice_number: string;
  invoice_date: string | null;
  amount: string | null;
  currency: string;
  discount_amount: string | null;
  balance: string | null;
  paid_total: string | null;
  items: OrderCentralInvoiceItem[];
}

export interface OrderCentralModel {
  importation_item_id: number;
  product_id: number | null;
  supplier_sku: string | null;
  description?: string | null;
  product_sku?: string | null;
  product_category?: string | null;
  model_label: string | null;
  quantity_ordered: number | null;
  quantity_shipped: number | null;
  quantity_nationalized: number | null;
  quantity_stocked: number | null;
  quantity_invoiced: number | null;
  to_dispatch: number | null;
  price_listino?: string | null;
  price_fattura?: string | null;
  discount_unit?: string | null;
  acconto_amount?: string | null;
  credit_remaining?: string | null;
  heroes_source?: boolean;
  dispatch_needs_review?: boolean;
}

export interface LegacySheetSummary {
  versato_amount: string | null;
  versato_currency: string | null;
  versato_source: string | null;
  versato_confidence: number | null;
  sheet_name: string | null;
  source: string;
}

export interface StatusRailStage {
  key: string;
  label: string;
  state: "done" | "now" | "todo" | "declared_without_data";
  data_supported: boolean;
  status_declared: boolean;
  subtitle?: string | null;
}

export interface CurrencyTotals {
  total_invoiced: string | null;
  total_paid: string | null;
  total_discounts: string | null;
  consolidated_balance: string | null;
}

export interface OperationalHeader {
  invoices_count: number;
  invoices_settled_count: number;
  totals_by_currency: Record<string, CurrencyTotals> | null;
  total_invoiced: string | null;
  total_paid: string | null;
  open_balance: string | null;
  open_balance_brl_equivalent: string | null;
  next_due_date: string | null;
  overdue_count: number;
  overdue_amount_foreign: string | null;
  next_etd: string | null;
  next_eta: string | null;
  active_modal: string | null;
  to_dispatch: number | null;
  quantity_ordered: number | null;
  supplier_credit_available: string | null;
  pending_actions_count: number;
}

export interface StatusRail {
  stages: StatusRailStage[];
  current_index: number;
  alerts: string[];
}

export interface OrderCentralResponse {
  order: Importation;
  supplier_name: string | null;
  legacy_sheet_summary: LegacySheetSummary | null;
  dispatch_pending: Array<Record<string, unknown>>;
  status_rail: StatusRail | null;
  operational_header: OperationalHeader;
  kpis: {
    currency: string;
    total_invoiced: string | null;
    total_paid: string | null;
    consolidated_balance: string | null;
    to_dispatch: number | null;
    versato_heroes?: string | null;
    versato_heroes_currency?: string | null;
  };
  invoices: OrderCentralInvoice[];
  models: OrderCentralModel[];
  payments_planned: Payment[];
  payments_settled: Payment[];
  pending_actions: Array<{ kind: string; label: string; detail: string | null; tone: string }>;
}

export interface ImportationItem {
  id: number;
  importation_id: number;
  product_id: number | null;
  supplier_sku?: string | null;
  description?: string | null;
  quantity_ordered: number | null;
  unit_price_foreign: string | null;
  discount_amount_foreign?: string | null;
  is_active?: boolean;
}

export interface Invoice {
  id: number;
  importation_id: number;
  invoice_type: string;
  invoice_number: string;
  invoice_date: string | null;
  amount: string | null;
  currency: string;
  discount_amount: string | null;
  balance: string | null;
  paid_total: string | null;
  payment_status: string | null;
  is_active: boolean;
}

export interface InvoiceItem {
  id: number;
  invoice_id: number;
  importation_item_id: number | null;
  product_id: number | null;
  quantity: number | null;
  unit_price: string | null;
  amount: string | null;
}

export interface FinancialSummary {
  importation_id: number;
  currency: string;
  total_invoiced: string;
  total_paid: string;
  total_discounts: string;
  consolidated_balance: string | null;
  invoices: Array<{
    invoice_id: number;
    invoice_number: string;
    invoice_type: string;
    amount: string | null;
    paid: string;
    discounts: string;
    balance: string | null;
  }>;
}

export interface Payment {
  id: number;
  invoice_id: number;
  payment_type: string;
  payment_date: string | null;
  due_date: string | null;
  amount_foreign: string | null;
  amount_local: string | null;
  exchange_rate: string | null;
  currency_foreign: string | null;
  receipt_reference: string | null;
  is_active: boolean;
}

export interface Credit {
  id: number;
  supplier_id: number;
  amount: string;
  amount_used: string;
  amount_available: string;
  currency: string;
  status: string;
}

export interface Discount {
  id: number;
  invoice_id: number;
  importation_item_id: number | null;
  discount_type: string;
  amount: string | null;
  currency: string;
  reason: string | null;
  source_document_ref: string | null;
  is_active: boolean;
}

export interface BrazilAccount {
  id: number;
  supplier_id: number;
  description: string;
  amount: string;
  currency: string;
  amount_available: string;
  financial_impact_estimated: string | null;
  fiscal_impact_estimated: string | null;
  status: string;
  is_active: boolean;
}

export interface Expense {
  id: number;
  importation_id: number;
  expense_type: string;
  description: string | null;
  amount: string | null;
  currency: string;
  source_document_ref: string | null;
  is_included_in_landed_cost: boolean;
  is_active: boolean;
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const authApi = {
  login: (email: string, password: string) =>
    api<User>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () =>
    api<{ message: string }>("/api/auth/logout", { method: "POST" }),
  me: () => api<User>("/api/auth/me"),
};

export const healthApi = {
  check: () =>
    api<{ status: string; app: string; database: string }>("/api/health"),
};

export const suppliersApi = {
  list: () => api<Supplier[]>("/api/suppliers"),
  get: (id: number) => api<Supplier>(`/api/suppliers/${id}`),
  create: (data: { name: string; country?: string; currency_default?: string }) =>
    api<Supplier>("/api/suppliers", { method: "POST", body: JSON.stringify(data) }),
};

export const productsApi = {
  list: () => api<Product[]>("/api/products"),
  create: (data: { sku_code: string; description: string; ncm?: string; category?: string }) =>
    api<Product>("/api/products", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: { description?: string; ncm?: string; category?: string }) =>
    api<Product>(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
};

export const importationsApi = {
  list: () => api<Importation[]>("/api/importations"),
  get: (id: number) => api<Importation>(`/api/importations/${id}`),
  items: (id: number) => api<ImportationItem[]>(`/api/importations/${id}/items`),
  orderCentral: (id: number) => api<OrderCentralResponse>(`/api/importations/${id}/order-central`),
  orderQueue: (limit = 200) => api<OrderQueueResponse>(`/api/importations/order-queue?limit=${limit}`),
  create: (data: object) =>
    api<Importation>("/api/importations", { method: "POST", body: JSON.stringify(data) }),
  transition: (id: number, new_status: string, reason?: string | null) =>
    api<Importation>(`/api/importations/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ new_status, reason: reason ?? null }),
    }),
  allowedTransitions: (id: number) =>
    api<{ current_status: string; transitions: Array<{ status: string; blocked: boolean; block_reason: string | null }> }>(
      `/api/importations/${id}/allowed-transitions`
    ),
  italyOverride: (id: number, data: {
    entity_type: "invoice" | "invoice_item";
    entity_id: number;
    field_name: string;
    new_value: string;
    reason: string;
    attachment_id: number;
  }) =>
    api<{ entity_type: string; entity_id: number; field_name: string; old_value: string | null; new_value: string }>(
      `/api/importations/${id}/italy-overrides`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  updateBrazilNotes: (id: number, brazil_operational_notes: string | null) =>
    api<Importation>(`/api/importations/${id}/brazil-fields`, {
      method: "PATCH",
      body: JSON.stringify({ brazil_operational_notes }),
    }),
  updateBrazilFields: (id: number, data: BrazilFieldsUpdate) =>
    api<Importation>(`/api/importations/${id}/brazil-fields`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  addItem: (id: number, data: object) =>
    api<ImportationItem>(`/api/importations/${id}/items`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateItemMapping: (
    id: number,
    itemId: number,
    data: { product_id?: number | null; description?: string | null; supplier_sku?: string | null },
  ) =>
    api<ImportationItem>(`/api/importations/${id}/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

export const invoicesApi = {
  list: (importationId?: number) =>
    api<Invoice[]>(
      importationId ? `/api/invoices?importation_id=${importationId}` : "/api/invoices"
    ),
  items: (invoiceId: number) => api<InvoiceItem[]>(`/api/invoices/${invoiceId}/items`),
  create: (data: object) =>
    api<Invoice>("/api/invoices", { method: "POST", body: JSON.stringify(data) }),
};

async function apiForm<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface DocumentAttachment {
  id: number;
  document_key: string;
  version: number;
  is_current_version: boolean;
  file_hash: string;
  original_filename: string;
  entity_type: string;
  entity_id: string;
  document_type: string | null;
}

export interface ReviewQueueItem {
  id: number;
  staging_row_id: number;
  status: string;
  reason: string;
  priority: number;
  staging_row?: { row_number: number; parsed_data_json: Record<string, string | null> };
}

export interface Shipment {
  id: number;
  importation_id: number;
  shipment_number: string;
  modal: string;
  modal_previous: string | null;
  bl_number: string | null;
  awb_number: string | null;
  status: string;
}

export interface ModalChangeLog {
  id: number;
  from_modal: string;
  to_modal: string;
  comment: string | null;
  timestamp: string;
}

export const documentsApi = {
  list: (entityType?: string, entityId?: string) => {
    const q = new URLSearchParams();
    if (entityType) q.set("entity_type", entityType);
    if (entityId) q.set("entity_id", entityId);
    return api<DocumentAttachment[]>(`/api/documents?${q}`);
  },
  upload: (file: File, entityType: string, entityId: string, documentType?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("entity_type", entityType);
    fd.append("entity_id", entityId);
    if (documentType) fd.append("document_type", documentType);
    return apiForm<DocumentAttachment>("/api/documents/upload", fd);
  },
};

export const importsApi = {
  reviewQueue: () => api<ReviewQueueItem[]>("/api/imports/review-queue"),
  uploadHeroes: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiForm<{ id: number; row_count: number | null }>("/api/imports/heroes/upload", fd);
  },
  locateHeroesWorkbook: () => api<HeroesWorkbookLocateResponse>("/api/imports/heroes/xlsx/locate"),
  profileHeroesWorkbook: () =>
    api<HeroesWorkbookProfileResponse>("/api/imports/heroes/xlsx/profile", { method: "POST" }),
  loadHeroesWorkbookLocal: () =>
    api<HeroesXlsxUploadResponse>("/api/imports/heroes/xlsx/load-local", { method: "POST" }),
  uploadHeroesXlsx: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiForm<HeroesXlsxUploadResponse>("/api/imports/heroes/xlsx/upload", fd);
  },
  previewHeroesXlsx: (rawFileId: number, sheetName: string, confirmedOrderNumber?: string) =>
    api<HeroesXlsxPreviewResponse>("/api/imports/heroes/xlsx/preview", {
      method: "POST",
      body: JSON.stringify({
        raw_file_id: rawFileId,
        sheet_name: sheetName,
        confirmed_order_number: confirmedOrderNumber ?? null,
      }),
    }),
  commitHeroesXlsx: (
    runId: number,
    opts?: {
      categoryOverrides?: Record<string, string>;
      confirmedOrderNumber?: string;
      confirmSheetMatch?: boolean;
      confirmImport?: boolean;
    },
  ) =>
    api<HeroesXlsxCommitResponse>("/api/imports/heroes/xlsx/commit", {
      method: "POST",
      body: JSON.stringify({
        run_id: runId,
        category_overrides: opts?.categoryOverrides ?? null,
        confirmed_order_number: opts?.confirmedOrderNumber ?? null,
        confirm_sheet_match: opts?.confirmSheetMatch ?? false,
        confirm_import: opts?.confirmImport ?? false,
      }),
    }),
  exportHeroesNormalized: async (runId: number, format: "xlsx" | "zip" = "xlsx") => {
    const res = await fetch("/api/imports/heroes/xlsx/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ run_id: runId, format }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  },
  resetOperational: () => api<Record<string, unknown>>("/api/imports/reset-operational", { method: "POST" }),
  approveStaging: (stagingId: number) =>
    api(`/api/imports/staging/${stagingId}/approve`, { method: "POST" }),
};

export interface HeroesWorkbookProfileSheet {
  sheet_name: string;
  sheet_type: string;
  order_number_from_sheet_name: string | null;
  order_number_from_content: string | null;
  order_number_divergence: boolean;
  parser_confidence: number;
  recommendation: string;
  warnings: string[];
  merged_cell_count: number;
}

export interface HeroesWorkbookProfileResponse {
  profiler_version: string;
  source_file: string | null;
  resolved_path: string | null;
  file_checksum: string;
  sheet_count: number;
  sheets: HeroesWorkbookProfileSheet[];
  database_writes: boolean;
  read_only_mode: boolean;
  note: string | null;
}

export interface HeroesWorkbookLocateResponse {
  found: boolean;
  resolved_path: string | null;
  search_paths: string[];
}

export interface HeroesXlsxSheetInfo {
  sheet_name: string;
  sheet_type: string;
  order_number_hint: string | null;
  order_number_from_content?: string | null;
  order_number_divergence?: boolean;
  parser_confidence?: number | null;
  recommendation?: string | null;
}

export interface HeroesXlsxUploadResponse {
  raw_file_id: number;
  file_checksum: string;
  sheets: HeroesXlsxSheetInfo[];
  workbook_profile?: HeroesWorkbookProfileResponse | null;
  source_path?: string | null;
}

export interface HeroesXlsxPreviewResponse {
  run_id: number;
  status: string;
  sheet_name: string;
  sheet_type: string;
  order_number: string | null;
  order_number_from_sheet_name?: string | null;
  order_number_from_content?: string | null;
  order_number_divergence?: boolean;
  preview: Record<string, unknown>;
  canonical?: Record<string, unknown> | null;
  warnings: string[] | null;
  errors: string[] | null;
  already_committed: boolean;
  importation_id: number | null;
}

export interface HeroesXlsxCommitResponse {
  importation_id: number;
  po_number: string;
  run_id: number;
}

export const shipmentsApi = {
  list: (importationId: number) => {
    if (!importationId || Number.isNaN(importationId)) {
      return Promise.reject(new Error("importation_id obrigatório"));
    }
    return api<Shipment[]>(`/api/shipments?importation_id=${importationId}`);
  },
  create: (data: object) =>
    api<Shipment>("/api/shipments", { method: "POST", body: JSON.stringify(data) }),
  changeModal: (shipmentId: number, data: object) =>
    api<Shipment>(`/api/shipments/${shipmentId}/change-modal`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  modalHistory: (shipmentId: number) =>
    api<ModalChangeLog[]>(`/api/shipments/${shipmentId}/modal-history`),
  quantitySummary: (importationId: number) =>
    api<Array<{ importation_item_id: number; quantity_ordered: number | null; quantity_shipped: number }>>(
      `/api/shipments/importations/${importationId}/quantity-summary`
    ),
};

export const financeApi = {
  summary: (importationId: number) =>
    api<FinancialSummary>(`/api/finance/importations/${importationId}/summary`),
  createPayment: (data: object) =>
    api<Payment>("/api/finance/payments", { method: "POST", body: JSON.stringify(data) }),
  updatePayment: (id: number, data: object) =>
    api<Payment>(`/api/finance/payments/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  listPayments: (invoiceId?: number) =>
    api<Payment[]>(
      invoiceId != null ? `/api/finance/payments?invoice_id=${invoiceId}` : "/api/finance/payments"
    ),
  createDiscount: (data: object) =>
    api<Discount>("/api/finance/discounts", { method: "POST", body: JSON.stringify(data) }),
  listDiscounts: (opts?: { invoiceId?: number; importationId?: number }) => {
    const params = new URLSearchParams();
    if (opts?.invoiceId != null) params.set("invoice_id", String(opts.invoiceId));
    else if (opts?.importationId != null) params.set("importation_id", String(opts.importationId));
    const q = params.toString();
    return api<Discount[]>(`/api/finance/discounts${q ? `?${q}` : ""}`);
  },
  listCredits: (supplierId?: number) =>
    api<Credit[]>(
      supplierId != null ? `/api/finance/credits?supplier_id=${supplierId}` : "/api/finance/credits"
    ),
  createCredit: (data: object) =>
    api<Credit>("/api/finance/credits", { method: "POST", body: JSON.stringify(data) }),
  applyCredit: (creditId: number, data: object) =>
    api<{ credit_usage_id: number; amount_used: string }>(
      `/api/finance/credits/${creditId}/apply`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  listBrazilAccounts: (supplierId?: number) =>
    api<BrazilAccount[]>(
      supplierId != null
        ? `/api/finance/brazil-accounts?supplier_id=${supplierId}`
        : "/api/finance/brazil-accounts"
    ),
  createBrazilAccount: (data: object) =>
    api<BrazilAccount>("/api/finance/brazil-accounts", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listExpenses: (importationId: number) =>
    api<Expense[]>(`/api/finance/expenses?importation_id=${importationId}`),
  createExpense: (data: object) =>
    api<Expense>("/api/finance/expenses", { method: "POST", body: JSON.stringify(data) }),
};

export interface CustomsDocument {
  id: number;
  importation_id: number;
  document_type: string;
  document_number: string;
  document_data_json: Record<string, unknown> | null;
  official_data_json: Record<string, unknown> | null;
  status: string;
  is_valid: boolean;
}

export interface Tax {
  id: number;
  importation_id: number;
  customs_document_id: number;
  tax_type: string;
  amount: string;
  currency: string;
}

export interface QuantityChain {
  importation_item_id: number;
  quantity_ordered: number | null;
  quantity_shipped: number;
  quantity_nationalized: number;
  quantity_stocked: number;
  difference_ordered_stocked: number | null;
}

export interface LandedCostVersion {
  id: number;
  importation_id: number;
  version_number: number;
  version_type: string;
  is_current_version: boolean;
  previous_version_id: number | null;
  total_cost: string | null;
  trigger_event: string | null;
  created_at: string;
  allocations: Array<{
    importation_item_id: number;
    allocated_amount: string;
    allocation_method: string;
    unit_cost: string | null;
  }>;
}

export const customsApi = {
  listDocuments: (importationId: number) =>
    api<CustomsDocument[]>(`/api/customs/documents?importation_id=${importationId}`),
  createDocument: (data: object) =>
    api<CustomsDocument>("/api/customs/documents", { method: "POST", body: JSON.stringify(data) }),
  approveDocument: (id: number, data: object) =>
    api<CustomsDocument>(`/api/customs/documents/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listTaxes: (importationId: number) =>
    api<Tax[]>(`/api/customs/taxes?importation_id=${importationId}`),
  createTax: (data: object) =>
    api<Tax>("/api/customs/taxes", { method: "POST", body: JSON.stringify(data) }),
};

export const stockApi = {
  quantityChain: (importationId: number) =>
    api<QuantityChain[]>(`/api/stock/importations/${importationId}/quantity-chain`),
  createNationalization: (data: object) =>
    api("/api/stock/nationalizations", { method: "POST", body: JSON.stringify(data) }),
  createStockEntry: (data: object) =>
    api("/api/stock/entries", { method: "POST", body: JSON.stringify(data) }),
};

export const landedCostApi = {
  listVersions: (importationId: number) =>
    api<LandedCostVersion[]>(`/api/landed-cost/importations/${importationId}/versions`),
  createVersion: (data: object) =>
    api<LandedCostVersion>("/api/landed-cost/versions", { method: "POST", body: JSON.stringify(data) }),
};

export interface Reconciliation {
  id: number;
  importation_id: number;
  pair_type: string;
  label: string;
  status: string;
  severity: string;
  variance_value: string | null;
  source_a_value: string | null;
  source_b_value: string | null;
}

export interface ClosureRecord {
  id: number;
  importation_id: number;
  closure_version: number;
  closure_type: string;
  status: string;
  closed_at: string;
  snapshot_json: Record<string, unknown>;
}

export interface TimelineEvent {
  type: string;
  timestamp: string;
  action?: string;
  from_status?: string;
  to_status?: string;
  comment?: string;
  entity_type?: string;
  entity_label?: string;
  field_changed?: string;
  old_value?: string;
  new_value?: string;
  user_name?: string | null;
  justification?: string | null;
  summary?: string;
}

export interface ReasonCode {
  id: number;
  code: string;
  category: string;
  label: string;
  requires_comment: boolean;
}

export const usersApi = {
  listReasonCodes: () => api<ReasonCode[]>("/api/users/reason-codes"),
};

export const dashboardApi = {
  summary: () => api<DashboardSummary>("/api/dashboard/summary"),
  importations: (limit = 100) =>
    api<DashboardImportationsPayload>(`/api/dashboard/importations?limit=${limit}`),
};

export interface DashboardDataAvailability {
  payments_due: boolean;
  eta: boolean;
  monthly_stock_trend: boolean;
  fx_rate: boolean;
}

export interface DashboardSummary {
  open_importations_count: number;
  open_value_by_currency: Record<string, string | null>;
  divergence_importations_count: number;
  divergence_reconciliations_count: number;
  stocked_units_total: number;
  review_queue_count: number;
  stage_counts: Array<{ label: string; count: number }>;
  closure_pending_importations_count: number;
  payments_due_count: number;
  payments_overdue_count: number;
  payments_due_amount_by_currency: Record<string, string>;
  payments_due_window_days: number;
  data_availability: DashboardDataAvailability;
}

export interface DashboardImportationsPayload {
  items: DashboardImportationApiRow[];
  total_open: number;
}

export interface DashboardImportationApiRow {
  id: number;
  po_number: string;
  status: string;
  supplier_name: string;
  currency: string;
  created_at: string;
  modal: string | null;
  stage_index: number;
  in_transit: boolean;
  open_value: string | null;
  stocked_qty: number;
  has_divergence: boolean;
  divergence_count: number;
  lc_estimated: string | null;
  lc_actual: string | null;
  eta: string | null;
  closure_pending_count: number;
  action_items: Array<{ kind: string; label: string; detail: string; tone: string }>;
  pending_payments: Array<{
    payment_id: number | null;
    invoice_id: number;
    invoice_number: string;
    invoice_type: string;
    balance: string | null;
    currency: string;
    due_date: string | null;
    is_overdue: boolean;
  }>;
}

export const demoApi = {
  seed: () => api<Record<string, number>>("/api/demo/seed", { method: "POST" }),
};

export const reconciliationApi = {
  list: (importationId: number) =>
    api<Reconciliation[]>(`/api/reconciliation/importations/${importationId}`),
  run: (importationId: number) =>
    api<Reconciliation[]>(`/api/reconciliation/importations/${importationId}/run`, { method: "POST" }),
  approve: (id: number, data: object) =>
    api<Reconciliation>(`/api/reconciliation/${id}/approve`, { method: "POST", body: JSON.stringify(data) }),
};

export const closureApi = {
  checklist: (importationId: number) =>
    api<Array<{ id: string; label: string; passed: boolean; blocking_count?: number }>>(
      `/api/closure/importations/${importationId}/checklist`
    ),
  close: (importationId: number, data: object) =>
    api<ClosureRecord>(`/api/closure/importations/${importationId}/close`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  reopen: (importationId: number, data: object) =>
    api(`/api/closure/importations/${importationId}/reopen`, { method: "POST", body: JSON.stringify(data) }),
  history: (importationId: number) =>
    api<ClosureRecord[]>(`/api/closure/importations/${importationId}/history`),
  timeline: (importationId: number) =>
    api<TimelineEvent[]>(`/api/closure/importations/${importationId}/timeline`),
};
