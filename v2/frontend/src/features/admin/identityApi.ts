import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type UserAdmin = components["schemas"]["UserAdminOut"];
export type RoleOut = components["schemas"]["RoleOut"];
export type UserList = components["schemas"]["UserListOut"];

/** AppError `{ message }` or FastAPI `{ detail: [{ loc, msg }] }` → human message. */
export function formatIdentityError(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") return fallback;
  const rec = error as Record<string, unknown>;
  if (typeof rec.message === "string" && rec.message.trim()) return rec.message;
  if (typeof rec.detail === "string" && rec.detail.trim()) return rec.detail;
  if (!Array.isArray(rec.detail) || rec.detail.length === 0) return fallback;
  const first = rec.detail[0];
  if (!first || typeof first !== "object") return fallback;
  const item = first as { loc?: unknown; msg?: string };
  const loc = Array.isArray(item.loc) ? item.loc.map(String).join(".") : "";
  const msg = typeof item.msg === "string" ? item.msg : "";
  if (loc.includes("email") || /email/i.test(msg)) {
    return "E-mail inválido. Use o formato nome@dominio.";
  }
  return msg || fallback;
}

function errMsg(error: unknown, fallback: string) {
  return formatIdentityError(error, fallback);
}

export async function listRoles() {
  const { data, error } = await api.GET("/api/roles");
  if (error) throw new Error(errMsg(error, "Erro ao listar papéis"));
  return data ?? [];
}

export async function listUsers(query?: {
  q?: string;
  isActive?: boolean | null;
  role?: string;
  limit?: number;
  offset?: number;
}): Promise<UserList> {
  const { data, error } = await api.GET("/api/users", {
    params: {
      query: {
        q: query?.q || undefined,
        is_active: query?.isActive ?? undefined,
        role: query?.role || undefined,
        limit: query?.limit ?? 50,
        offset: query?.offset ?? 0,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar usuários"));
  return data ?? { items: [], total: 0, limit: 50, offset: 0 };
}

export async function getUser(id: number) {
  const { data, error } = await api.GET("/api/users/{user_id}", {
    params: { path: { user_id: id } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar usuário"));
  return data!;
}

export async function createUser(body: components["schemas"]["UserCreateIn"]) {
  const { data, error } = await api.POST("/api/users", { body });
  if (error) throw new Error(errMsg(error, "Erro ao criar usuário"));
  return data!;
}

export async function patchUser(id: number, body: components["schemas"]["UserPatchIn"]) {
  const { data, error } = await api.PATCH("/api/users/{user_id}", {
    params: { path: { user_id: id } },
    body,
  });
  if (error) throw new Error(errMsg(error, "Erro ao atualizar usuário"));
  return data!;
}

export async function setUserPassword(id: number, password: string) {
  const { data, error } = await api.POST("/api/users/{user_id}/password", {
    params: { path: { user_id: id } },
    body: { password },
  });
  if (error) throw new Error(errMsg(error, "Erro ao definir senha"));
  return data!;
}
