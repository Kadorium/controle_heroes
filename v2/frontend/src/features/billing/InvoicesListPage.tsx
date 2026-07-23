import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { listInvoices, listPayables, type InvoiceListItem, type Payable } from "./billingApi";

type Props = { user: User };

export function InvoicesListPage({ user: _user }: Props) {
  const [rows, setRows] = useState<InvoiceListItem[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listInvoices(status ? { status } : undefined)
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [status]);

  return (
    <section className="panel" data-testid="invoices-list">
      <h1>Faturas</h1>
      {error ? <div className="error">{error}</div> : null}
      <select data-testid="filter-status" value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">Todas</option>
        <option value="DRAFT">DRAFT</option>
        <option value="ISSUED">ISSUED</option>
        <option value="CANCELLED">CANCELLED</option>
      </select>
      {rows.length === 0 ? <p className="empty">Nenhuma fatura</p> : null}
      <ul>
        {rows.map((r) => (
          <li key={r.id}>
            <Link to={`/invoices/${r.id}`}>
              {r.invoice_number} · ordem #{r.order_id} · {r.status} · {r.net_amount ?? "—"}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function PayablesListPage({ user: _user }: Props) {
  const [rows, setRows] = useState<Payable[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listPayables()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  return (
    <section className="panel" data-testid="payables-list-page">
      <h1>Payables</h1>
      {error ? <div className="error">{error}</div> : null}
      {rows.length === 0 ? <p className="empty">Nenhum payable</p> : null}
      <table className="data-table">
        <thead>
          <tr>
            <th>Invoice</th>
            <th>Seq</th>
            <th>Vencimento</th>
            <th>Valor</th>
            <th>Saldo</th>
            <th>Status</th>
            <th>FX</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td>
                <Link to={`/invoices/${p.invoice_id}`}>#{p.invoice_id}</Link>
              </td>
              <td>{p.sequence}</td>
              <td>{p.due_date}</td>
              <td>{p.amount}</td>
              <td>{p.balance}</td>
              <td>{p.status}</td>
              <td>
                <Link to={`/payables/${p.id}/fx`} data-testid={`payable-fx-link-${p.id}`}>
                  FX
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
