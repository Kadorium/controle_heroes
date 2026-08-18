/** Ingestion API wrappers — J3-I2 (generated OpenAPI client). */

import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type DocumentSummary = components["schemas"]["DocumentSummaryOut"] & {
  created_order_id?: number | null;
  created_order_code?: string | null;
};
export type DocumentDetail = components["schemas"]["DocumentOut"] & {
  created_order_id?: number | null;
  created_order_code?: string | null;
};
export type FieldOut = components["schemas"]["FieldOut"];
export type IssueOut = components["schemas"]["IssueOut"];
export type RowOut = components["schemas"]["RowOut"];
export type PreviewCommitOut = components["schemas"]["PreviewCommitOut"];
export type CommitAttemptOut = components["schemas"]["CommitAttemptOut"];
export type SectionOut = components["schemas"]["SectionOut"];

export class IngestionApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;
  constructor(message: string, status: number, code?: string, details?: Record<string, unknown>) {
    super(message);
    this.name = "IngestionApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function errMessage(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "message" in error) {
    const m = (error as { message?: string }).message;
    if (m) return m;
  }
  return fallback;
}

async function fetchJson<T>(
  url: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(url, { credentials: "include", ...init });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      message?: string;
      error?: string;
      detail?: string;
      details?: Record<string, unknown>;
    };
    const msg = body.message ?? body.error ?? body.detail ?? `Erro ${res.status}`;
    throw new IngestionApiError(msg, res.status, body.error, body.details);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function isVersionConflict(err: unknown): boolean {
  return err instanceof IngestionApiError && err.status === 409;
}

export async function fetchStagingQueue(opts?: {
  review_status?: string;
}): Promise<DocumentSummary[]> {
  const params = new URLSearchParams();
  if (opts?.review_status) params.set("review_status", opts.review_status);
  const qs = params.toString();
  return fetchJson<DocumentSummary[]>(
    `/api/ingestion/staging/queue${qs ? `?${qs}` : ""}`,
  );
}

export async function fetchIngestionDocument(documentId: number): Promise<DocumentDetail> {
  return fetchJson<DocumentDetail>(`/api/ingestion/documents/${documentId}`);
}

export async function correctIngestionField(
  fieldId: number,
  body: { corrected_value: string | null; expected_version: number; reason?: string },
): Promise<FieldOut> {
  const { data, error } = await api.PATCH("/api/ingestion/fields/{field_id}", {
    params: { path: { field_id: fieldId } },
    body,
  });
  if (error) throw new Error(errMessage(error, "Falha ao corrigir campo"));
  if (!data) throw new Error("Resposta vazia");
  return data;
}

export async function setIngestionOrderCode(
  documentId: number,
  body: { order_code: string; expected_version: number; reason?: string },
): Promise<FieldOut> {
  return fetchJson<FieldOut>(`/api/ingestion/documents/${documentId}/order-code`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function restoreIngestionField(
  fieldId: number,
  body: { expected_version: number; reason?: string },
): Promise<FieldOut> {
  const { data, error } = await api.POST("/api/ingestion/fields/{field_id}/restore", {
    params: { path: { field_id: fieldId } },
    body,
  });
  if (error) throw new Error(errMessage(error, "Falha ao restaurar campo"));
  if (!data) throw new Error("Resposta vazia");
  return data;
}

/** Content URL for quarantine PDF (credentials via cookie on same origin). */
export function occurrenceContentUrl(occurrenceId: number): string {
  return `/api/ingestion/occurrences/${occurrenceId}/content`;
}

export async function fetchCommitPreview(documentId: number): Promise<PreviewCommitOut> {
  const { data, error } = await api.GET("/api/ingestion/documents/{document_id}/preview-commit", {
    params: { path: { document_id: documentId } },
  });
  if (error) throw new Error(errMessage(error, "Falha no preview de commit"));
  if (!data) throw new Error("Preview vazio");
  return data;
}

export async function commitIngestionDocument(
  documentId: number,
  body: { operation_key: string },
): Promise<CommitAttemptOut> {
  return fetchJson<CommitAttemptOut>(`/api/ingestion/documents/${documentId}/commit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export type Locator = {
  page?: number;
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  unit?: string;
};

export function parseLocator(locatorJson: string | null | undefined): Locator | null {
  if (!locatorJson) return null;
  try {
    const o = JSON.parse(locatorJson) as Locator;
    if (o && typeof o === "object") return o;
  } catch {
    return null;
  }
  return null;
}

// --- J3-I4: Fattura policy A/B/C1/C2 ---

export type FatturaPolicy = "A" | "B" | "C1" | "C2";

export interface FatturaPolicyMatchOut {
  policy: string;
  order_id: number | null;
  order_status: string | null;
  order_code: string | null;
  invoice_will_be_created: boolean;
  warning: string | null;
}

export interface FatturaPreviewOperationOut {
  op_key: string;
  description: string;
  entity_type: string | null;
  params: Record<string, unknown>;
}

export interface FatturaLineChoiceIn {
  row_index: number;
  order_item_id: number;
}

export interface FatturaOrderCandidateOut {
  order_id: number;
  order_code: string;
  status: string;
  supplier_id: number;
  currency: string;
  evidence: string[];
  currency_match: boolean;
}

export interface FatturaLineCandidateOut {
  order_item_id: number;
  position: number;
  unit_price?: string | null;
  remaining: string;
}

export interface FatturaLineMatchOut {
  row_index: number;
  sku: string;
  pdf_qty: string;
  pdf_unit_price?: string | null;
  order_item_id?: number | null;
  order_unit_price?: string | null;
  remaining_before?: string | null;
  candidate_count: number;
  candidates: FatturaLineCandidateOut[];
  price_mismatch: boolean;
  ambiguous_price: boolean;
  status: string;
}

export interface FatturaPreviewOut {
  document_id: number;
  fingerprint: string;
  policy_match: FatturaPolicyMatchOut;
  operations: FatturaPreviewOperationOut[];
  open_error_count: number;
  can_commit: boolean;
  order_candidates?: FatturaOrderCandidateOut[];
  order_candidates_reason?: string | null;
  line_matches?: FatturaLineMatchOut[];
  already_committed?: boolean;
  last_succeeded_attempt_id?: number | null;
  last_succeeded_invoice_id?: number | null;
}

export interface FatturaCommitIn {
  operation_key: string;
  policy: FatturaPolicy;
  order_id?: number | null;
  c2_confirm?: boolean;
  c2_reason?: string | null;
  line_choices?: FatturaLineChoiceIn[];
}

export async function runAdapterFattura(occurrenceId: number): Promise<DocumentDetail> {
  const res = await fetch(`/api/ingestion/occurrences/${occurrenceId}/run-adapter-fattura`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { message?: string };
    throw new Error(body.message ?? `Erro ${res.status}`);
  }
  return (await res.json()) as DocumentDetail;
}

export async function fetchFatturaPreview(
  documentId: number,
  policy: FatturaPolicy,
  orderId?: number | null,
  c2Confirm?: boolean,
  c2Reason?: string | null,
  lineChoices?: FatturaLineChoiceIn[] | null,
): Promise<FatturaPreviewOut> {
  const params = new URLSearchParams({ policy });
  if (orderId != null) params.set("order_id", String(orderId));
  if (c2Confirm) params.set("c2_confirm", "true");
  if (c2Reason) params.set("c2_reason", c2Reason);
  if (lineChoices && lineChoices.length > 0) {
    params.set("line_choices", JSON.stringify(lineChoices));
  }

  const res = await fetch(
    `/api/ingestion/documents/${documentId}/preview-commit-fattura?${params.toString()}`,
    { credentials: "include" },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { message?: string };
    throw new Error(body.message ?? `Erro ${res.status}`);
  }
  return (await res.json()) as FatturaPreviewOut;
}

export async function commitFatturaDocument(
  documentId: number,
  body: FatturaCommitIn,
): Promise<CommitAttemptOut> {
  const res = await fetch(`/api/ingestion/documents/${documentId}/commit-fattura`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({})) as { message?: string; error?: string };
    throw new Error(b.message ?? b.error ?? `Erro ${res.status}`);
  }
  return (await res.json()) as CommitAttemptOut;
}

// --- J3-I6: Numerário multi-owner ---

export interface NumerarioPreviewOpOut {
  op_key: string;
  description: string;
  entity_type: string | null;
  process_id: number | null;
  params: Record<string, unknown>;
}

export interface NumerarioProcessCandidateOut {
  process_id: number;
  code: string;
  status: string;
  evidence: string[];
}

export interface NumerarioPreviewOut {
  document_id: number;
  fingerprint: string;
  invoice_refs: string[];
  process_ids_input: number[];
  planned_operations: NumerarioPreviewOpOut[];
  open_error_count: number;
  can_commit: boolean;
  process_candidates?: NumerarioProcessCandidateOut[];
  process_candidates_reason?: string | null;
  already_committed?: boolean;
  last_succeeded_attempt_id?: number | null;
  last_succeeded_process_id?: number | null;
  can_create_process?: boolean;
}

export interface NumerarioOpResultOut {
  op_key: string;
  status: string;
  entity_type: string | null;
  entity_id: string | null;
  error_message: string | null;
  details_json: string | null;
}

export interface NumerarioCommitResultOut {
  attempt_id: number;
  document_id: number;
  operation_key: string;
  status: string;
  operations: NumerarioOpResultOut[];
}

export async function runAdapterNumerario(occurrenceId: number): Promise<{ document_id: number; open_issue_count: number }> {
  const res = await fetch(`/api/ingestion/occurrences/${occurrenceId}/run-adapter-numerario`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { message?: string };
    throw new Error(body.message ?? `Erro ${res.status}`);
  }
  return res.json() as Promise<{ document_id: number; open_issue_count: number }>;
}

export async function fetchNumerarioPreview(
  documentId: number,
  processIds: number[],
): Promise<NumerarioPreviewOut> {
  const params = new URLSearchParams({ process_ids: processIds.join(",") });
  const res = await fetch(
    `/api/ingestion/documents/${documentId}/preview-numerario?${params.toString()}`,
    { credentials: "include" },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { message?: string };
    throw new Error(body.message ?? `Erro ${res.status}`);
  }
  return res.json() as Promise<NumerarioPreviewOut>;
}

export async function commitNumerarioDocument(
  documentId: number,
  body: { operation_key: string; process_ids: number[]; create_process?: boolean },
): Promise<NumerarioCommitResultOut> {
  const res = await fetch(`/api/ingestion/documents/${documentId}/commit-numerario`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({})) as { message?: string; error?: string };
    throw new Error(b.message ?? b.error ?? `Erro ${res.status}`);
  }
  return res.json() as Promise<NumerarioCommitResultOut>;
}

// --- J3-UIV: intake, workspace, dossier, catalog ---

export interface OccurrenceOut {
  id: number;
  batch_id: number;
  blob_id: number | null;
  status: string;
  original_filename: string;
  declared_mime: string | null;
  detected_mime: string | null;
  size_bytes: number;
  sha256: string | null;
  client_upload_key: string | null;
  rejection_reason: string | null;
  physical_reuse: boolean;
  rehydrated: boolean;
  retain_until: string | null;
  bytes_purged_at: string | null;
  blob_physical_status: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface BatchOut {
  id: number;
  status: string;
  created_by_actor_id: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  occurrences: OccurrenceOut[];
}

export interface UploadResponse {
  batch_id: number;
  results: OccurrenceOut[];
}

export interface ClassifySuggestion {
  adapter_id: string;
  doc_type: string;
  label: string;
  confidence: string;
  explanation: string;
}

export interface ClassifyOut {
  suggestions: ClassifySuggestion[];
}

export interface AdapterInfo {
  adapter_id: string;
  doc_type: string;
  label: string;
  adapter_version: string;
  mime_kinds?: string[];
}

export interface DocumentSetOut {
  id: number;
  batch_id: number | null;
  projection_key: string | null;
  label: string | null;
  created_by_actor_id: string | null;
  created_at: string | null;
  members: { id: number; document_set_id: number; document_id: number; role: string | null }[];
}

export interface ReconciliationIssueOut {
  code: string;
  severity: string;
  message: string;
  doc_types: string[];
}

export interface DossierPreviewOut {
  document_set_id: number;
  documents_found: string[];
  reconciliation_issues: ReconciliationIssueOut[];
  planned_operations: { op_key: string; description: string; entity_type: string | null }[];
  can_commit: boolean;
}

export interface CatalogSupplier {
  id: number;
  code: string | null;
  name: string;
  is_active?: boolean;
}

export interface CatalogProduct {
  id: number;
  sku: string;
  description: string | null;
  is_active?: boolean;
}

export interface XlsxPreviewOut {
  document_id: number;
  fingerprint: string;
  operations: { op_key: string; description: string; entity_type: string | null; params?: Record<string, unknown> }[];
  open_error_count: number;
  can_commit: boolean;
}

export interface XlsxCommitResultOut {
  attempt_id: number;
  document_id: number;
  status: string;
  operations: { op_key: string; status: string; entity_type: string | null; entity_id: string | null }[];
}

export async function createBatch(notes?: string | null): Promise<{ id: number }> {
  return fetchJson<{ id: number }>("/api/ingestion/batches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes: notes ?? null }),
  });
}

export async function getBatch(batchId: number): Promise<BatchOut> {
  return fetchJson<BatchOut>(`/api/ingestion/batches/${batchId}`);
}

export async function uploadBatchFiles(
  batchId: number,
  files: File[],
  clientUploadKeys?: string[],
): Promise<UploadResponse> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (clientUploadKeys?.length) {
    for (const k of clientUploadKeys) form.append("client_upload_keys", k);
  }
  return fetchJson<UploadResponse>(`/api/ingestion/batches/${batchId}/files`, {
    method: "POST",
    body: form,
  });
}

export async function abandonOccurrence(occurrenceId: number): Promise<OccurrenceOut> {
  return fetchJson<OccurrenceOut>(`/api/ingestion/occurrences/${occurrenceId}/abandon`, {
    method: "POST",
  });
}

export async function classifyOccurrence(occurrenceId: number): Promise<ClassifyOut> {
  return fetchJson<ClassifyOut>(`/api/ingestion/occurrences/${occurrenceId}/classify`, {
    method: "POST",
  });
}

export async function fetchAdapters(): Promise<AdapterInfo[]> {
  return fetchJson<AdapterInfo[]>("/api/ingestion/adapters");
}

export async function runAdapter(
  occurrenceId: number,
  body?: { adapter_id?: string; doc_type?: string },
): Promise<DocumentDetail> {
  return fetchJson<DocumentDetail>(`/api/ingestion/occurrences/${occurrenceId}/run-adapter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export async function patchIngestionRow(
  rowId: number,
  body: { cells_json?: string; cells?: Record<string, unknown>; expected_version: number; reason?: string },
): Promise<RowOut> {
  return fetchJson<RowOut>(`/api/ingestion/rows/${rowId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function addDocumentRow(
  documentId: number,
  body: {
    cells_json?: string;
    cells?: Record<string, unknown>;
    section_id?: number;
    expected_version: number;
    row_index?: number;
    row_key?: string;
  },
): Promise<RowOut> {
  return fetchJson<RowOut>(`/api/ingestion/documents/${documentId}/rows`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteIngestionRow(
  rowId: number,
  expectedVersion: number,
): Promise<void> {
  await fetchJson<void>(
    `/api/ingestion/rows/${rowId}?expected_version=${expectedVersion}`,
    { method: "DELETE" },
  );
}

export async function patchIngestionSection(
  sectionId: number,
  body: { review_status: string; expected_version: number; reason?: string },
): Promise<SectionOut> {
  return fetchJson<SectionOut>(`/api/ingestion/sections/${sectionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function patchDocumentReviewStatus(
  documentId: number,
  body: { review_status: string; expected_version: number },
): Promise<DocumentDetail> {
  return fetchJson<DocumentDetail>(`/api/ingestion/documents/${documentId}/review-status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteIngestionDocument(documentId: number): Promise<void> {
  await fetchJson<void>(`/api/ingestion/documents/${documentId}`, { method: "DELETE" });
}

export async function patchIngestionIssue(
  issueId: number,
  body: { status: string; justification?: string | null },
): Promise<IssueOut> {
  return fetchJson<IssueOut>(`/api/ingestion/issues/${issueId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function lockIngestionDocument(documentId: number): Promise<DocumentDetail> {
  return fetchJson<DocumentDetail>(`/api/ingestion/documents/${documentId}/lock`, {
    method: "POST",
  });
}

export async function unlockIngestionDocument(documentId: number): Promise<DocumentDetail> {
  return fetchJson<DocumentDetail>(`/api/ingestion/documents/${documentId}/unlock`, {
    method: "POST",
  });
}

export async function createDocumentSet(body: {
  batch_id?: number | null;
  projection_key?: string | null;
  label?: string | null;
}): Promise<DocumentSetOut> {
  return fetchJson<DocumentSetOut>("/api/ingestion/document-sets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function addDocumentSetMember(
  setId: number,
  body: { document_id: number; role?: string | null },
): Promise<{ id: number; document_set_id: number; document_id: number; role: string | null }> {
  return fetchJson(`/api/ingestion/document-sets/${setId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getDocumentSet(setId: number): Promise<DocumentSetOut> {
  return fetchJson<DocumentSetOut>(`/api/ingestion/document-sets/${setId}`);
}

export async function reconcileDocumentSet(setId: number): Promise<ReconciliationIssueOut[]> {
  return fetchJson<ReconciliationIssueOut[]>(`/api/ingestion/document-sets/${setId}/reconcile`, {
    method: "POST",
  });
}

export async function previewDossier(setId: number): Promise<DossierPreviewOut> {
  return fetchJson<DossierPreviewOut>(`/api/ingestion/document-sets/${setId}/preview-dossier`);
}

export interface PackingLineChoiceIn {
  group_key: string;
  order_item_id: number;
}

export interface PackingOrderCandidateOut {
  order_id: number;
  order_code: string;
  status: string;
  supplier_id: number;
  currency: string;
  evidence: string[];
  currency_match: boolean;
}

export interface PackingShipmentTargetOut {
  shipment_id: number;
  code: string;
  status: string;
  compatible: boolean;
  evidence: string[];
}

export interface PackingLineCandidateOut {
  order_item_id: number;
  position: number;
  sku: string;
  description: string;
  remaining: string;
  line_kind: string;
}

export interface PackingLineMatchOut {
  group_key: string;
  ncm: string;
  description: string;
  carton_count: number;
  total_qty: string;
  packaging: boolean;
  order_item_id?: number | null;
  remaining_before?: string | null;
  candidate_count: number;
  candidates: PackingLineCandidateOut[];
  status: string;
  carton_row_indexes: number[];
}

export interface PackingCartonOut {
  row_index: number;
  pallet_no?: string | null;
  carton_no?: string | null;
  items_per_ctn?: string | null;
  ncm: string;
  description: string;
  dimensions?: string | null;
  unit_net_weight_kg?: string | null;
  unit_gross_weight_kg?: string | null;
  total_net_weight_kg?: string | null;
  total_gross_weight_kg?: string | null;
  packaging: boolean;
}

export interface PackingPreviewOperationOut {
  op_key: string;
  description: string;
  entity_type?: string | null;
  params?: Record<string, unknown>;
}

export interface PackingPreviewOut {
  document_id: number;
  fingerprint: string;
  operations: PackingPreviewOperationOut[];
  open_error_count: number;
  can_commit: boolean;
  order_candidates: PackingOrderCandidateOut[];
  order_candidates_reason?: string | null;
  shipment_targets: PackingShipmentTargetOut[];
  shipment_targets_reason?: string | null;
  line_matches: PackingLineMatchOut[];
  cartons: PackingCartonOut[];
  blockers: string[];
  resolved_order_id?: number | null;
  resolved_shipment_id?: number | null;
  will_create_shipment: boolean;
  already_committed?: boolean;
  last_succeeded_attempt_id?: number | null;
  last_succeeded_shipment_id?: number | null;
}

export interface PackingCommitIn {
  operation_key: string;
  order_id?: number | null;
  shipment_id?: number | null;
  line_choices?: PackingLineChoiceIn[];
}

export async function fetchPackingPreview(
  documentId: number,
  orderId?: number | null,
  shipmentId?: number | null,
  lineChoices?: PackingLineChoiceIn[] | null,
): Promise<PackingPreviewOut> {
  const params = new URLSearchParams();
  if (orderId != null) params.set("order_id", String(orderId));
  if (shipmentId != null) params.set("shipment_id", String(shipmentId));
  if (lineChoices && lineChoices.length > 0) {
    params.set("line_choices", JSON.stringify(lineChoices));
  }
  const qs = params.toString();
  return fetchJson<PackingPreviewOut>(
    `/api/ingestion/documents/${documentId}/preview-commit-pl-detail${qs ? `?${qs}` : ""}`,
  );
}

export async function commitPlDetail(
  documentId: number,
  body: PackingCommitIn | string,
): Promise<CommitAttemptOut> {
  const payload: PackingCommitIn =
    typeof body === "string" ? { operation_key: body } : body;
  return fetchJson<CommitAttemptOut>(`/api/ingestion/documents/${documentId}/commit-pl-detail`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export interface DoganaleCommitIn {
  operation_key: string;
  process_id?: number | null;
  invoice_id?: number | null;
  shipment_id?: number | null;
}

export interface DoganaleProcessTargetOut {
  process_id: number;
  code: string;
  status: string;
  compatible: boolean;
  evidence: string[];
}

export interface DoganaleInvoiceCandidateOut {
  invoice_id: number;
  invoice_number: string;
  status: string;
  order_id: number | null;
  linked_process_id: number | null;
  evidence: string[];
}

export interface DoganaleShipmentTargetOut {
  shipment_id: number;
  code: string;
  status: string;
  compatible: boolean;
  linked_process_id: number | null;
  evidence: string[];
}

export interface DoganaleLinePreviewOut {
  position: number;
  ncm: string | null;
  description: string | null;
  quantity: string | null;
  unit: string | null;
  currency: string | null;
  unit_price: string | null;
  line_amount: string | null;
}

export interface DoganalePreviewOut {
  document_id: number;
  fingerprint: string;
  operations: { op_key: string; description: string; entity_type: string | null; params: Record<string, unknown> }[];
  open_error_count: number;
  can_commit: boolean;
  process_targets: DoganaleProcessTargetOut[];
  process_targets_reason: string | null;
  invoice_candidates: DoganaleInvoiceCandidateOut[];
  invoice_candidates_reason: string | null;
  shipment_targets: DoganaleShipmentTargetOut[];
  shipment_targets_reason: string | null;
  lines: DoganaleLinePreviewOut[];
  blockers: string[];
  resolved_process_id: number | null;
  resolved_invoice_id: number | null;
  resolved_shipment_id: number | null;
  will_create_process: boolean;
  reuse_reason: string | null;
  already_committed: boolean;
  last_succeeded_attempt_id: number | null;
  last_succeeded_process_id: number | null;
  document_number: string | null;
}

export async function fetchDoganalePreview(
  documentId: number,
  opts?: { process_id?: number | null; invoice_id?: number | null; shipment_id?: number | null },
): Promise<DoganalePreviewOut> {
  const params = new URLSearchParams();
  if (opts?.process_id != null) params.set("process_id", String(opts.process_id));
  if (opts?.invoice_id != null) params.set("invoice_id", String(opts.invoice_id));
  if (opts?.shipment_id != null) params.set("shipment_id", String(opts.shipment_id));
  const qs = params.toString();
  return fetchJson<DoganalePreviewOut>(
    `/api/ingestion/documents/${documentId}/preview-commit-doganale${qs ? `?${qs}` : ""}`,
  );
}

export async function commitDoganale(
  documentId: number,
  body: DoganaleCommitIn | string,
): Promise<CommitAttemptOut> {
  const payload: DoganaleCommitIn =
    typeof body === "string" ? { operation_key: body } : body;
  return fetchJson<CommitAttemptOut>(`/api/ingestion/documents/${documentId}/commit-doganale`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export interface PrintPreviewOut {
  document_id: number;
  fingerprint: string;
  operations: { op_key: string; description: string; entity_type: string | null; params: Record<string, unknown> }[];
  open_error_count: number;
  can_commit: boolean;
  invoice_ref: string | null;
  process_targets: DoganaleProcessTargetOut[];
  process_targets_reason: string | null;
  blockers: string[];
  already_committed: boolean;
  last_succeeded_attempt_id: number | null;
  last_succeeded_process_id: number | null;
  resolved_process_id: number | null;
}

export async function fetchPrintPreview(
  documentId: number,
  processId?: number | null,
): Promise<PrintPreviewOut> {
  const params = new URLSearchParams();
  if (processId != null) params.set("process_id", String(processId));
  const qs = params.toString();
  return fetchJson<PrintPreviewOut>(
    `/api/ingestion/documents/${documentId}/preview-commit-print${qs ? `?${qs}` : ""}`,
  );
}

export async function commitPrint(
  documentId: number,
  body: { operation_key: string; process_id?: number | null },
): Promise<CommitAttemptOut> {
  return fetchJson<CommitAttemptOut>(`/api/ingestion/documents/${documentId}/commit-print`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function searchSuppliers(q: string): Promise<CatalogSupplier[]> {
  const params = new URLSearchParams({ q, limit: "20" });
  return fetchJson<CatalogSupplier[]>(`/api/suppliers?${params.toString()}`);
}

export async function searchProducts(q: string): Promise<CatalogProduct[]> {
  const params = new URLSearchParams({ q, limit: "20" });
  return fetchJson<CatalogProduct[]>(`/api/products?${params.toString()}`);
}

export async function listBatchDocuments(batchId: number): Promise<DocumentSummary[]> {
  return fetchJson<DocumentSummary[]>(`/api/ingestion/batches/${batchId}/documents`);
}

export async function fetchXlsxPreview(documentId: number): Promise<XlsxPreviewOut> {
  return fetchJson<XlsxPreviewOut>(`/api/ingestion/documents/${documentId}/preview-commit-xlsx`);
}

export async function commitXlsxDocument(
  documentId: number,
  operationKey: string,
): Promise<XlsxCommitResultOut> {
  return fetchJson<XlsxCommitResultOut>(`/api/ingestion/documents/${documentId}/commit-xlsx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operation_key: operationKey }),
  });
}

export async function runAdapterXlsx(
  occurrenceId: number,
): Promise<{ document_id: number; doc_type: string; formula_cell_count?: number }> {
  return fetchJson(`/api/ingestion/occurrences/${occurrenceId}/run-adapter-xlsx`, {
    method: "POST",
  });
}

export async function listDocumentCommitAttempts(documentId: number): Promise<CommitAttemptOut[]> {
  return fetchJson<CommitAttemptOut[]>(`/api/ingestion/documents/${documentId}/commit-attempts`);
}
