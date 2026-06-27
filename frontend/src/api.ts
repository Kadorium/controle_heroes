export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  permissions: string[];
  last_login: string | null;
}

export interface AdminUser extends User {
  is_active: boolean;
  created_at?: string | null;
  cancelled_at?: string | null;
}

export interface RoleOption {
  name: string;
  description: string | null;
}

export interface Supplier {
  id: number;
  name: string;
  country: string | null;
  tax_id: string | null;
  contact_name: string | null;
  contact_email: string | null;
  currency_default: string | null;
  is_active: boolean;
}

export interface Product {
  id: number;
  sku_code: string;
  description: string;
  ncm: string | null;
  weight_kg?: string | null;
  volume_m3?: string | null;
  category?: string | null;
  lifecycle_status?: string | null;
  product_group?: string | null;
  product_subgroup?: string | null;
  supplier_code?: string | null;
  default_supplier_id?: number | null;
  default_supplier_name?: string | null;
  country_of_origin?: string | null;
  unit_of_measure?: string | null;
  fiscal_description?: string | null;
  fiscal_review_required?: boolean;
  launch_date?: string | null;
  commercial_notes?: string | null;
  is_active: boolean;
  has_photo?: boolean;
  photo_attachment_id?: number | null;
  pending_flags?: string[];
  last_importation_at?: string | null;
  last_importation_po?: string | null;
  last_landed_cost_unit?: string | null;
  orders_count?: number;
  archived_at?: string | null;
  archive_reason?: string | null;
  cancelled_at?: string | null;
  cancellation_reason?: string | null;
  used_in_importations?: boolean;
}

export interface ProductCatalogResponse {
  items: Product[];
  total: number;
}

export interface ProductAuditRow {
  id: number;
  action: string;
  timestamp: string;
  field_changed: string | null;
  old_value: string | null;
  new_value: string | null;
  justification: string | null;
  user_name: string | null;
}

export interface ProductOrderRow {
  importation_id: number;
  po_number: string;
  current_status: string;
  supplier_name: string | null;
  currency: string;
  qty_ordered: string | null;
  landed_cost_unit: string | null;
  updated_at: string | null;
  created_at: string | null;
}

export interface ProductImportPreviewRow {
  row_number: number;
  sku_code: string | null;
  valid: boolean;
  errors: string[];
  data: Record<string, unknown> | null;
}

export interface BulkActionResult {
  succeeded: number[];
  skipped: Array<{ id: number; reason: string }>;
  failed: Array<{ id: number; error: string }>;
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
  payment_due_date?: string | null;
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
  next_open_invoice_number?: string | null;
  next_open_invoice_balance?: string | null;
  next_etd: string | null;
  next_eta: string | null;
  active_modal: string | null;
  to_dispatch: number | null;
  quantity_ordered: number | null;
  supplier_credit_available: string | null;
  pending_actions_count: number;
  fx_pnl?: FxPnlBlock | null;
  order_total_eur?: string | null;
  order_total_brl?: string | null;
  invoiced_eur?: string | null;
  invoiced_brl?: string | null;
  settled_eur?: string | null;
  settled_brl?: string | null;
  remaining_to_invoice_eur?: string | null;
  remaining_to_invoice_brl?: string | null;
  balance_to_settle_eur?: string | null;
  balance_to_settle_brl?: string | null;
  opening_exchange_rate?: string | null;
}

export interface FxPnlBlock {
  label: string;
  disclaimer: string;
  provision_rate?: string | null;
  mark_rate?: string | null;
  orders_with_pnl?: number | null;
  pnl_realized_brl: string | null;
  pnl_planned_brl: string | null;
  pnl_unrealized_brl: string | null;
  pnl_total_brl: string | null;
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
  operational_header?: OperationalHeader | null;
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
  shipments?: OrderCentralShipment[];
}

export interface OrderCentralShipment {
  id: number;
  importation_id: number;
  shipment_number: string;
  modal: string;
  modal_previous: string | null;
  bl_number: string | null;
  awb_number: string | null;
  container_number: string | null;
  status: string;
  etd_planned: string | null;
  eta_planned: string | null;
  etd_actual: string | null;
  eta_actual: string | null;
  is_active: boolean;
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
    const detail = (body as { detail?: unknown }).detail;
    let message: string;
    if (typeof detail === "string") {
      message =
        detail === "Not Found"
          ? `Recurso não encontrado (${path}). Reinicie o backend e execute alembic upgrade head.`
          : detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ") || `Erro HTTP ${res.status}`;
    } else {
      message = `Erro HTTP ${res.status} (${path})`;
    }
    throw new Error(message);
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

export type SupplierPayload = {
  name?: string;
  country?: string | null;
  tax_id?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  currency_default?: string | null;
};

export const suppliersApi = {
  list: () => api<Supplier[]>("/api/suppliers"),
  get: (id: number) => api<Supplier>(`/api/suppliers/${id}`),
  create: (data: SupplierPayload & { name: string }) =>
    api<Supplier>("/api/suppliers", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: SupplierPayload) =>
    api<Supplier>(`/api/suppliers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  cancel: (id: number, reason: string) =>
    api<Supplier>(`/api/suppliers/${id}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),
};

export const productsApi = {
  list: (params?: { for_combobox?: boolean }) => {
    const qs = params?.for_combobox ? "?for_combobox=true" : "";
    return api<Product[]>(`/api/products${qs}`);
  },
  catalog: (params?: {
    q?: string;
    visibility?: string;
    quick_filter?: string;
    sort?: string;
    sort_dir?: string;
    limit?: number;
    offset?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.q) sp.set("q", params.q);
    if (params?.visibility) sp.set("visibility", params.visibility);
    if (params?.quick_filter) sp.set("quick_filter", params.quick_filter);
    if (params?.sort) sp.set("sort", params.sort);
    if (params?.sort_dir) sp.set("sort_dir", params.sort_dir);
    if (params?.limit != null) sp.set("limit", String(params.limit));
    if (params?.offset != null) sp.set("offset", String(params.offset));
    const q = sp.toString();
    return api<ProductCatalogResponse>(`/api/products/catalog${q ? `?${q}` : ""}`);
  },
  detail: (id: number) => api<Product>(`/api/products/${id}/detail`),
  create: (data: object) => api<Product>("/api/products", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: object) =>
    api<Product>(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  archive: (id: number, reason: string) =>
    api<Product>(`/api/products/${id}/archive`, { method: "POST", body: JSON.stringify({ reason }) }),
  restore: (id: number) => api<Product>(`/api/products/${id}/restore`, { method: "POST" }),
  cancel: (id: number, reason: string) =>
    api<Product>(`/api/products/${id}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),
  orders: (id: number, params?: { q?: string }) => {
    const qs = params?.q ? `?q=${encodeURIComponent(params.q)}` : "";
    return api<{ items: ProductOrderRow[]; total: number }>(`/api/products/${id}/orders${qs}`);
  },
  audit: (id: number) => api<ProductAuditRow[]>(`/api/products/${id}/audit`),
  costHistory: (id: number) =>
    api<{ items: Array<{ importation_id: number; po_number: string; version_number: number; version_type: string; unit_cost: string | null; created_at: string }> }>(
      `/api/products/${id}/cost-history`,
    ),
  importPreview: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiForm<{ valid_count: number; invalid_count: number; rows: ProductImportPreviewRow[] }>(
      "/api/products/import/preview",
      fd,
    );
  },
  importCommit: (rows: ProductImportPreviewRow[]) =>
    api<{ created: number; updated: number; skipped: number; errors: string[] }>(
      "/api/products/import/commit",
      { method: "POST", body: JSON.stringify({ rows, confirm: true }) },
    ),
  bulkArchive: (product_ids: number[], reason: string) =>
    api<BulkActionResult>("/api/products/bulk/archive", {
      method: "POST",
      body: JSON.stringify({ product_ids, reason }),
    }),
  bulkRestore: (product_ids: number[]) =>
    api<BulkActionResult>("/api/products/bulk/restore", {
      method: "POST",
      body: JSON.stringify({ product_ids }),
    }),
  bulkStatus: (product_ids: number[], lifecycle_status: string) =>
    api<BulkActionResult>("/api/products/bulk/status", {
      method: "POST",
      body: JSON.stringify({ product_ids, lifecycle_status }),
    }),
  bulkCancel: (product_ids: number[], reason: string) =>
    api<BulkActionResult>("/api/products/bulk/cancel", {
      method: "POST",
      body: JSON.stringify({ product_ids, reason }),
    }),
  exportBlob: async (format: "csv" | "xlsx" = "xlsx", visibility = "active") => {
    const res = await fetch(`/api/products/export?format=${format}&visibility=${visibility}`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
    return res.blob();
  },
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
  linkHeroesRaw: (importationId: number, rawFileId: number) =>
    api<{ run_id: number; raw_file_id: number; importation_id: number; status: string }>(
      `/api/importations/${importationId}/link-heroes-raw`,
      { method: "POST", body: JSON.stringify({ raw_file_id: rawFileId }) },
    ),
  heroesImportPreview: (importationId: number, sheetName?: string | null) => {
    const q = sheetName ? `?sheet_name=${encodeURIComponent(sheetName)}` : "";
    return api<HeroesImportRunResponse>(`/api/importations/${importationId}/heroes-import/preview${q}`);
  },
  heroesImportCommit: (
    importationId: number,
    opts?: { confirmImport?: boolean; confirmSheetMatch?: boolean; categoryOverrides?: Record<string, string> },
  ) =>
    api<HeroesImportRunResponse>(`/api/importations/${importationId}/heroes-import/commit`, {
      method: "POST",
      body: JSON.stringify({
        confirm_import: opts?.confirmImport ?? false,
        confirm_sheet_match: opts?.confirmSheetMatch ?? false,
        category_overrides: opts?.categoryOverrides ?? null,
      }),
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
  staging_row?: {
    row_number: number;
    parsed_data_json: Record<string, string | number | null>;
  };
}

export interface HeroesImportRunResponse {
  run_id: number;
  importation_id: number;
  status: string;
  sheet_name: string;
  preview: Record<string, unknown>;
  warnings?: string[] | null;
  errors?: string[] | null;
  sku_review_pending: boolean;
  sku_review_open_count: number;
  merge_warnings: string[];
}

export interface Shipment {
  id: number;
  importation_id: number;
  shipment_number: string;
  modal: string;
  modal_previous: string | null;
  bl_number: string | null;
  awb_number: string | null;
  container_number: string | null;
  status: string;
  etd_planned: string | null;
  eta_planned: string | null;
  etd_actual: string | null;
  eta_actual: string | null;
  freight_amount: string | null;
  freight_currency: string | null;
  is_active: boolean;
}

export interface ShipmentItem {
  id: number;
  shipment_id: number;
  importation_item_id: number;
  quantity_shipped: number | null;
  supplier_sku?: string | null;
  description?: string | null;
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
  resolveStagingSku: (stagingId: number, productId: number) =>
    api<{ id: number; parsed_data_json: Record<string, unknown> }>(
      `/api/imports/staging/${stagingId}/resolve-sku`,
      { method: "PATCH", body: JSON.stringify({ product_id: productId }) },
    ),
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
  get: (shipmentId: number) => api<Shipment>(`/api/shipments/${shipmentId}`),
  create: (data: object) =>
    api<Shipment>("/api/shipments", { method: "POST", body: JSON.stringify(data) }),
  update: (shipmentId: number, data: object) =>
    api<Shipment>(`/api/shipments/${shipmentId}`, { method: "PATCH", body: JSON.stringify(data) }),
  listItems: (shipmentId: number) => api<ShipmentItem[]>(`/api/shipments/${shipmentId}/items`),
  addItem: (shipmentId: number, data: object) =>
    api<ShipmentItem>(`/api/shipments/${shipmentId}/items`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
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

export interface FxReference {
  currency_from: string;
  currency_to: string;
  rate: string | null;
  rate_date: string | null;
  source: string | null;
  disclaimer: string;
  errors?: string[] | null;
}

export const financeApi = {
  fxReference: (currencyFrom = "EUR", currencyTo = "BRL") =>
    api<FxReference>(
      `/api/finance/fx-reference?currency_from=${encodeURIComponent(currencyFrom)}&currency_to=${encodeURIComponent(currencyTo)}`,
    ),
  fxPnlSummary: () => api<FxPnlBlock>("/api/finance/fx-pnl/summary"),
  fxPnlForImportation: (importationId: number) =>
    api<FxPnlBlock>(`/api/finance/importations/${importationId}/fx-pnl`),
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
  quantity_shipped: number | null;
  quantity_nationalized: number | null;
  quantity_stocked: number | null;
  quantity_entreposto_balance: number | null;
  quantity_entreposto_consumed: number | null;
  difference_ordered_stocked: number | null;
}

export interface EntrepostoMovement {
  id: number;
  importation_id: number;
  importation_item_id: number;
  movement_type: string;
  quantity: number;
  event_date: string | null;
  shipment_id: number | null;
  notes: string | null;
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
  listEntrepostoMovements: (importationId: number) =>
    api<EntrepostoMovement[]>(`/api/stock/importations/${importationId}/entreposto-movements`),
  createEntrepostoMovement: (data: object) =>
    api<EntrepostoMovement>("/api/stock/entreposto-movements", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  createNationalization: (data: object) =>
    api("/api/stock/nationalizations", { method: "POST", body: JSON.stringify(data) }),
  listNationalizations: (importationId: number) =>
    api<Array<{ id: number; importation_id: number; customs_document_id: number }>>(
      `/api/stock/nationalizations?importation_id=${importationId}`,
    ),
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
  list: (visibility: "active" | "cancelled" | "all" = "active") =>
    api<AdminUser[]>(`/api/users?visibility=${visibility}`),
  get: (id: number) => api<AdminUser>(`/api/users/${id}`),
  listRoles: () => api<RoleOption[]>("/api/users/roles"),
  create: (data: { email: string; name: string; password: string; role_name: string }) =>
    api<AdminUser>("/api/users", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: { name?: string; role_name?: string; password?: string }) =>
    api<AdminUser>(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  cancel: (id: number, data: { reason: string; reason_code?: string }) =>
    api<AdminUser>(`/api/users/${id}/cancel`, { method: "POST", body: JSON.stringify(data) }),
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
