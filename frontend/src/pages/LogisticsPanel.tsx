import { useEffect, useState } from "react";
import { importationsApi, shipmentsApi, type ModalChangeLog, type Shipment } from "../api";
import { modalLabel, shipmentStatusLabel } from "../i18n/glossario";

interface Props {
  importationId: number;
}

export function LogisticsPanel({ importationId }: Props) {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [history, setHistory] = useState<ModalChangeLog[]>([]);
  const [selectedShip, setSelectedShip] = useState<number | null>(null);
  const [shipmentNumber, setShipmentNumber] = useState("");
  const [modal, setModal] = useState("OCEAN");
  const [error, setError] = useState("");

  async function load() {
    const list = await shipmentsApi.list(importationId);
    setShipments(list);
    if (list.length && selectedShip) {
      setHistory(await shipmentsApi.modalHistory(selectedShip));
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [importationId, selectedShip]);

  async function createShipment(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await shipmentsApi.create({
        importation_id: importationId,
        shipment_number: shipmentNumber,
        modal,
        bl_number: modal === "OCEAN" ? "BL-NEW" : undefined,
        awb_number: modal === "AIR" ? "AWB-NEW" : undefined,
      });
      setShipmentNumber("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  async function changeModal(shipmentId: number) {
    setError("");
    try {
      await shipmentsApi.changeModal(shipmentId, {
        new_modal: "AIR",
        reason_code: "MODAL_CHANGE_URGENCY",
        comment: "Alteração via UI",
      });
      setSelectedShip(shipmentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  return (
    <div>
      {error && <p className="error">{error}</p>}
      <form className="inline-form" onSubmit={createShipment}>
        <input
          placeholder="Nº embarque"
          value={shipmentNumber}
          onChange={(e) => setShipmentNumber(e.target.value)}
          required
        />
        <select value={modal} onChange={(e) => setModal(e.target.value)}>
          <option value="OCEAN">{modalLabel("OCEAN")}</option>
          <option value="AIR">{modalLabel("AIR")}</option>
          <option value="OTHER">{modalLabel("OTHER")}</option>
        </select>
        <button type="submit">Novo embarque</button>
      </form>
      <table className="data-table">
        <thead>
          <tr>
            <th>Número</th>
            <th>Modal</th>
            <th>Modal anterior</th>
            <th>BL/AWB</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {shipments.map((s) => (
            <tr key={s.id}>
              <td>{s.shipment_number}</td>
              <td>
                <span className="badge">{modalLabel(s.modal)}</span>
              </td>
              <td>{s.modal_previous ? modalLabel(s.modal_previous) : "—"}</td>
              <td>{s.bl_number || s.awb_number || "—"}</td>
              <td>
                <button type="button" onClick={() => setSelectedShip(s.id)}>
                  Histórico
                </button>
                {s.modal === "OCEAN" && (
                  <button type="button" onClick={() => changeModal(s.id)}>
                    → AIR
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {selectedShip && history.length > 0 && (
        <section>
          <h2>Histórico de modal</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>De</th>
                <th>Para</th>
                <th>Comentário</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{modalLabel(h.from_modal)}</td>
                  <td>{modalLabel(h.to_modal)}</td>
                  <td>{h.comment ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
