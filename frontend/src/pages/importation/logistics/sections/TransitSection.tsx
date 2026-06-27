import { useState } from "react";
import { Button, Card, EmptyState, Table } from "../../../../components";
import type { Shipment } from "../../../../api";
import { modalLabel, shipmentStatusLabel } from "../../../../i18n/glossario";

interface Props {
  shipments: Shipment[];
  onUpdate: (shipmentId: number, data: object) => Promise<void>;
}

const TRANSIT_STATUSES = new Set(["SHIPPED", "IN_TRANSIT", "ARRIVED", "DELIVERED"]);

export function TransitSection({ shipments, onUpdate }: Props) {
  const inTransit = shipments.filter((s) => TRANSIT_STATUSES.has(s.status) || s.status !== "PLANNED");
  const [edits, setEdits] = useState<Record<number, { etd_actual: string; eta_actual: string; status: string }>>({});

  if (shipments.length === 0) {
    return (
      <Card id="transito" title="Em trânsito" compact className="stacked-section logistics-phase">
        <EmptyState title="Sem embarques em trânsito" />
      </Card>
    );
  }

  return (
    <Card id="transito" title="Em trânsito" compact className="stacked-section logistics-phase">
      <Table>
        <thead>
          <tr>
            <th>Embarque</th>
            <th>Modal</th>
            <th>Status</th>
            <th>ETD real</th>
            <th>ETA real</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {inTransit.map((s) => {
            const edit = edits[s.id] ?? {
              etd_actual: s.etd_actual ?? "",
              eta_actual: s.eta_actual ?? "",
              status: s.status,
            };
            return (
              <tr key={s.id}>
                <td>{s.shipment_number}</td>
                <td>{modalLabel(s.modal)}</td>
                <td>
                  <select
                    value={edit.status}
                    onChange={(e) =>
                      setEdits((ed) => ({
                        ...ed,
                        [s.id]: { ...edit, status: e.target.value },
                      }))
                    }
                  >
                    {["PLANNED", "SHIPPED", "IN_TRANSIT", "ARRIVED", "DELIVERED"].map((st) => (
                      <option key={st} value={st}>
                        {shipmentStatusLabel(st)}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="date"
                    value={edit.etd_actual}
                    onChange={(e) =>
                      setEdits((ed) => ({
                        ...ed,
                        [s.id]: { ...edit, etd_actual: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <input
                    type="date"
                    value={edit.eta_actual}
                    onChange={(e) =>
                      setEdits((ed) => ({
                        ...ed,
                        [s.id]: { ...edit, eta_actual: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() =>
                      onUpdate(s.id, {
                        status: edit.status,
                        etd_actual: edit.etd_actual || null,
                        eta_actual: edit.eta_actual || null,
                      })
                    }
                  >
                    Salvar
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </Card>
  );
}
