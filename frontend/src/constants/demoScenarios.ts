export interface DemoScenario {
  id: string;
  poNumber: string;
  title: string;
  description: string;
  path?: (importationId: number) => string;
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "ocean",
    poNumber: "DEMO-01-OCEAN",
    title: "Marítima simples",
    description: "Embarque marítimo básico — ponto de partida para operação OCEAN.",
    path: (id) => `/importacoes/${id}/logistica`,
  },
  {
    id: "air",
    poNumber: "DEMO-02-AIR",
    title: "Aérea simples",
    description: "Fluxo aéreo enxuto para comparar prazos e modal AIR.",
    path: (id) => `/importacoes/${id}/logistica`,
  },
  {
    id: "modal",
    poNumber: "DEMO-03-MODAL",
    title: "Mudança de modal",
    description: "Troca AIR → OCEAN auditada — essencial para revisar histórico logístico.",
    path: (id) => `/importacoes/${id}/logistica`,
  },
  {
    id: "antecipo",
    poNumber: "DEMO-04-3INV",
    title: "Importação com ANTECIPO",
    description: "Três invoices incluindo ANTECIPO — espelha pagamentos antecipados reais.",
    path: (id) => `/importacoes/${id}/invoices`,
  },
  {
    id: "partial",
    poNumber: "DEMO-06-PARTIAL",
    title: "Pagamento parcial",
    description: "Saldo após pagamento parcial liquidado — base para conciliação financeira.",
    path: (id) => `/importacoes/${id}/financeiro`,
  },
  {
    id: "credit",
    poNumber: "DEMO-09-CREDIT",
    title: "Crédito Heroes",
    description: "Crédito disponível e uso parcial — distinto de desconto na invoice.",
    path: (id) => `/importacoes/${id}/financeiro`,
  },
  {
    id: "brazil",
    poNumber: "DEMO-10-BRAZIL",
    title: "Conta corrente Brasil",
    description: "Compensação BR com impacto estimado — política fiscal ainda pendente.",
    path: (id) => `/importacoes/${id}/financeiro`,
  },
  {
    id: "qty",
    poNumber: "DEMO-11-QTY",
    title: "Divergência de quantidade",
    description: "Quantidade pedida ≠ estoque — gatilho de conciliação operacional.",
    path: (id) => `/importacoes/${id}/conciliacao`,
  },
  {
    id: "close",
    poNumber: "DEMO-13-CLOSE",
    title: "Fechamento limpo",
    description: "Importação pronta para fechar sem divergências bloqueantes.",
    path: (id) => `/importacoes/${id}/conciliacao`,
  },
  {
    id: "reopen",
    poNumber: "DEMO-15-REOPEN",
    title: "Reabertura",
    description: "Processo fechado candidato a reabertura com motivo documentado.",
    path: (id) => `/importacoes/${id}/conciliacao`,
  },
];

export const EXPENSE_TYPE_LABELS: Record<string, string> = {
  FREIGHT: "Frete",
  INSURANCE: "Seguro",
  STORAGE: "Armazenagem",
  CUSTOMS_AGENT: "Despachante",
  BANK_FEE: "Taxa bancária",
  LOCAL_TRANSPORT: "Transporte local",
  OTHER: "Outro",
};
