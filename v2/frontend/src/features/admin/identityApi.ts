import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type UserAdmin = components["schemas"]["UserAdminOut"];
export type RoleOut = components["schemas"]["RoleOut"];
export type UserList = components["schemas"]["UserListOut"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

export async function listRoles() {
  const { data, error } = await api.GET("/api/roles");
  if (error) throw new Error(errMsg(error, "Erro ao listar papéis"));
  return data ?? [];
}

export async function listUsers(query?: { q?: string; limit?: number; offset?: number }): Promise<UserList> {
  const { data, error } = await api.GET("/api/users", {
    params: {
      query: {
        q: query?.q || undefined,
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
