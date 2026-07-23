import { useState } from "react";
import { Button, Card, EditableCell, EmptyState, Table } from "../../../../components";
import type { ModalChangeLog, Shipment, ShipmentItem } from "../../../../api";
import { modalLabel, shipmentStatusLabel } from "../../../../i18n/glossario";
import { fmtDate } from "../../../../utils/formatDate";
import { itemsForShipment, qtyCell, type SkuRow } from "../logisticsUtils";

interface Props {
  shipments: Shipment[];
  itemsByShipment: Record<number, ShipmentItem[]>;
  skuRows: SkuRow[];
  onAddItem: (shipmentId: number, itemId: number, qty: number) => Promise<void>;
  onUpdateShipment: (shipmentId: number, data: Record<string, string | null>) => Promise<void>;
  onChangeModal: (shipmentId: number, newModal: string, comment: string) => Promise<void>;
  onLoadHistory: (shipmentId: number) => Promise<ModalChangeLog[]>;
}

function skuLabelForItem(itemId: number, skuRows: SkuRow[], item?: ShipmentItem): string {
  const row = skuRows.find((r) => r.importation_item_id === itemId);
  if (row) return row.label;
  return item?.supplier_sku || item?.description || `#${itemId}`;
}

function oppositeModal(modal: string): { code: string; label: string } | null {
  if (modal === "OCEAN") return { code: "AIR", label: "Aéreo" };
  if (modal === "AIR") return { code: "OCEAN", label: "Marítimo" };
  return null;
}

export function ShipmentsSection({
  shipments,
  itemsByShipment,
  skuRows,
  onAddItem,
  onUpdateShipment,
  onChangeModal,
  onLoadHistory,
}: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [addQty, setAddQty] = useState<Record<string, string>>({});
  const [addItemId, setAddItemId] = useState<Record<number, string>>({});
  const [history, setHistory] = useState<ModalChangeLog[]>([]);
  const [modalComment, setModalComment] = useState<Record<number, string>>({});

  async function toggleExpand(id: number) {
    if (expanded === id) {
      setExpanded(null);
      setHistory([]);
      return;
    }
    setExpanded(id);
    setHistory(await onLoadHistory(id));
  }

  async function saveField(shipmentId: number, field: string, value: string) {
    await onUpdateShipment(shipmentId, { [field]: value.trim() || null });
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
            const altModal = oppositeModal(s.modal);
            return (
              <div key={s.id} className="logistics-shipment-card">
                <div className="logistics-shipment-header">
                  <button type="button" className="logistics-shipment-toggle" onClick={() => toggleExpand(s.id)}>
                    <strong>{s.shipment_number}</strong>
                    <span className="badge">{modalLabel(s.modal)}</span>
                    <span className="badge">{shipmentStatusLabel(s.status)}</span>
                    <span className="meta">
                      {s.eta_planned ? `ETA ${fmtDate(s.eta_planned)}` : "Sem ETA"}
                      {" · "}
                      {items.length} item(ns)
                    </span>
                  </button>
                </div>
                {isOpen && (
                  <div className="logistics-shipment-body">
                    <p className="meta logistics-shipment-hint">
                      Clique nos campos para editar BL/AWB, container e datas planejadas.
                    </p>
                    <div className="logistics-shipment-edit-grid">
                      <label className="logistics-shipment-field">
                        <span>BL (marítimo)</span>
                        <EditableCell
                          value={s.bl_number ?? ""}
                          placeholder="Nº BL"
                          onSave={(v) => saveField(s.id, "bl_number", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>AWB (aéreo)</span>
                        <EditableCell
                          value={s.awb_number ?? ""}
                          placeholder="Nº AWB"
                          onSave={(v) => saveField(s.id, "awb_number", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>Container</span>
                        <EditableCell
                          value={s.container_number ?? ""}
                          placeholder="Nº container"
                          onSave={(v) => saveField(s.id, "container_number", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>ETD planejado</span>
                        <EditableCell
                          type="date"
                          value={s.etd_planned ?? ""}
                          display={s.etd_planned ? fmtDate(s.etd_planned) : undefined}
                          onSave={(v) => saveField(s.id, "etd_planned", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>ETA planejado</span>
                        <EditableCell
                          type="date"
                          value={s.eta_planned ?? ""}
                          display={s.eta_planned ? fmtDate(s.eta_planned) : undefined}
                          onSave={(v) => saveField(s.id, "eta_planned", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>ETD real</span>
                        <EditableCell
                          type="date"
                          value={s.etd_actual ?? ""}
                          display={s.etd_actual ? fmtDate(s.etd_actual) : undefined}
                          onSave={(v) => saveField(s.id, "etd_actual", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>ETA real</span>
                        <EditableCell
                          type="date"
                          value={s.eta_actual ?? ""}
                          display={s.eta_actual ? fmtDate(s.eta_actual) : undefined}
                          onSave={(v) => saveField(s.id, "eta_actual", v)}
                        />
                      </label>
                      <label className="logistics-shipment-field">
                        <span>Status</span>
                        <EditableCell
                          type="select"
                          value={s.status}
                          display={shipmentStatusLabel(s.status)}
                          options={["PLANNED", "SHIPPED", "IN_TRANSIT", "ARRIVED", "DELIVERED"].map((st) => ({
                            value: st,
                            label: shipmentStatusLabel(st),
                          }))}
                          onSave={(v) => saveField(s.id, "status", v)}
                        />
                      </label>
                    </div>
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
                        aria-label="SKU para alocar"
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
                        aria-label="Quantidade"
                      />
                      <Button type="submit" variant="secondary">
                        Alocar item
                      </Button>
                    </form>
                    {altModal && (
                      <div className="inline-form logistics-modal-change">
                        <input
                          placeholder="Motivo da alteração de modal"
                          value={modalComment[s.id] ?? ""}
                          onChange={(e) =>
                            setModalComment((c) => ({ ...c, [s.id]: e.target.value }))
                          }
                        />
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() =>
                            onChangeModal(
                              s.id,
                              altModal.code,
                              modalComment[s.id]?.trim() || "Alteração via UI",
                            )
                          }
                        >
                          {modalLabel(s.modal)} → {altModal.label}
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
