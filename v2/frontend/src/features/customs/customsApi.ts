import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type ImportProcess = components["schemas"]["ProcessOut"];
export type ImportProcessListItem = components["schemas"]["ProcessListItem"];
export type ResidualInvoiceItem = components["schemas"]["ResidualInvoiceItemOut"];
export type ResidualShipmentItem = components["schemas"]["ResidualShipmentItemOut"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

function throwApi(error: unknown, response: Response | undefined, fallback: string): never {
  const err = new Error(errMsg(error, fallback)) as Error & { status?: number; code?: string };
  err.status = response?.status;
  err.code = (error as { error?: string } | undefined)?.error;
  throw err;
}

export async function listImportProcesses(query?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const { data, error } = await api.GET("/api/import-processes", {
    params: { query: { limit: 50, offset: 0, ...query } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar processos"));
  return data ?? [];
}

export async function getImportProcess(processId: number) {
  const { data, error, response } = await api.GET("/api/import-processes/{process_id}", {
    params: { path: { process_id: processId } },
  });
  if (error) throwApi(error, response, "Erro ao carregar processo");
  return data!;
}

export async function createImportProcess(body: { external_reference?: string; notes?: string }) {
  const { data, error, response } = await api.POST("/api/import-processes", { body });
  if (error) throwApi(error, response, "Erro ao criar processo");
  return data!;
}

export async function updateImportProcess(
  processId: number,
  body: components["schemas"]["ProcessUpdate"],
) {
  const { data, error, response } = await api.PATCH("/api/import-processes/{process_id}", {
    params: { path: { process_id: processId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar processo");
  return data!;
}

export async function linkInvoice(
  processId: number,
  body: components["schemas"]["LinkInvoiceBody"],
) {
  const { data, error, response } = await api.POST("/api/import-processes/{process_id}/invoices", {
    params: { path: { process_id: processId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao vincular invoice");
  return data!;
}

export async function unlinkInvoice(
  processId: number,
  body: components["schemas"]["UnlinkInvoiceBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/invoices/unlink",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao desvincular invoice");
  return data!;
}

export async function allocateInvoiceItem(
  processId: number,
  body: components["schemas"]["AllocInvoiceItemBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/invoice-items/allocate",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao alocar item de invoice");
  return data!;
}

export async function linkShipment(
  processId: number,
  body: components["schemas"]["LinkShipmentBody"],
) {
  const { data, error, response } = await api.POST("/api/import-processes/{process_id}/shipments", {
    params: { path: { process_id: processId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao vincular shipment");
  return data!;
}

export async function unlinkShipment(
  processId: number,
  body: components["schemas"]["UnlinkShipmentBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/shipments/unlink",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao desvincular shipment");
  return data!;
}

export async function allocateShipmentItem(
  processId: number,
  body: components["schemas"]["AllocShipmentItemBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/shipment-items/allocate",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao alocar item de shipment");
  return data!;
}

export async function submitImportProcess(processId: number, expected_version: number) {
  const { data, error, response } = await api.POST("/api/import-processes/{process_id}/submit", {
    params: { path: { process_id: processId } },
    body: { expected_version },
  });
  if (error) throwApi(error, response, "Erro ao submeter processo");
  return data!;
}

export async function cancelImportProcess(
  processId: number,
  body: components["schemas"]["app__customs__routes__CancelBody"],
) {
  const { data, error, response } = await api.POST("/api/import-processes/{process_id}/cancel", {
    params: { path: { process_id: processId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao cancelar processo");
  return data!;
}

export async function listInvoiceResiduals(processId: number) {
  const { data, error } = await api.GET(
    "/api/import-processes/{process_id}/residuals/invoice-items",
    { params: { path: { process_id: processId } } },
  );
  if (error) throw new Error(errMsg(error, "Erro ao carregar residuals"));
  return data ?? [];
}

export async function listShipmentResiduals(processId: number) {
  const { data, error } = await api.GET(
    "/api/import-processes/{process_id}/residuals/shipment-items",
    { params: { path: { process_id: processId } } },
  );
  if (error) throw new Error(errMsg(error, "Erro ao carregar residuals"));
  return data ?? [];
}

export async function listProcessDocuments(processId: number) {
  const res = await fetch(
    `/api/documents?entity_type=import_process&entity_id=${encodeURIComponent(String(processId))}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error("Erro ao listar documentos");
  return (await res.json()) as Array<{
    id: number;
    original_filename: string;
    mime_type?: string | null;
  }>;
}

export async function uploadProcessDocument(processId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", "import_process");
  form.append("entity_id", String(processId));
  form.append("role", "attachment");
  const res = await fetch("/api/documents", { method: "POST", credentials: "include", body: form });
  if (!res.ok) throw new Error("Erro ao anexar documento");
  return res.json();
}

export async function listProcessAudit(processId: number) {
  const { data, error } = await api.GET("/api/audit", {
    params: {
      query: {
        entity_type: "import_process",
        entity_id: String(processId),
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar auditoria"));
  return data ?? [];
}

/* —— Doganale (I5-2) —— */

export type DoganaleSummary = components["schemas"]["DoganaleSummaryOut"];
export type DoganaleVersion = components["schemas"]["DoganaleVersionOut"];
export type Divergence = components["schemas"]["DivergenceOut"];

export async function getDoganale(processId: number) {
  const { data, error, response } = await api.GET("/api/import-processes/{process_id}/doganale", {
    params: { path: { process_id: processId } },
  });
  if (error) throwApi(error, response, "Erro ao carregar Doganale");
  return (data ?? null) as DoganaleSummary | null;
}

export async function createDoganaleVersion(
  processId: number,
  body: components["schemas"]["CreateVersionBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/doganale/versions",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao criar versão Doganale");
  return data!;
}

export async function replaceDoganaleLines(
  processId: number,
  versionId: number,
  body: components["schemas"]["ReplaceLinesBody"],
) {
  const { data, error, response } = await api.PUT(
    "/api/import-processes/{process_id}/doganale/versions/{version_id}/lines",
    {
      params: { path: { process_id: processId, version_id: versionId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao salvar linhas");
  return data!;
}

export async function activateDoganaleVersion(
  processId: number,
  versionId: number,
  body: components["schemas"]["VersionLockBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/doganale/versions/{version_id}/activate",
    {
      params: { path: { process_id: processId, version_id: versionId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao ativar Doganale");
  return data!;
}

export async function supersedeDoganaleVersion(
  processId: number,
  versionId: number,
  body: components["schemas"]["SupersedeBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/doganale/versions/{version_id}/supersede",
    {
      params: { path: { process_id: processId, version_id: versionId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao retificar Doganale");
  return data!;
}

export async function listDivergences(processId: number) {
  const { data, error, response } = await api.GET(
    "/api/import-processes/{process_id}/divergences",
    { params: { path: { process_id: processId } } },
  );
  if (error) throwApi(error, response, "Erro ao listar divergências");
  return data ?? [];
}

export async function registerDivergence(
  processId: number,
  body: components["schemas"]["DivergenceIn"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/divergences",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao registrar divergência");
  return data!;
}

/* —— Numerário / Funding (I5-3A) —— */

export type CustomsPayee = components["schemas"]["PayeeOut"];
export type FundingRequest = components["schemas"]["FundingOut"];

export async function listPayees(query?: { limit?: number; offset?: number }) {
  const { data, error, response } = await api.GET("/api/customs/payees", {
    params: { query: { limit: 100, ...query } },
  });
  if (error) throwApi(error, response, "Erro ao listar favorecidos");
  return data ?? [];
}

export async function createPayee(body: components["schemas"]["PayeeIn"]) {
  const { data, error, response } = await api.POST("/api/customs/payees", { body });
  if (error) throwApi(error, response, "Erro ao criar favorecido");
  return data!;
}

export async function updatePayee(
  payeeId: number,
  body: components["schemas"]["PayeeUpdate"],
) {
  const { data, error, response } = await api.PATCH("/api/customs/payees/{payee_id}", {
    params: { path: { payee_id: payeeId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar favorecido");
  return data!;
}

export async function listFundingRequests(processId: number) {
  const { data, error, response } = await api.GET(
    "/api/import-processes/{process_id}/funding-requests",
    { params: { path: { process_id: processId } } },
  );
  if (error) throwApi(error, response, "Erro ao listar Numerário");
  return data ?? [];
}

export async function createFundingRequest(
  processId: number,
  body: components["schemas"]["FundingCreate"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/funding-requests",
    { params: { path: { process_id: processId } }, body },
  );
  if (error) throwApi(error, response, "Erro ao criar Numerário");
  return data!;
}

export async function replaceValueBases(
  processId: number,
  fundingId: number,
  body: components["schemas"]["FundingReplaceLinesBody"],
) {
  const { data, error, response } = await api.PUT(
    "/api/import-processes/{process_id}/funding-requests/{funding_id}/value-bases",
    {
      params: { path: { process_id: processId, funding_id: fundingId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao salvar bases");
  return data!;
}

export async function replaceTaxLines(
  processId: number,
  fundingId: number,
  body: components["schemas"]["FundingReplaceLinesBody"],
) {
  const { data, error, response } = await api.PUT(
    "/api/import-processes/{process_id}/funding-requests/{funding_id}/tax-lines",
    {
      params: { path: { process_id: processId, funding_id: fundingId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao salvar tributos");
  return data!;
}

export async function replaceExpenseLines(
  processId: number,
  fundingId: number,
  body: components["schemas"]["FundingReplaceLinesBody"],
) {
  const { data, error, response } = await api.PUT(
    "/api/import-processes/{process_id}/funding-requests/{funding_id}/expense-lines",
    {
      params: { path: { process_id: processId, funding_id: fundingId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao salvar despesas");
  return data!;
}

export async function confirmFundingRequest(
  processId: number,
  fundingId: number,
  body: components["schemas"]["FundingVersionLockBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/funding-requests/{funding_id}/confirm",
    {
      params: { path: { process_id: processId, funding_id: fundingId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao confirmar Numerário");
  return data!;
}

export async function cancelFundingRequest(
  processId: number,
  fundingId: number,
  body: components["schemas"]["FundingVersionLockBody"],
) {
  const { data, error, response } = await api.POST(
    "/api/import-processes/{process_id}/funding-requests/{funding_id}/cancel",
    {
      params: { path: { process_id: processId, funding_id: fundingId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao cancelar Numerário");
  return data!;
}
