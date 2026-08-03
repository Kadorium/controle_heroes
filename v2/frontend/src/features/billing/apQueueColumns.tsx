import type { ReactNode } from "react";
import {
  EntityRef,
  FxDisplay,
  MoneyDisplay,
  RowAction,
  RowLink,
  StatusBadge,
  formatDateOnly,
  formatPendencies,
  type OperationalColumnDef,
} from "../../ui";

export type ApQueueRow = Record<string, unknown> & { id: string | number };

function invoiceLabel(number: unknown) {
  const n = typeof number === "string" && number.trim() ? number.trim() : null;
  return n ?? "—";
}

function orderLabel(code: unknown) {
  const c = typeof code === "string" && code.trim() ? code.trim() : null;
  return c ?? "—";
}

function dueCell(row: ApQueueRow): ReactNode {
  const days = Number(row.days_overdue);
  const due = formatDateOnly(String(row.due_date));
  return days > 0 ? `${due} · ${days}d` : due;
}

/** Política de colunas SCR-008 — estável em module scope (Onda B). */
export const AP_QUEUE_COLUMNS: OperationalColumnDef<ApQueueRow>[] = [
  {
    id: "due",
    header: "Vencimento",
    visibility: "always",
    priority: 0,
    minWidth: "8rem",
    truncate: false,
    cell: (row) => dueCell(row),
  },
  {
    id: "supplier",
    header: "Fornecedor",
    visibility: "always",
    priority: 0,
    minWidth: "10rem",
    truncate: true,
    cell: (row) => {
      const isCustoms = row.source_type === "CUSTOMS_FUNDING";
      const name =
        (typeof row.payee_display_name === "string" && row.payee_display_name.trim()
          ? row.payee_display_name
          : null) || (row.supplier_name as string | null);
      return (
        <span className="stack-tight">
          <EntityRef primary={name} missingLabel="Fornecedor não identificado" />
          {isCustoms ? (
            <span className="muted" data-testid="ap-origin-customs">
              Numerário
            </span>
          ) : null}
        </span>
      );
    },
  },
  {
    id: "invoice",
    header: "Fatura",
    visibility: "always",
    priority: 0,
    minWidth: "7rem",
    truncate: true,
    cell: (row) => {
      const invText = invoiceLabel(row.invoice_number);
      if (invText === "—") return "—";
      return (
        <RowLink to={`/invoices/${row.invoice_id}`} onClick={(e) => e.stopPropagation()}>
          {invText}
        </RowLink>
      );
    },
  },
  {
    id: "balance",
    header: "Saldo",
    visibility: "always",
    priority: 0,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => (
      <MoneyDisplay amount={String(row.balance)} currency={String(row.currency)} />
    ),
  },
  {
    id: "status",
    header: "Status",
    visibility: "always",
    priority: 0,
    minWidth: "6rem",
    cell: (row) => <StatusBadge status={String(row.status)} entity="payable" />,
  },
  {
    id: "order",
    header: "Pedido",
    visibility: "standard",
    priority: 1,
    minWidth: "7rem",
    truncate: true,
    cell: (row) => {
      const ordText = orderLabel(row.order_code);
      if (ordText === "—") return "—";
      return (
        <RowLink to={`/orders/${row.order_id}`} onClick={(e) => e.stopPropagation()}>
          {ordText}
        </RowLink>
      );
    },
  },
  {
    id: "amount",
    header: "Valor",
    visibility: "standard",
    priority: 1,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => (
      <MoneyDisplay amount={String(row.amount)} currency={String(row.currency)} />
    ),
  },
  {
    id: "fx",
    header: "Câmbio / BRL",
    visibility: "wide",
    priority: 2,
    minWidth: "8rem",
    truncate: true,
    align: "end",
    cell: (row) => (
      <span className="stack-tight">
        <FxDisplay rate={row.fx_projected_rate as string | null} />
        <MoneyDisplay amount={row.fx_projected_brl as string | null} currency="BRL" />
      </span>
    ),
  },
  {
    id: "pendencies",
    header: "Pendências",
    visibility: "wide",
    priority: 2,
    minWidth: "8rem",
    truncate: true,
    cell: (row) => formatPendencies(row.pendencies),
  },
  {
    id: "fxAction",
    header: "",
    visibility: "always",
    priority: 3,
    minWidth: "4.5rem",
    cell: (row) => (
      <RowAction to={`/payables/${row.id}/fx`} onClick={(e) => e.stopPropagation()}>
        Câmbio
      </RowAction>
    ),
  },
];
