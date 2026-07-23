import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { listOrders, type OrderListItem } from "./ordersApi";
import { canWriteOrders } from "./orderTotals";

type Props = { user: User };

export function OrdersListPage({ user }: Props) {
  const [rows, setRows] = useState<OrderListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await listOrders();
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="error" role="alert">{error}</div>;
  if (rows === null) return <p className="muted">Carregando ordens…</p>;

  return (
    <section className="panel">
      <div className="panel-header">
        <h1>Ordens</h1>
        {canWriteOrders(user) ? (
          <Link className="btn" to="/orders/new">
            Nova ordem
          </Link>
        ) : null}
      </div>
      {rows.length === 0 ? (
        <p className="empty" data-testid="orders-empty">
          Nenhuma ordem — criar ou importar Ordine
        </p>
      ) : (
        <table className="data-table" data-testid="orders-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Data</th>
              <th>Fornecedor</th>
              <th>Status</th>
              <th>Total comercial</th>
              <th>Atualizado</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.id}>
                <td>
                  <Link to={`/orders/${o.id}`}>{o.code}</Link>
                </td>
                <td>{o.order_date}</td>
                <td>{o.supplier_id}</td>
                <td>{o.status}</td>
                <td>
                  {o.commercial_total ??
                    (o.unpriced_item_count > 0 ? "—" : "—")}
                </td>
                <td>{o.updated_at ? new Date(o.updated_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
