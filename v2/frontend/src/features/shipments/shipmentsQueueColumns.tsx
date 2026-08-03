import type { ShipmentListItem } from "./shipmentsApi";
import {
  RowLink,
  StatusBadge,
  formatDateOnly,
  formatDateTime,
  formatQuantity,
  type OperationalColumnDef,
} from "../../ui";

export type ShipmentsQueueColumnsContext = {
  returnTo: string;
  onRememberRow: (id: number) => void;
};

function displayStatus(row: ShipmentListItem) {
  return row.cancelled_at ? "CANCELLED" : row.status;
}

/** Colunas fila operacional de embarques — factory (RowLink depende de returnTo). */
export function createShipmentsQueueColumns(
  ctx: ShipmentsQueueColumnsContext,
): OperationalColumnDef<ShipmentListItem>[] {
  return [
    {
      id: "code",
      header: "Código",
      visibility: "always",
      priority: 0,
      minWidth: "8rem",
      truncate: true,
      cell: (row) => (
        <RowLink
          to={`/shipments/${row.id}`}
          state={{ returnTo: ctx.returnTo }}
          onClick={() => ctx.onRememberRow(row.id)}
        >
          {row.code}
        </RowLink>
      ),
    },
    {
      id: "status",
      header: "Status",
      visibility: "always",
      priority: 0,
      minWidth: "6.5rem",
      cell: (row) => <StatusBadge status={displayStatus(row)} entity="shipment" />,
    },
    {
      id: "route",
      header: "Rota",
      visibility: "always",
      priority: 0,
      minWidth: "10rem",
      truncate: true,
      cell: (row) => {
        const parts = [row.origin, row.destination].filter(Boolean);
        return parts.length ? parts.join(" → ") : "—";
      },
    },
    {
      id: "carrier",
      header: "Transportador",
      visibility: "standard",
      priority: 1,
      minWidth: "8rem",
      truncate: true,
      cell: (row) => row.carrier_name_snapshot?.trim() || "—",
    },
    {
      id: "modal",
      header: "Modal",
      visibility: "standard",
      priority: 1,
      minWidth: "5rem",
      cell: (row) => {
        const code = row.modal?.trim();
        if (!code) return "—";
        const labels: Record<string, string> = {
          SEA: "Marítimo",
          AIR: "Aéreo",
          ROAD: "Rodoviário",
          COURIER: "Courier",
          MULTIMODAL: "Multimodal",
          OTHER: "Outro",
        };
        return labels[code] ?? code;
      },
    },
    {
      id: "planned_departure",
      header: "Saída prev.",
      visibility: "standard",
      priority: 1,
      minWidth: "6.5rem",
      cell: (row) => formatDateOnly(row.planned_departure),
    },
    {
      id: "item_count",
      header: "Itens",
      visibility: "wide",
      priority: 2,
      minWidth: "4rem",
      align: "end",
      cell: (row) => formatQuantity(String(row.item_count)),
    },
    {
      id: "package_count",
      header: "Volumes",
      visibility: "wide",
      priority: 2,
      minWidth: "4.5rem",
      align: "end",
      cell: (row) => formatQuantity(String(row.package_count)),
    },
    {
      id: "updated_at",
      header: "Atualizado",
      visibility: "wide",
      priority: 2,
      minWidth: "8rem",
      cell: (row) => formatDateTime(row.updated_at),
    },
  ];
}
