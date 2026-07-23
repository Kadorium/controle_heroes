import type { AdminUser, RoleOption } from "../../api";

export const ROLE_LABELS: Record<string, string> = {
  admin: "Administrador",
  gestor: "Gestor",
  financeiro: "Financeiro",
  operador: "Operador",
  comprador: "Comprador",
  logistica: "Logística",
};

export type UserVisibility = "active" | "cancelled" | "all";

export function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role;
}

export function isUserActive(user: AdminUser): boolean {
  return user.is_active !== false;
}

export function canCancelUser(user: AdminUser, currentUserId: number | undefined): boolean {
  return isUserActive(user) && user.id !== currentUserId;
}

export function statusLabel(user: AdminUser): string {
  return isUserActive(user) ? "Ativo" : "Anulado";
}

export function fallbackRoleOptions(currentRole?: string): RoleOption[] {
  const options = Object.keys(ROLE_LABELS).map((name) => ({ name, description: null }));
  if (currentRole && !options.some((r) => r.name === currentRole)) {
    return [{ name: currentRole, description: null }, ...options];
  }
  return options;
}

export function mergeRoleOptions(roles: RoleOption[], currentRole?: string): RoleOption[] {
  if (roles.length === 0) {
    return fallbackRoleOptions(currentRole);
  }
  if (currentRole && !roles.some((r) => r.name === currentRole)) {
    return [{ name: currentRole, description: null }, ...roles];
  }
  return roles;
}
