import { useEffect, useState } from "react";
import { importsApi, type ReviewQueueItem } from "../api";

export function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      setItems(await importsApi.reviewQueue());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="card">
      <h1>Fila de Revisão</h1>
      <p className="meta">Linhas ambíguas ou com campos vazios aguardam revisão humana.</p>
      {error && <p className="error">{error}</p>}
      <table className="data-table">
        <thead>
          <tr>
            <th>Linha</th>
            <th>Motivo</th>
            <th>Prioridade</th>
            <th>PO</th>
            <th>SKU</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.staging_row?.row_number ?? item.staging_row_id}</td>
              <td>{item.reason}</td>
              <td>{item.priority}</td>
              <td>{item.staging_row?.parsed_data_json?.po_number ?? "—"}</td>
              <td>{item.staging_row?.parsed_data_json?.sku ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <p className="meta">Nenhum item pendente.</p>}
    </div>
  );
}
