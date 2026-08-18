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
    case "set_password":
      return "Senha definida";
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
    case "shipment.create":
      return "Embarque criado";
    case "shipment.item.add":
      return "Item adicionado ao embarque";
    case "shipment.packages.add":
      return "Volumes adicionados";
    case "shipment.package.contents.set":
      return "Conteúdo do volume definido";
    case "shipment.reference.add":
      return "Referência adicionada";
    case "shipment.summary.upsert":
      return "Totais documentais gravados";
    case "shipment.update":
      return "Embarque atualizado";
    case "shipment.advance":
      return "Status do embarque avançado";
    case "shipment.annul":
      return "Embarque anulado";
    case "shipment.delete":
      return "Embarque excluído";
    case "import_process.create":
      return "Processo criado";
    case "import_process.update":
      return "Processo atualizado";
    case "import_process.submit":
      return "Processo submetido";
    case "import_process.cancel":
      return "Processo cancelado";
    case "import_process.link_invoice":
      return "Fatura vinculada ao processo";
    case "import_process.unlink_invoice":
      return "Fatura desvinculada do processo";
    case "import_process.link_shipment":
      return "Embarque vinculado ao processo";
    case "import_process.unlink_shipment":
      return "Embarque desvinculado do processo";
    case "import_process.allocate_invoice_item":
      return "Item de fatura alocado";
    case "import_process.deallocate_invoice_item":
      return "Item de fatura desalocado";
    case "import_process.allocate_shipment_item":
      return "Item de embarque alocado";
    case "import_process.deallocate_shipment_item":
      return "Item de embarque desalocado";
    case "funding.create":
      return "Numerário criado";
    case "funding.confirm":
      return "Numerário confirmado (obrigação)";
    case "funding.cancel":
      return "Numerário cancelado";
    case "funding.value_bases.replace":
      return "Bases do Numerário alteradas";
    case "nationalization.create":
      return "Liberação criada";
    case "nationalization.add_items":
      return "Quantidades adicionadas à liberação";
    case "nationalization.confirm":
      return "Liberação confirmada";
    case "nationalization.reverse":
      return "Liberação revertida";
    case "goods_receipt.create":
      return "Recebimento criado";
    case "goods_receipt.add_lines":
      return "Linhas adicionadas ao recebimento";
    case "goods_receipt.confirm":
      return "Recebimento confirmado";
    case "goods_receipt.reverse":
      return "Recebimento estornado";
    case "doganale.version.create":
      return "Versão Doganale criada";
    default:
      return action?.trim() || "—";
  }
}
