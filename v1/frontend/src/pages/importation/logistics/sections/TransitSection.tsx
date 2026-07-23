import { Card, EditableCell, EmptyState, Table } from "../../../../components";
import type { Shipment } from "../../../../api";
import { modalLabel, shipmentStatusLabel } from "../../../../i18n/glossario";
import { fmtDate } from "../../../../utils/formatDate";

interface Props {
  shipments: Shipment[];
  onUpdate: (shipmentId: number, data: Record<string, string | null>) => Promise<void>;
}

const STATUS_OPTIONS = ["PLANNED", "SHIPPED", "IN_TRANSIT", "ARRIVED", "DELIVERED"].map((st) => ({
  value: st,
  label: shipmentStatusLabel(st),
}));

export function TransitSection({ shipments, onUpdate }: Props) {
  if (shipments.length === 0) {
    return (
      <Card id="transito" title="Em trânsito" compact className="stacked-section logistics-phase">
        <EmptyState title="Sem embarques" description="Crie um embarque na seção anterior." />
      </Card>
    );
  }

  async function saveField(shipmentId: number, field: string, value: string) {
    await onUpdate(shipmentId, { [field]: value.trim() || null });
  }

  return (
    <Card id="transito" title="Em trânsito" compact className="stacked-section logistics-phase">
      <p className="meta logistics-shipment-hint">
        Visão rápida — clique em qualquer célula para atualizar status e datas (planejadas ou reais).
      </p>
      <div className="sheet-grid-wrap">
        <Table className="sheet-grid logistics-transit-table">
          <thead>
            <tr>
              <th>Embarque</th>
              <th>Modal</th>
              <th>Status</th>
              <th>ETD plan.</th>
              <th>ETA plan.</th>
              <th>ETD real</th>
              <th>ETA real</th>
            </tr>
          </thead>
          <tbody>
            {shipments.map((s) => (
              <tr key={s.id}>
                <td>
                  <strong>{s.shipment_number}</strong>
                </td>
                <td>{modalLabel(s.modal)}</td>
                <td>
                  <EditableCell
                    type="select"
                    value={s.status}
                    display={shipmentStatusLabel(s.status)}
                    options={STATUS_OPTIONS}
                    onSave={(v) => saveField(s.id, "status", v)}
                  />
                </td>
                <td>
                  <EditableCell
                    type="date"
                    value={s.etd_planned ?? ""}
                    display={s.etd_planned ? fmtDate(s.etd_planned) : undefined}
                    onSave={(v) => saveField(s.id, "etd_planned", v)}
                  />
                </td>
                <td>
                  <EditableCell
                    type="date"
                    value={s.eta_planned ?? ""}
                    display={s.eta_planned ? fmtDate(s.eta_planned) : undefined}
                    onSave={(v) => saveField(s.id, "eta_planned", v)}
                  />
                </td>
                <td>
                  <EditableCell
                    type="date"
                    value={s.etd_actual ?? ""}
                    display={s.etd_actual ? fmtDate(s.etd_actual) : undefined}
                    onSave={(v) => saveField(s.id, "etd_actual", v)}
                  />
                </td>
                <td>
                  <EditableCell
                    type="date"
                    value={s.eta_actual ?? ""}
                    display={s.eta_actual ? fmtDate(s.eta_actual) : undefined}
                    onSave={(v) => saveField(s.id, "eta_actual", v)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </Card>
  );
}
