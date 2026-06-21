import { useEffect, useState } from "react";
import { dashboardApi, type DashboardSummary } from "../api";
import type { BadgeTone } from "../components";

export const STAGE_LABELS = [
  "Pedido",
  "Proforma",
  "Pago",
  "Embarcado",
  "Trânsito",
  "Aduana",
  "Fechado",
] as const;

export interface ActionItem {
  kind: string;
  label: string;
  detail: string;
  tone: BadgeTone;
}

export interface PendingPayment {
  importationId: number;
  po: string;
  paymentId: number | null;
  invoiceId: number;
  invoiceNumber: string;
  invoiceType: string;
  balance: number;
  currency: string;
  dueDate: string | null;
  isOverdue: boolean;
}

export interface DashboardRow {
  id: number;
  po: string;
  status: string;
  supplierName: string;
  currency: string;
  createdAt: string;
  modal: "AIR" | "OCEAN" | "OTHER" | null;
  stageIndex: number;
  inTransit: boolean;
  openValue: number | null;
  stockedQty: number;
  hasDivergence: boolean;
  divergenceCount: number;
  lcEstimated: number | null;
  lcActual: number | null;
  eta: string | null;
  closurePendingCount: number;
  actionItems: ActionItem[];
  pendingPayments: PendingPayment[];
}

export interface DashboardData {
  loading: boolean;
  summary: DashboardSummary | null;
  rows: DashboardRow[];
  totalOpen: number;
  stageCounts: number[];
}

function num(value: string | null | undefined): number | null {
  if (value == null) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function mapModal(raw: string | null): DashboardRow["modal"] {
  if (raw === "AIR" || raw === "OCEAN" || raw === "OTHER") return raw;
  return null;
}

function mapRow(item: Awaited<ReturnType<typeof dashboardApi.importations>>["items"][0]): DashboardRow {
  return {
    id: item.id,
    po: item.po_number,
    status: item.status,
    supplierName: item.supplier_name,
    currency: item.currency,
    createdAt: item.created_at,
    modal: mapModal(item.modal),
    stageIndex: item.stage_index,
    inTransit: item.in_transit,
    openValue: num(item.open_value),
    stockedQty: item.stocked_qty,
    hasDivergence: item.has_divergence,
    divergenceCount: item.divergence_count,
    lcEstimated: num(item.lc_estimated),
    lcActual: num(item.lc_actual),
    eta: item.eta,
    closurePendingCount: item.closure_pending_count,
    actionItems: item.action_items.map((a) => ({
      kind: a.kind,
      label: a.label,
      detail: a.detail,
      tone: a.tone as BadgeTone,
    })),
    pendingPayments: item.pending_payments.map((p) => ({
      importationId: item.id,
      po: item.po_number,
      paymentId: p.payment_id,
      invoiceId: p.invoice_id,
      invoiceNumber: p.invoice_number,
      invoiceType: p.invoice_type,
      balance: num(p.balance) ?? 0,
      currency: p.currency,
      dueDate: p.due_date,
      isOverdue: p.is_overdue,
    })),
  };
}

export function useDashboardMetrics(): DashboardData {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [rows, setRows] = useState<DashboardRow[]>([]);
  const [totalOpen, setTotalOpen] = useState(0);
  const [stageCounts, setStageCounts] = useState<number[]>(() => STAGE_LABELS.map(() => 0));

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [sum, imps] = await Promise.all([
          dashboardApi.summary(),
          dashboardApi.importations(100),
        ]);
        if (cancelled) return;
        setSummary(sum);
        setRows(imps.items.map(mapRow));
        setTotalOpen(imps.total_open);
        setStageCounts(sum.stage_counts.map((s) => s.count));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { loading, summary, rows, totalOpen, stageCounts };
}
