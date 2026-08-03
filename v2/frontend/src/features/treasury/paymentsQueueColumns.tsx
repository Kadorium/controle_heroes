import type { Payment } from "./treasuryApi";
import {
  EntityRef,
  MoneyDisplay,
  RowAction,
  StatusBadge,
  formatDateOnly,
  type OperationalColumnDef,
} from "../../ui";

/** Colunas SCR-010 — module-scope. Referência nunca é link (C-010). Sem coluna Moeda. */
export const PAYMENTS_QUEUE_COLUMNS: OperationalColumnDef<Payment>[] = [
  {
    id: "payment_date",
    header: "Data",
    visibility: "always",
    priority: 0,
    minWidth: "6.5rem",
    cell: (row) => formatDateOnly(row.payment_date),
  },
  {
    id: "reference",
    header: "Referência",
    visibility: "always",
    priority: 0,
    minWidth: "8rem",
    truncate: true,
    cell: (row) => {
      const ref = row.external_reference?.trim() || "";
      return ref || "—";
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
    id: "residual",
    header: "Residual",
    visibility: "always",
    priority: 0,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => <MoneyDisplay amount={row.amount_unallocated} currency={row.currency} />,
  },
  {
    id: "status",
    header: "Status",
    visibility: "always",
    priority: 0,
    minWidth: "6rem",
    cell: (row) => <StatusBadge status={row.status} entity="payment" />,
  },
  {
    id: "open",
    header: "",
    visibility: "always",
    priority: 3,
    minWidth: "4.5rem",
    cell: (row) => (
      <RowAction to={`/payments/${row.id}`} data-testid={`payment-open-${row.id}`}>
        Abrir
      </RowAction>
    ),
  },
  {
    id: "amount",
    header: "Valor",
    visibility: "standard",
    priority: 1,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => <MoneyDisplay amount={row.amount} currency={row.currency} />,
  },
  {
    id: "allocated",
    header: "Alocado",
    visibility: "wide",
    priority: 2,
    minWidth: "9rem",
    align: "end",
    cellClassName: "nowrap",
    cell: (row) => <MoneyDisplay amount={row.amount_allocated} currency={row.currency} />,
  },
];
