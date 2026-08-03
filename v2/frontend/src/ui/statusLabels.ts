/** Mapeamento domínio → label PT + semântica DS (por entidade/contexto). */

export type StatusEntity =
  | "order"
  | "invoice"
  | "payment"
  | "payable"
  | "fx"
  | "shipment"
  | "customs"
  | "generic";

export type StatusSemantics = "neutral" | "information" | "success" | "warning" | "danger";

type StatusMeta = { label: string; semantics: StatusSemantics };

const ORDER: Record<string, StatusMeta> = {
  DRAFT: { label: "Rascunho", semantics: "neutral" },
  CONFIRMED: { label: "Confirmado", semantics: "success" },
  CANCELLED: { label: "Cancelado", semantics: "danger" },
};

const INVOICE: Record<string, StatusMeta> = {
  DRAFT: { label: "Rascunho", semantics: "neutral" },
  ISSUED: { label: "Emitida", semantics: "success" },
  CANCELLED: { label: "Cancelada", semantics: "danger" },
};

const PAYMENT: Record<string, StatusMeta> = {
  REGISTERED: { label: "Registrado", semantics: "information" },
  CANCELLED: { label: "Cancelado", semantics: "danger" },
};

const PAYABLE: Record<string, StatusMeta> = {
  OPEN: { label: "Aberto", semantics: "information" },
  PARTIALLY_PAID: { label: "Parcialmente pago", semantics: "warning" },
  PAID: { label: "Pago", semantics: "success" },
  CANCELLED: { label: "Cancelado", semantics: "danger" },
  OVERDUE: { label: "Vencido", semantics: "danger" },
};

const FX: Record<string, StatusMeta> = {
  // INITIAL permanece técnico (autoridade MCK/UI/UX)
  INITIAL: { label: "INITIAL", semantics: "neutral" },
  STALE: { label: "Desatualizado", semantics: "warning" },
};

const SHIPMENT: Record<string, StatusMeta> = {
  PLANNED: { label: "Planejado", semantics: "neutral" },
  BOOKED: { label: "Reservado", semantics: "information" },
  IN_TRANSIT: { label: "Em trânsito", semantics: "warning" },
  ARRIVED: { label: "Chegou", semantics: "success" },
  CANCELLED: { label: "Anulado", semantics: "danger" },
};

const CUSTOMS: Record<string, StatusMeta> = {
  DRAFT: { label: "Rascunho", semantics: "neutral" },
  SUBMITTED: { label: "Submetido", semantics: "information" },
  IN_CLEARANCE: { label: "Em liberação", semantics: "warning" },
  PARTIALLY_CLEARED: { label: "Parcialmente liberado", semantics: "warning" },
  CLEARED: { label: "Liberado", semantics: "success" },
  CANCELLED: { label: "Cancelado", semantics: "danger" },
};

const GENERIC: Record<string, StatusMeta> = {
  ...ORDER,
  ...INVOICE,
  ...PAYMENT,
  ...PAYABLE,
  DRAFT: { label: "Rascunho", semantics: "neutral" },
  TODAY: { label: "Hoje", semantics: "warning" },
};

const BY_ENTITY: Record<StatusEntity, Record<string, StatusMeta>> = {
  order: ORDER,
  invoice: INVOICE,
  payment: PAYMENT,
  payable: PAYABLE,
  fx: FX,
  shipment: SHIPMENT,
  customs: CUSTOMS,
  generic: GENERIC,
};

export function resolveStatus(
  status: string,
  entity: StatusEntity = "generic",
): StatusMeta {
  const code = status.trim();
  const map = BY_ENTITY[entity] ?? GENERIC;
  if (map[code]) return map[code];
  if (GENERIC[code]) return GENERIC[code];
  // Heurística mínima para códigos ainda não mapeados — não inventar label PT
  if (code.includes("CANCEL")) return { label: code, semantics: "danger" };
  if (code.includes("PARTIAL") || code === "DRAFT" || code === "STALE") {
    return { label: code, semantics: "warning" };
  }
  if (code.includes("PAID") || code === "CONFIRMED" || code === "ISSUED") {
    return { label: code, semantics: "success" };
  }
  if (code === "OPEN" || code === "REGISTERED") {
    return { label: code, semantics: "information" };
  }
  return { label: code, semantics: "neutral" };
}

export function statusLabel(status: string, entity: StatusEntity = "generic"): string {
  return resolveStatus(status, entity).label;
}

export function statusSemantics(
  status: string,
  entity: StatusEntity = "generic",
): StatusSemantics {
  return resolveStatus(status, entity).semantics;
}
