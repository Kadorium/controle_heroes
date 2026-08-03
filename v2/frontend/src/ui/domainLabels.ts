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
      return "Pagamentos com residual (candidatos a alocação — não são vínculos com o pedido)";
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
    default:
      return action?.trim() || "—";
  }
}
