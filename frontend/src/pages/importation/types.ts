import type {
  DocumentAttachment,
  FinancialSummary,
  Importation,
  ImportationItem,
  Invoice,
} from "../api";

export type ImportationSection =
  | "resumo"
  | "itens"
  | "invoices"
  | "financeiro"
  | "documentos"
  | "logistica"
  | "aduaneiro"
  | "conciliacao"
  | "historico";

export interface SidebarGroup {
  label: string;
  items: { path: ImportationSection; label: string }[];
}

export const IMPORTATION_SIDEBAR_GROUPS: SidebarGroup[] = [
  {
    label: "Visão geral",
    items: [{ path: "resumo", label: "Visão Geral" }],
  },
  {
    label: "Operação",
    items: [
      { path: "invoices", label: "Faturas e pagamentos" },
      { path: "itens", label: "Produtos e quantidades" },
      { path: "logistica", label: "Logística e nacionalização" },
      { path: "financeiro", label: "Crédito / conta corrente" },
      { path: "documentos", label: "Documentos" },
    ],
  },
  {
    label: "Fechamento",
    items: [
      { path: "conciliacao", label: "Conciliação e fechamento" },
      { path: "historico", label: "Histórico" },
    ],
  },
];

export interface ImportationOutletContext {
  id: number;
  imp: Importation;
  items: ImportationItem[];
  invoices: Invoice[];
  summary: FinancialSummary | null;
  entityDocs: DocumentAttachment[];
  error: string;
  setError: (msg: string) => void;
  reload: () => Promise<void>;
}

export interface ChecklistItem {
  id: string;
  label: string;
  passed: boolean;
  blocking_count?: number;
}

export const CHECKLIST_ROUTE_MAP: Record<string, (id: number) => string> = {
  invoices: (id) => `/importacoes/${id}/invoices`,
  finance: (id) => `/importacoes/${id}/financeiro`,
  customs: (id) => `/importacoes/${id}/logistica#aduana`,
  proforma: (id) => `/importacoes/${id}/documentos`,
  landed_cost: (id) => `/importacoes/${id}/logistica#landed-cost`,
  nationalization: (id) => `/importacoes/${id}/logistica#nacionalizacao`,
  reconciliations: (id) => `/importacoes/${id}/conciliacao#conciliacao`,
  closure: (id) => `/importacoes/${id}/conciliacao#fechamento`,
  divergencia: (id) => `/importacoes/${id}/conciliacao#conciliacao`,
  "DI/DUIMP": (id) => `/importacoes/${id}/logistica#aduana`,
};

export const ACTION_ROUTE_MAP: Record<string, (id: number) => string> = {
  ...CHECKLIST_ROUTE_MAP,
  customs: (id) => `/importacoes/${id}/logistica#aduana`,
};
