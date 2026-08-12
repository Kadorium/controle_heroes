import { Link } from "react-router-dom";
import { RowLink, type OperationalColumnDef } from "../../ui";
import type { DocumentSummary } from "./ingestionApi";

type Opts = {
  returnTo: string;
  onRememberRow: (id: number) => void;
  onDeleteRow?: (row: DocumentSummary) => void;
};

const DOC_TYPE_LABELS: Record<string, string> = {
  ORDINE_COMPRA: "Pedido de compra",
  ORDINE_COMPRA_XLSX: "Pedido (planilha)",
  FATTURA_VENDITA: "Fatura",
  SOLICITACAO_NUMERARIO: "Solicitação de numerário",
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Rascunho",
  IN_REVIEW: "Em revisão",
  READY: "Pronto",
  REJECTED: "Rejeitado",
};

function statusLabel(row: DocumentSummary): string {
  if (row.created_order_id) return "Pedido criado";
  return STATUS_LABELS[row.review_status] ?? row.review_status;
}

export function createIngestionQueueColumns({
  returnTo,
  onRememberRow,
  onDeleteRow,
}: Opts): OperationalColumnDef<DocumentSummary>[] {
  const cols: OperationalColumnDef<DocumentSummary>[] = [
    {
      id: "id",
      header: "Importação",
      visibility: "always",
      priority: 0,
      minWidth: "6rem",
      cell: (row) => (
        <RowLink
          to={`/ingestion/${row.id}`}
          state={{ returnTo }}
          onClick={() => onRememberRow(row.id)}
          data-testid={`ingestion-row-${row.id}`}
        >
          #{row.id}
        </RowLink>
      ),
    },
    {
      id: "doc_type",
      header: "Tipo",
      visibility: "always",
      priority: 1,
      minWidth: "9rem",
      cell: (row) => DOC_TYPE_LABELS[row.doc_type] ?? row.doc_type,
    },
    {
      id: "review_status",
      header: "Status",
      visibility: "always",
      priority: 1,
      minWidth: "8rem",
      cell: (row) => (
        <span data-testid={`ingestion-status-${row.id}`}>{statusLabel(row)}</span>
      ),
    },
    {
      id: "created_order",
      header: "Pedido",
      visibility: "always",
      priority: 1,
      minWidth: "8rem",
      cell: (row) =>
        row.created_order_id ? (
          <Link
            to={`/orders/${row.created_order_id}/commercial`}
            data-testid={`ingestion-order-link-${row.id}`}
            onClick={(e) => e.stopPropagation()}
          >
            {row.created_order_code ?? `#${row.created_order_id}`}
          </Link>
        ) : (
          "—"
        ),
    },
    {
      id: "issues",
      header: "Pendências",
      visibility: "standard",
      priority: 2,
      minWidth: "6rem",
      cell: (row) => row.open_issue_count,
    },
  ];
  if (onDeleteRow) {
    cols.push({
      id: "actions",
      header: "",
      visibility: "always",
      priority: 0,
      minWidth: "5rem",
      cell: (row) =>
        row.created_order_id ? null : (
          <button
            type="button"
            className="ui-button ui-button--ghost"
            data-testid={`ingestion-delete-${row.id}`}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDeleteRow(row);
            }}
          >
            Excluir
          </button>
        ),
    });
  }
  return cols;
}
