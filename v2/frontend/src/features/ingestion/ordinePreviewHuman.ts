/** RUX-3B-2b — labels humanas do preview Ordine (sem nomes de operação). */

export type PreviewOpLike = {
  op_key: string;
  description?: string | null;
  params?: Record<string, unknown> | null;
};

function paramStr(params: Record<string, unknown> | null | undefined, key: string): string {
  const v = params?.[key];
  if (v == null) return "";
  return String(v).trim();
}

/** Lista em português para o operador; nunca expõe create_supplier / add_item / etc. */
export function humanPreviewSteps(operations: PreviewOpLike[]): string[] {
  const steps: string[] = [];
  const addItems = operations.filter((o) => o.op_key.startsWith("add_item_"));
  const commitmentCount = addItems.filter(
    (o) => String(o.params?.line_kind ?? "").toUpperCase() === "COMMITMENT",
  ).length;
  const productCount = addItems.length - commitmentCount;

  for (const op of operations) {
    if (op.op_key === "create_supplier") {
      const name = paramStr(op.params, "name") || "fornecedor";
      steps.push(`Cadastrar fornecedor ${name}`);
      continue;
    }
    if (op.op_key === "store_document") {
      steps.push("Guardar o documento");
      continue;
    }
    if (op.op_key === "create_order") {
      const code = paramStr(op.params, "code") || "pedido";
      steps.push(`Criar pedido ${code} em rascunho`);
      continue;
    }
    if (op.op_key.startsWith("add_item_")) {
      // Agregado uma vez no fim do grupo
      continue;
    }
    if (op.op_key === "link_document") {
      steps.push("Vincular o documento ao pedido");
      continue;
    }
    if (op.op_key === "skip_order") {
      steps.push(op.description || "Pedido ainda não pode ser criado");
      continue;
    }
    if (op.op_key.startsWith("skip_item_")) {
      steps.push(op.description || "Há uma linha incompleta");
      continue;
    }
    // Outras ops: descrição já humana, sem op_key
    if (op.description) steps.push(op.description);
  }

  if (addItems.length > 0) {
    // Inserir após create_order (antes de link)
    const linkIdx = steps.findIndex((s) => s.startsWith("Vincular o documento"));
    const parts: string[] = [];
    if (commitmentCount > 0) {
      parts.push(
        commitmentCount === 1
          ? "Registrar 1 linha de compromisso (produtos reais virão pela fatura)"
          : `Registrar ${commitmentCount} linhas de compromisso (produtos reais virão pela fatura)`,
      );
    }
    if (productCount > 0) {
      parts.push(
        productCount === 1
          ? "Registrar 1 linha de produto"
          : `Registrar ${productCount} linhas de produto`,
      );
    }
    const block = parts.join(" · ");
    if (linkIdx >= 0) steps.splice(linkIdx, 0, block);
    else steps.push(block);
  }

  return steps;
}
