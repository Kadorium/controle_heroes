import type { ReactNode } from "react";
import { ApProjection, ApReference, apPendingText } from "./apQueuePresentation";
import {
  MoneyDisplay,
  RowAction,
  StatusBadge,
  formatDateOnly,
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
  return <span className="ap-cell-stack"><span className="ap-date">{due}</span>{days > 0 && <span className="ap-secondary ap-overdue">{days} {days === 1 ? "dia" : "dias"} em atraso</span>}</span>;
}

/** Política de colunas SCR-008 — estável em module scope (Onda B). */
export const AP_QUEUE_COLUMNS: OperationalColumnDef<ApQueueRow>[] = [
  {
    id: "due",
    header: "Vencimento",
    visibility: "always",
    priority: 0,
    minWidth: "10rem",
    truncate: false,
    cell: (row) => dueCell(row),
  },
  {
    id: "supplier",
    header: "Fornecedor",
    visibility: "always",
    priority: 0,
    minWidth: "15rem",
    truncate: false,
    cell: (row) => {
      const isCustoms = row.source_type === "CUSTOMS_FUNDING";
      const name =
        (typeof row.payee_display_name === "string" && row.payee_display_name.trim()
          ? row.payee_display_name
          : null) || (row.supplier_name as string | null);
      return (
        <span className="ap-cell-stack">
          {name ? <button type="button" className="ap-name" title={name} aria-label={`Ver nome completo e detalhes: ${name}`}>{name}</button> : <span>Fornecedor não identificado</span>}
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
    minWidth: "12rem",
    truncate: false,
    cell: (row) => {
      const invText = invoiceLabel(row.invoice_number);
      if (invText === "—") return "—";
      return (
        <ApReference text={invText} href={`/invoices/${row.invoice_id}`} entity="Fatura" id={row.invoice_id}/>
      );
    },
  },
  {
    id: "balance",
    header: "Saldo aberto",
    visibility: "always",
    priority: 0,
    minWidth: "10rem",
    align: "end",
    cellClassName: "nowrap ap-balance",
    cell: (row) => (
      <MoneyDisplay amount={String(row.balance)} currency={String(row.currency)} />
    ),
  },
  {
    id: "status",
    header: "Status",
    headerClassName: "ap-status-cell",
    cellClassName: "ap-status-cell",
    visibility: "always",
    priority: 0,
    minWidth: "11rem",
    cell: (row) => <StatusBadge status={String(row.status)} entity="payable" />,
  },
  {
    id: "order",
    header: "Pedido",
    visibility: "standard",
    priority: 1,
    minWidth: "12rem",
    truncate: false,
    cell: (row) => {
      const ordText = orderLabel(row.order_code);
      if (ordText === "—") return "—";
      return (
        <ApReference text={ordText} href={`/orders/${row.order_id}`} entity="Pedido" id={row.order_id}/>
      );
    },
  },
  {
    id: "amount",
    header: "Valor original",
    visibility: "standard",
    priority: 1,
    minWidth: "10rem",
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
    minWidth: "12rem",
    truncate: false,
    align: "end",
    cell: (row) => <ApProjection row={row}/>,
  },
  {
    id: "pendencies",
    header: "Pendências",
    visibility: "wide",
    priority: 2,
    minWidth: "12rem",
    truncate: false,
    cell: (row) => apPendingText(row),
  },
  {
    id: "iban",
    header: "Banco / IBAN",
    visibility: "wide",
    priority: 2,
    minWidth: "15rem",
    truncate: false,
    cell: (row) => {
      const bank = typeof row.destination_bank === "string" ? row.destination_bank.trim() : "";
      const iban = typeof row.destination_iban === "string" ? row.destination_iban.trim() : "";
      if (!bank && !iban) return "—";
      return (
        <span className="ap-cell-stack" data-testid="ap-destination-iban">
          <button type="button" className="ap-name" title={bank} aria-label="Ver dados bancários completos">{bank || "Banco não informado"}</button>
          {iban ? <button type="button" className="ap-name ap-secondary" title={iban} aria-label="Ver IBAN completo">{iban}</button> : null}
        </span>
      );
    },
  },
  {
    id: "fxAction",
    header: "Ação",
    visibility: "always",
    priority: 3,
    minWidth: "8rem",
    cell: (row) =>
      row.source_type === "CUSTOMS_FUNDING" || row.currency === "BRL" ? (
        <span className="muted">Não se aplica</span>
      ) : (
        <RowAction to={`/payables/${row.id}/fx`} onClick={(e) => e.stopPropagation()}>
          Câmbio
        </RowAction>
      ),
  },
];
