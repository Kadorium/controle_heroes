/** Labels de produto para Inventory / Numerário — sem nomes de schema internos. */

export function skuBucketLabel(key: string): string {
  switch (key) {
    case "available_qty":
      return "Disponível";
    case "bonded_qty":
      return "Entreposto";
    case "quarantine_qty":
      return "Quarentena";
    case "cleared_not_received_qty":
      return "Liberado não recebido";
    case "in_clearance_qty":
      return "Em liberação";
    case "in_transit_qty":
      return "Em trânsito";
    case "future_order_qty":
      return "Pedido futuro";
    default:
      return key;
  }
}

export function movementTypeLabel(type: string | null | undefined): string {
  switch (type) {
    case "BONDED_IN":
      return "Entrada entreposto";
    case "DOMESTIC_IN":
      return "Entrada doméstica";
    case "RECLASS_OUT":
      return "Reclassificação (saída)";
    case "RECLASS_IN":
      return "Reclassificação (entrada)";
    case "ADJUSTMENT":
      return "Ajuste";
    case "QUARANTINE_IN":
      return "Entrada quarentena";
    case "QUARANTINE_OUT":
      return "Saída quarentena";
    case "SHORTAGE":
      return "Falta";
    case "SURPLUS":
      return "Sobra";
    case "DAMAGE":
      return "Avaria";
    case "REVERSAL":
      return "Estorno";
    default:
      return type?.trim() || "—";
  }
}

export function receiptTypeLabel(type: string | null | undefined): string {
  switch (type) {
    case "BONDED_IN":
      return "Entrada entreposto";
    case "DOMESTIC_IN":
      return "Entrada doméstica";
    case "RECLASS":
      return "Reclassificação";
    case "ADJUSTMENT":
      return "Ajuste";
    default:
      return type?.trim() || "—";
  }
}

export function locationTypeLabel(type: string | null | undefined): string {
  switch (type) {
    case "BONDED":
      return "Entreposto";
    case "DOMESTIC":
      return "Doméstico";
    case "QUARANTINE":
      return "Quarentena";
    default:
      return type?.trim() || "—";
  }
}

export function receiptStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "DRAFT":
      return "Rascunho";
    case "CONFIRMED":
      return "Confirmado";
    case "REVERSED":
      return "Estornado";
    default:
      return status?.trim() || "—";
  }
}

export function nationalizationStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "DRAFT":
      return "Rascunho";
    case "CONFIRMED":
      return "Confirmada";
    case "REVERSED":
      return "Estornada";
    default:
      return status?.trim() || "—";
  }
}

export function fundingStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "DRAFT":
      return "Rascunho";
    case "CONFIRMED":
      return "Confirmado";
    case "CANCELLED":
      return "Cancelado";
    default:
      return status?.trim() || "—";
  }
}
