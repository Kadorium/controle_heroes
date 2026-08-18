import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type LogisticsProvider = components["schemas"]["ProviderOut"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

function throwApi(error: unknown, response: Response | undefined, fallback: string): never {
  const err = new Error(errMsg(error, fallback)) as Error & { status?: number };
  err.status = response?.status;
  throw err;
}

export async function listLogisticsProviders(query?: {
  q?: string;
  active_only?: boolean;
  shipment_eligible_only?: boolean;
  limit?: number;
  offset?: number;
}) {
  const { data, error, response } = await api.GET("/api/logistics-providers", {
    params: {
      query: {
        limit: 100,
        offset: 0,
        ...query,
      },
    },
  });
  if (error) throwApi(error, response, "Erro ao listar prestadores");
  return data ?? [];
}

export async function createLogisticsProvider(body: components["schemas"]["ProviderCreate"]) {
  const { data, error, response } = await api.POST("/api/logistics-providers", { body });
  if (error) throwApi(error, response, "Erro ao criar prestador");
  return data!;
}

export async function updateLogisticsProvider(
  providerId: number,
  body: components["schemas"]["ProviderUpdate"],
) {
  const { data, error, response } = await api.PATCH("/api/logistics-providers/{provider_id}", {
    params: { path: { provider_id: providerId } },
    body,
  });
  if (error) throwApi(error, response, "Erro ao atualizar prestador");
  return data!;
}
