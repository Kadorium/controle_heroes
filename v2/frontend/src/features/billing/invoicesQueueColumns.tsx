import type { InvoiceListItem } from "./billingApi";
import {
  EntityRef,
  MoneyDisplay,
  RowLink,
  StatusBadge,
  formatDateOnly,
  invoiceTypeLabel,
  type OperationalColumnDef,
} from "../../ui";

function orderCodeLabel(code: string | null | undefined) {
  const c = typeof code === "string" && code.trim() ? code.trim() : null;
  return c;
}

/** Colunas SCR-006 — module-scope (células sem contexto React). */
export const INVOICES_QUEUE_COLUMNS: OperationalColumnDef<InvoiceListItem>[] = [
  {
    id: "number",
    header: "Número",
    visibility: "always",
    priority: 0,
    minWidth: "7rem",
    truncate: true,
    cell: (row) => <RowLink to={`/invoices/${row.id}`}>{row.invoice_number}</RowLink>,
  },
  {
    id: "order",
    header: "Pedido",
    visibility: "always",
    priority: 0,
    minWidth: "7rem",
    truncate: true,
    cell: (row) => {
      const code = orderCodeLabel(row.order_code);
      if (!code) return "—";
      return <RowLink to={`/orders/${row.order_id}`}>{code}</RowLink>;
    },
  },
  {
    id: "supplier",
    header: "Fornecedor",
    visibility: "always",
    priority: 0,
    minWidth: "10rem",
    truncate: true,
    cell: (row) => (
      <EntityRef primary={row.supplier_name} missingLabel="Fornecedor não identificado" />
    ),
  },
  {
    id: "status",
    header: "Status",
    visibility: "always",
    priority: 0,
    minWidth: "6rem",
    cell: (row) => <StatusBadge status={row.status} entity="invoice" />,
  },
  {
    id: "balance",
    header: "Saldo",
    visibility: "always",
    priority: 0,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => <MoneyDisplay amount={row.balance} currency={row.currency} />,
  },
  {
    id: "invoice_date",
    header: "Data",
    visibility: "standard",
    priority: 1,
    minWidth: "6.5rem",
    cell: (row) => formatDateOnly(row.invoice_date),
  },
  {
    id: "net_amount",
    header: "Líquido",
    visibility: "standard",
    priority: 1,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => <MoneyDisplay amount={row.net_amount} currency={row.currency} />,
  },
  {
    id: "invoice_type",
    header: "Tipo",
    visibility: "wide",
    priority: 2,
    minWidth: "6rem",
    cell: (row) => invoiceTypeLabel(row.invoice_type),
  },
  {
    id: "payable_count",
    header: "Obrigações",
    visibility: "wide",
    priority: 2,
    minWidth: "5rem",
    align: "end",
    cell: (row) =>
      row.payable_count === null || row.payable_count === undefined ? "—" : row.payable_count,
  },
];
