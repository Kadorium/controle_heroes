import type { User } from "../auth/types";

export function canReadCustoms(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("customs:read");
}

export function canWriteCustoms(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("customs:write");
}

export function canClearCustoms(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("customs:clear");
}

/** Status de ImportProcess — labels persistentes pt-BR. */
export function statusLabel(status: string) {
  switch (status) {
    case "DRAFT":
      return "Rascunho";
    case "SUBMITTED":
      return "Submetido";
    case "IN_CLEARANCE":
      return "Em liberação";
    case "PARTIALLY_CLEARED":
      return "Parcialmente liberado";
    case "CLEARED":
      return "Liberado";
    case "CANCELLED":
      return "Cancelado";
    default:
      return status;
  }
}

/** Mensagem de conflito 409 / reason code visível ao operador. */
export function conflictMessage(err: Error & { status?: number; code?: string }) {
  const base = err.message?.trim() || "Conflito de estado";
  if (err.status === 409) {
    const code = err.code?.trim();
    return code ? `Conflito (409 · ${code}): ${base}` : `Conflito (409): ${base}`;
  }
  return base;
}
