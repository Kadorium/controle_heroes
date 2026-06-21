/** Glossário operacional PT — enums internos permanecem em inglês; só labels visíveis mudam. */

const EMPTY = "—";

export function emptyDash(value: unknown): string {
  if (value === null || value === undefined || value === "") return EMPTY;
  if (typeof value === "string" && value.trim() === "") return EMPTY;
  return String(value);
}

function lookup(map: Record<string, string>, code: string | null | undefined): string {
  if (!code) return EMPTY;
  const key = code.toUpperCase().trim();
  return map[key] ?? code;
}

export const STATUS_LABELS: Record<string, string> = {
  PO_CREATED: "Pedido criado",
  SI_OPEN: "Solicitação aberta",
  PROFORMA_RECEIVED: "Proforma recebida",
  ADVANCE_PAID: "Acconto pago",
  PARTIAL_PAID: "Parcialmente pago",
  FULL_PAID: "Pago",
  BOOKED: "Embarque reservado",
  SHIPPED: "Despachado",
  IN_TRANSIT: "Em trânsito",
  ARRIVED: "Chegou ao Brasil",
  UNLOADED: "Descarregado",
  DI_SUBMITTED: "DI registrada",
  DUIMP_REGISTERED: "DUIMP registrada",
  CUSTOMS_RELEASED: "Liberado pela aduana",
  CLEARED: "Desembaraçado",
  DELIVERED: "Entregue",
  RECEIVED_IN_STOCK: "Recebido em estoque",
  CONCILIATION_PENDING: "Conciliação pendente",
  CONCILIATION_DONE: "Conciliação concluída",
  CLOSED: "Fechada",
  REOPENED: "Reaberta",
  CANCELLED: "Cancelada",
  ON_HOLD: "Em espera",
  DRAFT: "Rascunho",
  RASCUNHO: "Rascunho",
};

export const PAY_STATUS_LABELS: Record<string, string> = {
  PENDING: "Aberto",
  PLANNED: "Planejado",
  SETTLED: "Liquidado",
  PAID: "Pago",
  FULL_PAID: "Pago",
  OVERDUE: "Vencido",
  OPEN: "Aberto",
  ADVANCE: "Antecipado",
  PARTIAL: "Parcial",
  FINAL: "Final",
  ADJUSTMENT: "Ajuste",
};

export const INVOICE_TYPE_LABELS: Record<string, string> = {
  ANTECIPO: "Acconto / Antecipo",
  PROFORMA: "Proforma",
  SALDO: "Saldo",
  COMPLEMENTAR: "Complementar",
  AJUSTE: "Ajuste",
  CREDITO: "Crédito",
  OUTRA: "Outra",
};

export const SHIPMENT_STATUS_LABELS: Record<string, string> = {
  PLANNED: "Planejado",
  BOOKED: "Reservado",
  SHIPPED: "Despachado",
  IN_TRANSIT: "Em trânsito",
  ARRIVED: "Chegou",
  DELIVERED: "Entregue",
  CANCELLED: "Cancelado",
};

export const MODAL_LABELS: Record<string, string> = {
  AIR: "Aéreo",
  OCEAN: "Marítimo",
  OTHER: "Outro",
};

export const RECONCILIATION_STATUS_LABELS: Record<string, string> = {
  OK: "OK",
  WARNING: "Atenção",
  DIVERGENT: "Divergente",
  APPROVED: "Aprovado",
  PENDING: "Pendente",
};

export const FIELD_LABELS: Record<string, string> = {
  Invoices: "Faturas",
  Invoice: "Fatura",
  Payment: "Pagamento",
  Payments: "Pagamentos",
  Shipment: "Embarque",
  Shipments: "Embarques",
  "Landed Cost": "Custo final (landed)",
  "Landed cost": "Custo final (landed)",
  reason_code: "Motivo",
  "Audit Log": "Auditoria",
  Timeline: "Histórico",
  SKU: "Produto/SKU",
  Importation: "Ordem",
  Importations: "Ordens",
  importation: "ordem",
  importations: "ordens",
};

export function statusLabel(code: string | null | undefined): string {
  return lookup(STATUS_LABELS, code);
}

export function payStatusLabel(code: string | null | undefined): string {
  return lookup(PAY_STATUS_LABELS, code);
}

export function invoiceTypeLabel(code: string | null | undefined): string {
  return lookup(INVOICE_TYPE_LABELS, code);
}

export function shipmentStatusLabel(code: string | null | undefined): string {
  return lookup(SHIPMENT_STATUS_LABELS, code);
}

export function modalLabel(code: string | null | undefined): string {
  return lookup(MODAL_LABELS, code);
}

export function reconciliationStatusLabel(code: string | null | undefined): string {
  return lookup(RECONCILIATION_STATUS_LABELS, code);
}

export function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

/** Lista para página de glossário */
export function glossarySections(): Array<{ title: string; entries: Array<{ code: string; label: string }> }> {
  const toEntries = (map: Record<string, string>) =>
    Object.entries(map).map(([code, label]) => ({ code, label }));
  return [
    { title: "Status da ordem", entries: toEntries(STATUS_LABELS) },
    { title: "Pagamentos", entries: toEntries(PAY_STATUS_LABELS) },
    { title: "Tipos de fatura", entries: toEntries(INVOICE_TYPE_LABELS) },
    { title: "Embarques", entries: toEntries(SHIPMENT_STATUS_LABELS) },
    { title: "Modal", entries: toEntries(MODAL_LABELS) },
    { title: "Termos de tela", entries: toEntries(FIELD_LABELS) },
  ];
}
