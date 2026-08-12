/** Labels de produto (não-status) — tipos, pendências, etc. */

export function invoiceTypeLabel(type: string | null | undefined): string {
  switch (type) {
    case "FINAL":
      return "Final";
    case "PROFORMA":
      return "Pró-forma";
    default:
      return type?.trim() || "—";
  }
}

/**
 * Estado do crédito/saída de caixa vs alocação a Contas a pagar.
 * Nunca use "Contas pagas" / "Liquidados" para adiantamento.
 */
export function paymentAllocationStateLabel(input: {
  status: string | null | undefined;
  amount_allocated: string | number | null | undefined;
  amount_unallocated: string | number | null | undefined;
}): string {
  const status = (input.status || "").toUpperCase();
  if (status === "CANCELLED") return "Cancelado";
  const allocated = Number(input.amount_allocated ?? 0);
  const unallocated = Number(input.amount_unallocated ?? 0);
  if (!Number.isFinite(allocated) || !Number.isFinite(unallocated)) return "—";
  if (allocated <= 0) return "crédito em aberto";
  if (unallocated > 0) return "parcialmente alocado";
  return "totalmente alocado";
}

export function pendencyLabel(code: string): string {
  switch (code) {
    case "OVERDUE":
      return "Vencido";
    case "MISSING_FX":
      return "Sem plano cambial";
    case "OPEN_BALANCE":
      return "Saldo aberto";
    default:
      return code;
  }
}

export function formatPendencies(value: unknown): string {
  if (Array.isArray(value)) {
    const labels = value.map((v) => pendencyLabel(String(v))).filter(Boolean);
    return labels.length ? labels.join(", ") : "—";
  }
  if (typeof value === "string" && value.trim()) {
    return value
      .split(/[,;]/)
      .map((p) => pendencyLabel(p.trim()))
      .filter(Boolean)
      .join(", ");
  }
  return "—";
}

export function discountTypeLabel(type: string | null | undefined): string {
  switch (type) {
    case "NONE":
      return "Nenhum";
    case "UNIT_AMOUNT":
      return "Valor/un";
    case "PERCENT":
      return "%";
    default:
      return type?.trim() || "—";
  }
}

/** Alertas do cockpit — labels de produto (codes estáveis; message pode ser legado). */
export function cockpitAlertLabel(code: string, fallback?: string | null): string {
  switch (code) {
    case "OVERDUE":
      return "Há obrigações vencidas";
    case "MISSING_FX":
      return "Obrigação sem taxa projetada";
    case "UNALLOCATED_CANDIDATE":
      return (
        "Candidatos a alocação do mesmo fornecedor/moeda " +
        "(podem ser de outros pedidos — não são a lista deste pedido)"
      );
    default:
      return fallback?.trim() || code;
  }
}

/** Papel do usuário — label de produto (não enum cru). */
export function roleLabel(role: string | null | undefined): string {
  switch (role) {
    case "admin":
      return "Administrador";
    case "operator":
      return "Operador";
    case "viewer":
      return "Consulta";
    case "buyer":
      return "Compras";
    case "comprador":
      return "Comprador";
    case "treasury":
      return "Tesouraria";
    case "aduana":
      return "Aduana";
    case "estoque":
      return "Estoque";
    default:
      return role?.trim() || "—";
  }
}

/** Ações de auditoria — microcopy de produto. */
export function auditActionLabel(action: string | null | undefined): string {
  switch (action) {
    case "create":
      return "Criação";
    case "confirm":
      return "Confirmação";
    case "add_item":
      return "Item adicionado";
    case "update":
      return "Atualização";
    case "issue":
      return "Emissão";
    case "cancel":
      return "Cancelamento";
    case "allocate":
      return "Alocação";
    case "register":
      return "Registro";
    case "invoice_price_divergence":
      return "Preço da Fattura diferente do pedido";
    default:
      return action?.trim() || "—";
  }
}
