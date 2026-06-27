import { useState } from "react";
import { Button, Card, EmptyState, Table } from "../../../../components";
import type { ModalChangeLog, Shipment, ShipmentItem } from "../../../../api";
import { modalLabel, shipmentStatusLabel } from "../../../../i18n/glossario";
import { itemsForShipment, qtyCell, type SkuRow } from "../logisticsUtils";

interface Props {
  shipments: Shipment[];
  itemsByShipment: Record<number, ShipmentItem[]>;
  skuRows: SkuRow[];
  onAddItem: (shipmentId: number, itemId: number, qty: number) => Promise<void>;
  onChangeModal: (shipmentId: number, newModal: string, comment: string) => Promise<void>;
  onLoadHistory: (shipmentId: number) => Promise<ModalChangeLog[]>;
}

function skuLabelForItem(itemId: number, skuRows: SkuRow[], item?: ShipmentItem): string {
  const row = skuRows.find((r) => r.importation_item_id === itemId);
  if (row) return row.label;
  return item?.supplier_sku || item?.description || `#${itemId}`;
}

export function ShipmentsSection({
  shipments,
  itemsByShipment,
  skuRows,
  onAddItem,
  onChangeModal,
  onLoadHistory,
}: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [addQty, setAddQty] = useState<Record<string, string>>({});
  const [addItemId, setAddItemId] = useState<Record<number, string>>({});
  const [history, setHistory] = useState<ModalChangeLog[]>([]);
  const [modalComment, setModalComment] = useState("");

  async function toggleExpand(id: number) {
    if (expanded === id) {
      setExpanded(null);
      setHistory([]);
      return;
    }
    setExpanded(id);
    setHistory(await onLoadHistory(id));
  }

  return (
    <Card id="embarques" title="Embarques" compact className="stacked-section logistics-phase">
      {shipments.length === 0 ? (
        <EmptyState title="Nenhum embarque" description="Registre embarques na seção A despachar." />
      ) : (
        <div className="logistics-shipment-list">
          {shipments.map((s) => {
            const items = itemsForShipment(s.id, itemsByShipment);
            const isOpen = expanded === s.id;
            return (
              <div key={s.id} className="logistics-shipment-card">
                <div className="logistics-shipment-header">
                  <button type="button" className="logistics-shipment-toggle" onClick={() => toggleExpand(s.id)}>
                    <strong>{s.shipment_number}</strong>
                    <span className="badge">{modalLabel(s.modal)}</span>
                    <span className="badge">{shipmentStatusLabel(s.status)}</span>
                    <span className="meta">{items.length} item(ns)</span>
                  </button>
                </div>
                {isOpen && (
                  <div className="logistics-shipment-body">
                    <dl className="logistics-shipment-meta">
                      <div>
                        <dt>BL/AWB</dt>
                        <dd>{s.bl_number || s.awb_number || "—"}</dd>
                      </div>
                      <div>
                        <dt>Container</dt>
                        <dd>{s.container_number || "—"}</dd>
                      </div>
                      <div>
                        <dt>ETD plan.</dt>
                        <dd>{s.etd_planned || "—"}</dd>
                      </div>
                      <div>
                        <dt>ETA plan.</dt>
                        <dd>{s.eta_planned || "—"}</dd>
                      </div>
                    </dl>
                    <Table>
                      <thead>
                        <tr>
                          <th>SKU</th>
                          <th className="num">Qtd embarcada</th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map((it) => (
                          <tr key={it.id}>
                            <td>{skuLabelForItem(it.importation_item_id, skuRows, it)}</td>
                            <td className="num">{qtyCell(it.quantity_shipped)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                    <form
                      className="inline-form"
                      onSubmit={async (e) => {
                        e.preventDefault();
                        const itemId = Number(addItemId[s.id]);
                        const qty = Number(addQty[s.id]);
                        if (!itemId || !qty) return;
                        await onAddItem(s.id, itemId, qty);
                        setAddQty((a) => ({ ...a, [s.id]: "" }));
                      }}
                    >
                      <select
                        value={addItemId[s.id] ?? ""}
                        onChange={(e) => setAddItemId((a) => ({ ...a, [s.id]: e.target.value }))}
                      >
                        <option value="">SKU…</option>
                        {skuRows.map((r) => (
                          <option key={r.importation_item_id} value={r.importation_item_id}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min={1}
                        placeholder="Qtd"
                        value={addQty[s.id] ?? ""}
                        onChange={(e) => setAddQty((a) => ({ ...a, [s.id]: e.target.value }))}
                      />
                      <Button type="submit" variant="secondary">
                        Alocar item
                      </Button>
                    </form>
                    {s.modal === "OCEAN" && (
                      <div className="inline-form">
                        <input
                          placeholder="Motivo alteração modal"
                          value={modalComment}
                          onChange={(e) => setModalComment(e.target.value)}
                        />
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => onChangeModal(s.id, "AIR", modalComment || "Alteração via UI")}
                        >
                          → Aéreo
                        </Button>
                      </div>
                    )}
                    {history.length > 0 && (
                      <div className="logistics-modal-history">
                        <p className="meta">Histórico de modal</p>
                        <ul>
                          {history.map((h) => (
                            <li key={h.id}>
                              {modalLabel(h.from_modal)} → {modalLabel(h.to_modal)}: {h.comment ?? "—"}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
