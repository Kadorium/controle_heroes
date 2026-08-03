import type { OrderListRow } from "../reporting/reportingApi";
import {
  EntityRef,
  MoneyDisplay,
  RowLink,
  StatusBadge,
  formatDateOnly,
  formatPendencies,
  type OperationalColumnDef,
} from "../../ui";

export type OrdersQueueColumnsContext = {
  returnTo: string;
  onRememberRow: (id: number) => void;
};

/** Colunas SCR-003 — factory (RowLink depende de returnTo / remember). */
export function createOrdersQueueColumns(
  ctx: OrdersQueueColumnsContext,
): OperationalColumnDef<OrderListRow>[] {
  return [
    {
      id: "code",
      header: "Código",
      visibility: "always",
      priority: 0,
      minWidth: "7rem",
      truncate: true,
      cell: (row) => (
        <RowLink
          to={`/orders/${row.id}`}
          state={{ returnTo: ctx.returnTo }}
          onClick={() => ctx.onRememberRow(row.id)}
        >
          {row.code}
        </RowLink>
      ),
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
      cell: (row) => <StatusBadge status={row.status} entity="order" />,
    },
    {
      id: "open_balance",
      header: "Saldo",
      visibility: "always",
      priority: 0,
      minWidth: "9rem",
      align: "end",
      cellClassName: "nowrap",
      cell: (row) => <MoneyDisplay amount={row.open_balance} currency={row.currency} />,
    },
    {
      id: "order_date",
      header: "Data",
      visibility: "standard",
      priority: 1,
      minWidth: "6.5rem",
      cell: (row) => formatDateOnly(row.order_date),
    },
    {
      id: "commercial_total",
      header: "Subtotal precificado",
      visibility: "standard",
      priority: 1,
      minWidth: "9rem",
      align: "end",
      cellClassName: "nowrap",
      cell: (row) => <MoneyDisplay amount={row.commercial_total} currency={row.currency} />,
    },
    {
      id: "next_due_date",
      header: "Próx. venc.",
      visibility: "standard",
      priority: 1,
      minWidth: "6.5rem",
      cell: (row) => formatDateOnly(row.next_due_date),
    },
    {
      id: "invoiced_amount",
      header: "Faturado",
      visibility: "wide",
      priority: 2,
      minWidth: "9rem",
      align: "end",
      cellClassName: "nowrap",
      cell: (row) => <MoneyDisplay amount={row.invoiced_amount} currency={row.currency} />,
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
  ];
}
