import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Shipment = components["schemas"]["ShipmentOut"];
export type ShipmentListItem = components["schemas"]["ShipmentListItem"];
export type ShipmentCandidate = components["schemas"]["CandidateOut"];
export type AuditEvent = components["schemas"]["AuditEventResponse"];

export type DerivedTotals = {
  net_weight_kg: string | number;
  gross_weight_kg: string | number;
  volume_m3: string | number;
  pallet_count: number;
  carton_count: number;
  box_count: number;
  package_row_count: number;
};

export type DivergenceDiff = {
  field: string;
  declared: string | number;
  derived: string | number;
  is_significant: boolean;
};

export type DivergenceRow = {
  document_id: number;
  summary_id: number;
  diffs: DivergenceDiff[];
  is_significant: boolean;
};

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

function throwApi(error: unknown, response: Response | undefined, fallback: string): never {
  const err = new Error(errMsg(error, fallback)) as Error & { status?: number };
  err.status = response?.status;
  throw err;
}

export async function listShipments(query?: {
  status?: string | null;
  modal?: string | null;
  logistics_provider_id?: number | null;
  include_cancelled?: boolean;
  limit?: number;
  offset?: number;
}) {
  const { data, error } = await api.GET("/api/shipments", {
    params: {
      query: {
        limit: 50,
        offset: 0,
        ...query,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar embarques"));
  return data ?? [];
}

export async function getShipment(shipmentId: number) {
  const { data, error } = await api.GET("/api/shipments/{shipment_id}", {
    params: { path: { shipment_id: shipmentId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar embarque"));
  return data!;
}

export async function createShipment(body: components["schemas"]["ShipmentCreate"]) {
  const { data, error, response } = await api.POST("/api/shipments", { body });
  if (error) throwApi(error, response, "Erro ao criar embarque");
  return data!;
}

export async function updateShipment(
  shipmentId: number,
  body: components["schemas"]["ShipmentUpdate"],
) {
  const { data, error, response } = await api.PATCH("/api/shipments/{shipment_id}", {
    params: { path: { shipment_id: shipmentId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar embarque");
  return data!;
}

export async function advanceShipment(
  shipmentId: number,
  body: components["schemas"]["AdvanceBody"],
) {
  const { data, error, response } = await api.POST("/api/shipments/{shipment_id}/advance", {
    params: { path: { shipment_id: shipmentId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao avançar status");
  return data!;
}

export async function annulShipment(shipmentId: number, expected_version: number) {
  const { data, error, response } = await api.POST("/api/shipments/{shipment_id}/annul", {
    params: { path: { shipment_id: shipmentId } },
    body: { expected_version },
  });
  if (error) throwApi(error, response, "Erro ao anular embarque");
  return data!;
}

export async function deleteShipment(shipmentId: number, expected_version: number) {
  const { error, response } = await api.DELETE("/api/shipments/{shipment_id}", {
    params: {
      path: { shipment_id: shipmentId },
      query: { expected_version },
    },
  });
  if (error) throwApi(error, response, "Erro ao excluir embarque");
}

export async function addItem(
  shipmentId: number,
  body: components["schemas"]["app__logistics__routes__ItemCreate"],
) {
  const { data, error, response } = await api.POST("/api/shipments/{shipment_id}/items", {
    params: { path: { shipment_id: shipmentId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao adicionar item");
  return data!;
}

export async function updateItem(
  shipmentId: number,
  itemId: number,
  body: components["schemas"]["app__logistics__routes__ItemUpdate"],
) {
  const { data, error, response } = await api.PATCH(
    "/api/shipments/{shipment_id}/items/{item_id}",
    {
      params: { path: { shipment_id: shipmentId, item_id: itemId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao atualizar item");
  return data!;
}

export async function removeItem(shipmentId: number, itemId: number, expected_version: number) {
  const { data, error, response } = await api.DELETE(
    "/api/shipments/{shipment_id}/items/{item_id}",
    {
      params: {
        path: { shipment_id: shipmentId, item_id: itemId },
        query: { expected_version },
      },
    },
  );
  if (error) throwApi(error, response, "Erro ao remover item");
  return data!;
}

export async function addPackage(shipmentId: number, body: components["schemas"]["PackageCreate"]) {
  const { data, error, response } = await api.POST("/api/shipments/{shipment_id}/packages", {
    params: { path: { shipment_id: shipmentId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao adicionar volume");
  return data!;
}

export async function updatePackage(
  shipmentId: number,
  packageId: number,
  body: components["schemas"]["PackageUpdate"],
) {
  const { data, error, response } = await api.PATCH(
    "/api/shipments/{shipment_id}/packages/{package_id}",
    {
      params: { path: { shipment_id: shipmentId, package_id: packageId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao atualizar volume");
  return data!;
}

export async function removePackage(
  shipmentId: number,
  packageId: number,
  expected_version: number,
) {
  const { data, error, response } = await api.DELETE(
    "/api/shipments/{shipment_id}/packages/{package_id}",
    {
      params: {
        path: { shipment_id: shipmentId, package_id: packageId },
        query: { expected_version },
      },
    },
  );
  if (error) throwApi(error, response, "Erro ao remover volume");
  return data!;
}

export async function setPackageContents(
  shipmentId: number,
  packageId: number,
  body: components["schemas"]["ContentsReplace"],
) {
  const { data, error, response } = await api.PUT(
    "/api/shipments/{shipment_id}/packages/{package_id}/contents",
    {
      params: { path: { shipment_id: shipmentId, package_id: packageId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao salvar conteúdo do volume");
  return data!;
}

export async function addPackagesBatch(
  shipmentId: number,
  body: components["schemas"]["PackagesBatchCreate"],
) {
  const { data, error, response } = await api.POST("/api/shipments/{shipment_id}/packages/batch", {
    params: { path: { shipment_id: shipmentId } },
    body,
  });
  if (error) throwApi(error, response, "Erro no batch de volumes");
  return data!;
}

export async function updatePackagesBatch(
  shipmentId: number,
  body: components["schemas"]["PackagesBatchUpdate"],
) {
  const { data, error, response } = await api.PATCH(
    "/api/shipments/{shipment_id}/packages/batch",
    {
      params: { path: { shipment_id: shipmentId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro na edição em lote");
  return data!;
}

export async function listShipmentDocuments(shipmentId: number) {
  const res = await fetch(
    `/api/documents?entity_type=shipment&entity_id=${encodeURIComponent(String(shipmentId))}`,
    { credentials: "include" },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "Erro ao listar documentos do embarque");
  }
  return (await res.json()) as Array<{
    id: number;
    original_filename: string;
    mime_type?: string | null;
    role?: string | null;
  }>;
}

export async function uploadShipmentDocument(shipmentId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", "shipment");
  form.append("entity_id", String(shipmentId));
  form.append("role", "official");
  const res = await fetch("/api/documents", { method: "POST", body: form, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "Erro ao anexar documento do embarque");
  }
  return res.json();
}

export async function addReference(
  shipmentId: number,
  body: components["schemas"]["ReferenceCreate"],
) {
  const { data, error, response } = await api.POST("/api/shipments/{shipment_id}/references", {
    params: { path: { shipment_id: shipmentId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao adicionar referência");
  return data!;
}

export async function removeReference(
  shipmentId: number,
  referenceId: number,
  expected_version: number,
) {
  const { data, error, response } = await api.DELETE(
    "/api/shipments/{shipment_id}/references/{reference_id}",
    {
      params: {
        path: { shipment_id: shipmentId, reference_id: referenceId },
        query: { expected_version },
      },
    },
  );
  if (error) throwApi(error, response, "Erro ao remover referência");
  return data!;
}

export async function upsertDocumentSummary(
  shipmentId: number,
  body: components["schemas"]["SummaryUpsert"],
) {
  const { data, error, response } = await api.PUT(
    "/api/shipments/{shipment_id}/document-summaries",
    {
      params: { path: { shipment_id: shipmentId } },
      body,
    },
  );
  if (error) throwApi(error, response, "Erro ao salvar resumo documental");
  return data!;
}

export async function orderItemCandidates(query: {
  order_code?: string | null;
  order_id?: number | null;
  external_ref?: string | null;
  sku?: string | null;
  supplier_id?: number | null;
  limit?: number;
}) {
  const { data, error, response } = await api.GET("/api/shipments/order-item-candidates", {
    params: { query: { limit: 50, ...query } },
  });
  if (error) throwApi(error, response, "Erro ao buscar candidatos");
  return data ?? [];
}

export async function getDerivedTotals(shipmentId: number) {
  const { data, error } = await api.GET("/api/shipments/{shipment_id}/totals/derived", {
    params: { path: { shipment_id: shipmentId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar totais derivados"));
  return data as DerivedTotals;
}

export async function getDivergences(shipmentId: number) {
  const { data, error } = await api.GET("/api/shipments/{shipment_id}/totals/divergences", {
    params: { path: { shipment_id: shipmentId } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar divergências"));
  return (data ?? []) as DivergenceRow[];
}

export async function listShipmentAudit(shipmentId: number) {
  const { data, error } = await api.GET("/api/audit", {
    params: {
      query: {
        entity_type: "shipment",
        entity_id: String(shipmentId),
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar auditoria"));
  return data ?? [];
}
