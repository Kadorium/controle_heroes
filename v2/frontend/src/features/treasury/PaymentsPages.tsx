import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { listSuppliers } from "../catalog/catalogApi";
import {
  allocatePayment,
  canAllocateTreasury,
  canWriteTreasury,
  eligiblePayables,
  getPayment,
  listPayments,
  registerPaymentWithFile,
  type EligiblePayable,
  type Payment,
} from "./treasuryApi";
import { PaymentFxPanel } from "./FxPanels";

type Props = { user: User };

export function PaymentsListPage({ user }: Props) {
  const [rows, setRows] = useState<Payment[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void listPayments()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);
  return (
    <section className="panel" data-testid="payments-list">
      <header className="panel-header">
        <h1>Pagamentos</h1>
        {canWriteTreasury(user) ? (
          <Link to="/payments/new" data-testid="new-payment">
            Novo pagamento
          </Link>
        ) : null}
      </header>
      {error ? <div className="error">{error}</div> : null}
      {rows.length === 0 ? <p className="empty">Nenhum pagamento</p> : null}
      <table className="data-table">
        <thead>
          <tr>
            <th>Data</th>
            <th>Fornecedor</th>
            <th>Moeda</th>
            <th>Valor</th>
            <th>Alocado</th>
            <th>Residual</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td>{p.payment_date}</td>
              <td>#{p.supplier_id}</td>
              <td>{p.currency}</td>
              <td>{p.amount}</td>
              <td>{p.amount_allocated}</td>
              <td>{p.amount_unallocated}</td>
              <td>{p.status}</td>
              <td>
                <Link to={`/payments/${p.id}`}>Abrir</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function PaymentCreatePage({ user }: Props) {
  const nav = useNavigate();
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [supplierId, setSupplierId] = useState("");
  const [amount, setAmount] = useState("1000");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [ref, setRef] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void listSuppliers().then((s) => setSuppliers(s.map((x) => ({ id: x.id, name: x.name }))));
  }, []);

  if (!canWriteTreasury(user)) return <div className="error">Sem permissão</div>;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Anexe o comprovante");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("supplier_id", supplierId);
      form.append("amount", amount);
      form.append("currency", "EUR");
      form.append("payment_date", date);
      if (ref) form.append("external_reference", ref);
      form.append("file", file);
      const pay = await registerPaymentWithFile(form);
      nav(`/payments/${pay.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" data-testid="payment-create">
      <h1>Registrar pagamento</h1>
      {error ? <div className="error">{error}</div> : null}
      <form onSubmit={(e) => void onSubmit(e)}>
        <label>
          Fornecedor
          <select
            data-testid="pay-supplier"
            required
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value)}
          >
            <option value="">Selecione</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Data
          <input data-testid="pay-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label>
          Valor EUR
          <input data-testid="pay-amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <label>
          Referência
          <input data-testid="pay-ref" value={ref} onChange={(e) => setRef(e.target.value)} />
        </label>
        <label>
          Comprovante
          <input
            data-testid="pay-doc"
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" data-testid="save-payment" disabled={busy}>
          Registrar
        </button>
      </form>
    </section>
  );
}

export function PaymentDetailPage({ user }: Props) {
  const { paymentId } = useParams();
  const id = Number(paymentId);
  const [pay, setPay] = useState<Payment | null>(null);
  const [elig, setElig] = useState<EligiblePayable[]>([]);
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const p = await getPayment(id);
    setPay(p);
    setElig(await eligiblePayables(id));
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [id]);

  if (!pay) return <p className="muted">Carregando…</p>;

  async function onAllocate() {
    if (!pay) return;
    const lines = elig
      .map((e) => ({
        payable_id: e.id,
        amount: amounts[e.id] || "",
        expected_version: e.version,
      }))
      .filter((l) => l.amount && Number(l.amount) > 0);
    if (!lines.length) {
      setError("Informe ao menos um valor a alocar");
      return;
    }
    if (!window.confirm("Confirmar alocação atômica?")) return;
    setBusy(true);
    setError(null);
    try {
      const next = await allocatePayment(pay.id, {
        expected_version: pay.version,
        idempotency_key: `ui-${pay.id}-${Date.now()}`,
        allocations: lines,
      });
      setPay(next);
      setAmounts({});
      setElig(await eligiblePayables(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" data-testid="payment-detail">
      <p>
        <Link to="/payments">← Pagamentos</Link>
      </p>
      <h1>
        Pagamento #{pay.id} · {pay.currency} {pay.amount}
      </h1>
      <p className="muted">
        Residual {pay.amount_unallocated} · Alocado {pay.amount_allocated} · {pay.status} · v
        {pay.version}
      </p>
      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}
      <h2>Comprovantes</h2>
      <ul>
        {pay.documents.map((d) => (
          <li key={d.id}>{d.original_filename}</li>
        ))}
      </ul>
      <h2>Alocações</h2>
      <ul data-testid="alloc-list">
        {pay.allocations.map((a) => (
          <li key={a.id}>
            Payable #{a.payable_id} · {a.amount}
          </li>
        ))}
      </ul>
      {canAllocateTreasury(user) && pay.status === "REGISTERED" && Number(pay.amount_unallocated) > 0 ? (
        <>
          <h2>Payables elegíveis</h2>
          <table className="data-table" data-testid="eligible-table">
            <thead>
              <tr>
                <th>Payable</th>
                <th>Order</th>
                <th>Invoice</th>
                <th>Venc.</th>
                <th>Saldo</th>
                <th>Alocar</th>
              </tr>
            </thead>
            <tbody>
              {elig.map((e) => (
                <tr key={e.id}>
                  <td>#{e.id}</td>
                  <td>#{e.order_id}</td>
                  <td>#{e.invoice_id}</td>
                  <td>{e.due_date}</td>
                  <td>{e.balance}</td>
                  <td>
                    <input
                      data-testid={`alloc-amt-${e.id}`}
                      value={amounts[e.id] ?? ""}
                      onChange={(ev) => setAmounts({ ...amounts, [e.id]: ev.target.value })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            type="button"
            data-testid="allocate-btn"
            disabled={busy}
            onClick={() => void onAllocate()}
          >
            Alocar
          </button>
        </>
      ) : null}
      {pay.allocations.length > 0 || pay.currency !== "BRL" ? (
        <PaymentFxPanel key={`${pay.id}-${pay.version}`} user={user} paymentId={pay.id} />
      ) : null}
    </section>
  );
}
