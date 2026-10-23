import type { DemoManifest } from "./demoManifest";

export type DemoStep = { title: string; path: string; target: string; question: string; see: string; action: string; decision: string; next: string; pdf?: boolean };
const target = (id: string) => `[data-testid="${id}"]`;
const money = (n: string, currency: string) => new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(n));

export function demoSteps(m: DemoManifest): DemoStep[] {
  const i = m.ids, v = m.expected;
  return [
    { title: "Visão gerencial", path: "/dashboard", target: '[data-demo-ready="true"] [data-demo-summary]',
      question: "O que exige atenção agora?", see: "Leia compromissos e a próxima ação. Consulte a origem; cada bloco avisa quando sua informação está indisponível.",
      action: "O gestor identifica prioridades e abre os detalhes dos indicadores.", decision: "Separar compromisso financeiro de andamento físico.", next: "Vamos à origem comercial e ao documento de apoio." },
    { title: "Pedido e documento", path: `/orders/${i.order}/commercial`, target: '[data-demo-document] [data-pdf-ready="true"]', pdf: true,
      question: "O que foi comprado e qual documento sustenta a compra?", see: `Pedido ${m.scenario_id}: dois SKUs, ${v.shipped_units} unidades, ${money(v.order_eur, "EUR")}. PDF sintético renderizado; registros preparados por API, não por ingestão documental.`,
      action: "Conferir itens e documento vinculado ao mesmo pedido.", decision: "Uma origem rastreável para faturamento, logística e custo.", next: "A fatura transforma a compra em obrigação." },
    { title: "Fatura e obrigação", path: `/invoices/${i.invoice}`, target: target("payables-list"),
      question: "Quanto temos a pagar e quando?", see: `Uma parcela persistida. Fatura de ${money(v.order_eur, "EUR")}; saldo em aberto de ${money(v.open_eur, "EUR")}. A tabela mostra vencimento e situação da obrigação.`,
      action: "Conferir condição, obrigação gerada e seu saldo; abrir Contas a pagar para priorizar vencimentos.", decision: "Planejar o desembolso restante sem somar novamente o que já foi alocado.", next: "Vamos distinguir pagamento registrado de obrigação liquidada." },
    { title: "Pagamento e alocação", path: `/payments/${i.payment}`, target: target("alloc-list"),
      question: "O pagamento efetivamente abateu a obrigação?", see: `${money(v.paid_allocated_eur, "EUR")} registrados e alocados à fatura. Não há crédito livre neste pagamento. Registrar o pagamento sozinho não liquidava a obrigação.`,
      action: "Conferir alocação e comprovante; nenhuma confirmação financeira será automatizada.", decision: `Explicar por que ainda faltam ${money(v.open_eur, "EUR")} a pagar.`, next: "O dinheiro e a mercadoria têm acompanhamentos distintos." },
    { title: "Embarque e packing", path: `/shipments/${i.shipment}`, target: target("shipment-items"),
      question: "Onde está a mercadoria?", see: `Embarque com chegada registrada em Santos, ${v.shipped_units} unidades dos mesmos dois SKUs e packing em duas caixas. Chegada não é nacionalização nem entrada no estoque.`,
      action: "Conferir itens, datas, volumes e documento de packing.", decision: "Acompanhar o próximo marco aduaneiro sem antecipar disponibilidade.", next: "Veremos a liberação parcial do mesmo embarque." },
    { title: "Liberação parcial", path: `/customs/${i.process}`, target: target("customs-section-liberacoes"),
      question: "O que já foi liberado e o que ainda depende de ação?", see: `${v.nationalized_received_units} unidades nacionalizadas: 6 Atlas e 4 Aurora. Restam ${v.nationalization_residual_units} unidades. A declaração é sintética e não foi transmitida a órgão externo.`,
      action: "Conferir liberação e saldo; preparar a próxima liberação somente quando houver documentação.", decision: "Tratar o residual real como próxima ação operacional.", next: "A quantidade recebida deve aparecer no estoque." },
    { title: "Estoque disponível", path: `/inventory/sku/${i.product}`, target: target("sku-buckets"),
      question: "Quanto deste SKU pode ser utilizado agora?", see: "Atlas tem 6 unidades recebidas no estoque doméstico. As outras dimensões distinguem recebido, em trânsito e liberado; não devem ser somadas como estoques independentes.",
      action: "Consultar posição e movimentos para localizar a origem do recebimento.", decision: "Evitar prometer como disponível o que ainda não foi recebido.", next: "Fechamos com o custo publicado dos mesmos produtos." },
    { title: "Custo e próxima decisão", path: `/costing/${i.case}`, target: target("costing-result"),
      question: "Quanto custou cada produto e de onde veio esse custo?", see: `Custo revisado publicado: ${money(v.cost_brl, "BRL")} para ${v.shipped_units} unidades, ${money(v.unit_cost_brl, "BRL")} por unidade. Fontes: mercadoria, tributo bruto do numerário em rascunho e despesa documental.`,
      action: "Conferir componentes e fontes na mesma tela. Taxa de planejamento/documental não é câmbio bancário realizado; custo revisado não é fechamento final.", decision: `Próximas ações: pagar o saldo de ${money(v.open_eur, "EUR")} e liberar as ${v.nationalization_residual_units} unidades residuais.`, next: "Demonstração concluída. Saia para explorar livremente ou reinicie sem duplicar dados." },
  ];
}
