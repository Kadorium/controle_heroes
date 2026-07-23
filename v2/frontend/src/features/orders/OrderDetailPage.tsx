import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { cancelOrder, confirmOrder, getOrder, type Order } from "./ordersApi";
import { canCancelOrders, canWriteOrders } from "./orderTotals";
import { OrderInvoicesPanel } from "../billing/InvoiceDetailPage";

type Props = { user: User };

export function OrderDetailPage({ user }: Props) {
  const { orderId } = useParams();
  const id = Number(orderId);
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("ORDER_CANCEL_UI");
  const [busy, setBusy] = useState(false);

  async function reload() {
    const data = await getOrder(id);
    setOrder(data);
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getOrder(id);
        if (!cancelled) setOrder(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!order) return <p className="muted">Carregando…</p>;

  const editable = order.status === "DRAFT" && canWriteOrders(user);

  async function onConfirm() {
    setBusy(true);
    setError(null);
    try {
      setOrder(await confirmOrder(order!.id, order!.version));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    setBusy(true);
    setError(null);
    try {
      setOrder(
        await cancelOrder(
          order!.id,
          order!.version,
          order!.status === "CONFIRMED" ? reason : undefined,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" data-testid="order-detail">
      <p>
        <Link to="/orders">← Fila</Link>
      </p>
      <header className="panel-header">
        <div>
          <h1>Ordem {order.code}</h1>
          <p className="muted">
            Status {order.status} · Fornecedor #{order.supplier_id} · v{order.version}
          </p>
        </div>
        <div className="actions">
          {editable ? (
            <button type="button" disabled={busy} data-testid="confirm-order" onClick={() => void onConfirm()}>
              Confirmar
            </button>
          ) : null}
          {(order.status === "DRAFT" && canWriteOrders(user)) ||
          (order.status === "CONFIRMED" && canCancelOrders(user)) ? (
            <>
              {order.status === "CONFIRMED" ? (
                <input
                  data-testid="cancel-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  aria-label="Motivo do cancelamento"
                />
              ) : null}
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                data-testid="cancel-order"
                onClick={() => void onCancel()}
              >
                Cancelar
              </button>
            </>
          ) : null}
        </div>
      </header>

      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}

      {!editable && order.status !== "DRAFT" ? (
        <p className="muted" data-testid="readonly-banner">
          Ordem somente leitura ({order.status}).
        </p>
      ) : null}

      <table className="data-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Descrição</th>
            <th>Qtd</th>
            <th>Preço</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {order.items?.map((i) => (
            <tr key={i.id}>
              <td>{i.sku_snapshot}</td>
              <td>{i.description_snapshot}</td>
              <td>{i.quantity}</td>
              <td>{i.unit_price ?? "—"}</td>
              <td>{i.line_total ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p data-testid="detail-commercial-total">
        Total comercial: {order.commercial_total ?? "—"}
        {(order.unpriced_item_count ?? 0) > 0
          ? ` · incompleto (${order.unpriced_item_count} sem preço; subtotal ${order.priced_subtotal})`
          : null}
      </p>

      <h2>Documentos</h2>
      {(order.documents?.length ?? 0) === 0 ? (
        <p className="empty">Nenhum documento vinculado</p>
      ) : (
        <ul>
          {order.documents?.map((d) => (
            <li key={d.id}>{d.original_filename}</li>
          ))}
        </ul>
      )}

      <OrderInvoicesPanel user={user} orderId={order.id} orderStatus={order.status} />

      <button type="button" className="btn-secondary" onClick={() => void reload()}>
        Atualizar
      </button>
    </section>
  );
}
