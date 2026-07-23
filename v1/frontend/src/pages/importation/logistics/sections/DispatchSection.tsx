import { useState } from "react";
import { Button, Card, EmptyState, Table } from "../../../../components";
import { qtyCell, type SkuRow } from "../logisticsUtils";

interface Props {
  rows: SkuRow[];
  dispatchPending: Array<Record<string, unknown>>;
  onCreateShipment: (
    shipmentNumber: string,
    modal: string,
    allocations: Array<{ importation_item_id: number; quantity: number }>,
  ) => Promise<void>;
}

export function DispatchSection({ rows, dispatchPending, onCreateShipment }: Props) {
  const pending = rows.filter((r) => (r.to_dispatch ?? 0) > 0);
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [shipmentNumber, setShipmentNumber] = useState("");
  const [modal, setModal] = useState("OCEAN");
  const [busy, setBusy] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const allocations = Object.entries(selected)
      .filter(([, qty]) => qty && Number(qty) > 0)
      .map(([id, qty]) => ({ importation_item_id: Number(id), quantity: Number(qty) }));
    if (!shipmentNumber.trim() || allocations.length === 0) return;
    setBusy(true);
    try {
      await onCreateShipment(shipmentNumber.trim(), modal, allocations);
      setSelected({});
      setShipmentNumber("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card id="despachar" title="A despachar" compact className="stacked-section logistics-phase">
      {pending.length === 0 && dispatchPending.length === 0 ? (
        <EmptyState title="Nada pendente de despacho" description="Todos os SKUs foram alocados em embarques." />
      ) : (
        <>
          {dispatchPending.length > 0 && (
            <div className="logistics-heroes-block">
              <p className="meta">DA SPEDIRE (Heroes — staging)</p>
              <Table>
                <thead>
                  <tr>
                    <th>Modelo</th>
                    <th className="num">Qtd</th>
                  </tr>
                </thead>
                <tbody>
                  {dispatchPending.map((d, i) => (
                    <tr key={i}>
                      <td>{String(d.model_label ?? d.supplier_sku ?? "—")}</td>
                      <td className="num">{qtyCell(d.quantity_to_dispatch as number | null)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}

          {pending.length > 0 && (
            <>
              <Table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th className="num">Pedida</th>
                    <th className="num">A despachar</th>
                    <th className="num">Qtd neste embarque</th>
                  </tr>
                </thead>
                <tbody>
                  {pending.map((r) => (
                    <tr key={r.importation_item_id}>
                      <td>{r.label}</td>
                      <td className="num">{qtyCell(r.quantity_ordered)}</td>
                      <td className="num sheet-warn">{qtyCell(r.to_dispatch)}</td>
                      <td className="num">
                        <input
                          type="number"
                          min={0}
                          max={r.to_dispatch ?? undefined}
                          className="logistics-qty-input"
                          value={selected[r.importation_item_id] ?? ""}
                          placeholder="0"
                          onChange={(e) =>
                            setSelected((s) => ({ ...s, [r.importation_item_id]: e.target.value }))
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>

              <form className="inline-form" onSubmit={handleCreate}>
                <input
                  placeholder="Nº embarque"
                  value={shipmentNumber}
                  onChange={(e) => setShipmentNumber(e.target.value)}
                  required
                />
                <select value={modal} onChange={(e) => setModal(e.target.value)}>
                  <option value="OCEAN">Marítimo</option>
                  <option value="AIR">Aéreo</option>
                  <option value="OTHER">Outro</option>
                </select>
                <Button type="submit" disabled={busy}>
                  Criar embarque e alocar
                </Button>
              </form>
            </>
          )}
        </>
      )}
    </Card>
  );
}
