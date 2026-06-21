import { useEffect, useState } from "react";
import { shipmentsApi, type ModalChangeLog, type Shipment } from "../api";
import { modalLabel } from "../i18n/glossario";
import { EmptyState, LoadingState } from "../components";

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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!importationId || Number.isNaN(importationId)) {
      setShipments([]);
      setHistory([]);
      setSelectedShip(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setShipments([]);
    setHistory([]);
    setSelectedShip(null);
    setError("");

    (async () => {
      try {
        const list = await shipmentsApi.list(importationId);
        if (cancelled) return;
        setShipments(list);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [importationId]);

  useEffect(() => {
    if (!selectedShip) {
      setHistory([]);
      return;
    }
    shipmentsApi
      .modalHistory(selectedShip)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [selectedShip]);

  async function reload() {
    if (!importationId || Number.isNaN(importationId)) return;
    setLoading(true);
    try {
      setShipments(await shipmentsApi.list(importationId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setLoading(false);
    }
  }

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
      await reload();
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
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  if (loading) {
    return <LoadingState label="Carregando embarques desta ordem..." />;
  }

  return (
    <div>
      <p className="meta logistics-scope">
        Embarques desta ordem · {shipments.length} registro(s)
      </p>
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
      {shipments.length === 0 ? (
        <EmptyState title="Nenhum embarque nesta ordem" description="Registre o primeiro embarque acima." />
      ) : (
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
      )}
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
