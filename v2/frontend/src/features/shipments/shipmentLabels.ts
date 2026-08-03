/** Shared shipment modal / provider labels (pt-BR). */

export const SHIPMENT_MODAL_OPTIONS = [
  { value: "SEA", label: "Marítimo" },
  { value: "AIR", label: "Aéreo" },
  { value: "ROAD", label: "Rodoviário" },
  { value: "COURIER", label: "Courier" },
  { value: "MULTIMODAL", label: "Multimodal" },
  { value: "OTHER", label: "Outro" },
] as const;

export const PROVIDER_TYPE_OPTIONS = [
  { value: "TRANSPORTADOR", label: "Transportador" },
  { value: "ARMADOR", label: "Armador" },
  { value: "FREIGHT_FORWARDER", label: "Agente de cargas" },
  { value: "OPERADOR_LOGISTICO", label: "Operador logístico" },
  { value: "DESPACHANTE", label: "Despachante aduaneiro" },
] as const;

export const SHIPMENT_PROVIDER_TYPE_VALUES = new Set([
  "TRANSPORTADOR",
  "ARMADOR",
  "FREIGHT_FORWARDER",
  "OPERADOR_LOGISTICO",
]);

export function modalLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return SHIPMENT_MODAL_OPTIONS.find((o) => o.value === code)?.label ?? code;
}

export function providerDisplayName(p: {
  trade_name?: string | null;
  legal_name: string;
}): string {
  const trade = p.trade_name?.trim();
  return trade || p.legal_name;
}

export function providerTypeLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return PROVIDER_TYPE_OPTIONS.find((o) => o.value === code)?.label ?? code;
}
