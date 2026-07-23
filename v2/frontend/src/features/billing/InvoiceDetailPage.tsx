import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  createInvoice,
  getInvoice,
  issueInvoice,
  listOrderInvoices,
  replaceItems,
  setTerms,
  uploadInvoiceDocument,
  invoicedQuantities,
  type Invoice,
  type InvoiceListItem,
  type OrderQtyRow,
} from "./billingApi";
import { canIssueBilling, canWriteBilling, lineAmounts, previewPercentPayables } from "./invoiceMath";

type Props = { user: User };

export function OrderInvoicesPanel({ user, orderId, orderStatus }: Props & { orderId: number; orderStatus: string }) {
  const nav = useNavigate();
  const [rows, setRows] = useState<InvoiceListItem[]>([]);
  const [qtys, setQtys] = useState<OrderQtyRow[]>([]);
  const [number, setNumber] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canWrite = canWriteBilling(user);

  async function reload() {
    setRows(await listOrderInvoices(orderId));
    setQtys(await invoicedQuantities(orderId));
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [orderId]);

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      const inv = await createInvoice(orderId, { invoice_number: number.trim() });
      nav(`/invoices/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section data-testid="order-invoices">
      <h2>Faturas</h2>
      {error ? <div className="error">{error}</div> : null}
      {qtys.length > 0 ? (
        <table className="data-table" data-testid="invoiced-qty">
          <thead>
            <tr>
              <th>Item</th>
              <th>Pedida</th>
              <th>Faturada</th>
              <th>Disponível</th>
            </tr>
          </thead>
          <tbody>
            {qtys.map((q) => (
              <tr key={q.order_item_id}>
                <td>#{q.order_item_id}</td>
                <td>{q.ordered_qty}</td>
                <td>{q.issued_qty}</td>
                <td>{q.available_qty}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <ul>
        {rows.map((r) => (
          <li key={r.id}>
            <Link to={`/invoices/${r.id}`}>
              {r.invoice_number} · {r.status} · líquido {r.net_amount ?? "—"}
            </Link>
          </li>
        ))}
        {rows.length === 0 ? <li className="empty">Nenhuma fatura</li> : null}
      </ul>
      {orderStatus === "CONFIRMED" && canWrite ? (
        <div className="actions">
          <input
            data-testid="new-invoice-number"
            placeholder="Número da fatura"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
          />
          <button
            type="button"
            data-testid="create-invoice"
            disabled={busy || !number.trim()}
            onClick={() => void onCreate()}
          >
            Criar fatura
          </button>
        </div>
      ) : null}
    </section>
  );
}

export function InvoiceDetailPage({ user }: Props) {
  const { invoiceId } = useParams();
  const id = Number(invoiceId);
  const [inv, setInv] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [termMode, setTermMode] = useState<"PERCENT" | "AMOUNT">("PERCENT");
  const [terms, setTermsLocal] = useState<{ due_date: string; percent: string; amount: string }[]>([
    { due_date: "", percent: "30", amount: "" },
    { due_date: "", percent: "70", amount: "" },
  ]);

  async function reload() {
    const data = await getInvoice(id);
    setInv(data);
    if (data.terms_mode) setTermMode(data.terms_mode as "PERCENT" | "AMOUNT");
    if (data.terms?.length) {
      setTermsLocal(
        data.terms.map((t) => ({
          due_date: t.due_date,
          percent: t.percent ?? "",
          amount: t.amount ?? "",
        })),
      );
    }
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [id]);

  if (error && !inv) return <div className="error">{error}</div>;
  if (!inv) return <p className="muted">Carregando…</p>;

  const readonly = inv.status !== "DRAFT";
  const canWrite = canWriteBilling(user) && !readonly;
  const canIssue = canIssueBilling(user) && inv.status === "DRAFT";

  async function saveItems() {
    if (!inv) return;
    setBusy(true);
    setError(null);
    try {
      const next = await replaceItems(
        inv.id,
        inv.version,
        (inv.items ?? []).map((i) => ({
          order_item_id: i.order_item_id,
          quantity: i.quantity,
          unit_price_gross: i.unit_price_gross,
          discount_type: i.discount_type,
          discount_unit_amount: i.discount_unit_amount,
          discount_percent: i.discount_percent,
        })),
      );
      setInv(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  async function saveTerms() {
    if (!inv) return;
    setBusy(true);
    setError(null);
    try {
      const cleaned = terms.filter((t) =>
        termMode === "PERCENT"
          ? Boolean(t.due_date && t.percent.trim())
          : Boolean(t.due_date && t.amount.trim()),
      );
      if (!cleaned.length) {
        setError("Informe ao menos uma scadenza com data e valor/%");
        return;
      }
      const next = await setTerms(
        inv.id,
        inv.version,
        termMode,
        cleaned.map((t) =>
          termMode === "PERCENT"
            ? { due_date: t.due_date, percent: t.percent }
            : { due_date: t.due_date, amount: t.amount },
        ),
      );
      setInv(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File | null) {
    if (!file || !inv) return;
    setBusy(true);
    setError(null);
    try {
      await uploadInvoiceDocument(inv.id, file);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  async function onIssue() {
    if (!inv) return;
    if (!window.confirm("Emitir fatura? Após a emissão ela fica somente leitura.")) return;
    setBusy(true);
    setError(null);
    try {
      const next = await issueInvoice(inv.id, inv.version);
      setInv(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  const net = Number(inv.net_amount ?? NaN);
  const preview =
    termMode === "PERCENT" && Number.isFinite(net)
      ? previewPercentPayables(
          net,
          terms.map((t) => Number(t.percent)).filter((n) => Number.isFinite(n)),
        )
      : terms.map((t) => t.amount);

  return (
    <section className="panel" data-testid="invoice-detail">
      <p>
        <Link to={`/orders/${inv.order_id}`}>← Ordem</Link> · <Link to="/invoices">Faturas</Link>
      </p>
      <header className="panel-header">
        <div>
          <h1>
            Fatura {inv.invoice_number}
          </h1>
          <p className="muted">
            {inv.invoice_type} · {inv.status} · {inv.currency} · v{inv.version}
          </p>
        </div>
      </header>

      {readonly ? (
        <p className="muted" data-testid="invoice-readonly">
          Fatura somente leitura ({inv.status}).
        </p>
      ) : null}

      {error ? (
        <div className="error" role="alert" data-testid="invoice-error">
          {error}
        </div>
      ) : null}

      {inv.blockers?.length ? (
        <ul data-testid="invoice-blockers">
          {inv.blockers.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      ) : null}

      <h2>Itens</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Qtd</th>
            <th>Preço bruto</th>
            <th>Desconto</th>
            <th>Valor</th>
            <th>Bruto</th>
            <th>Desc.</th>
            <th>Líquido</th>
          </tr>
        </thead>
        <tbody>
          {(inv.items ?? []).map((item, idx) => {
            const live = lineAmounts({
              quantity: item.quantity,
              unit_price_gross: item.unit_price_gross,
              discount_type: (item.discount_type as "" | null) ?? "",
              discount_unit_amount: item.discount_unit_amount,
              discount_percent: item.discount_percent,
            });
            return (
              <tr key={item.id}>
                <td>{item.sku_snapshot}</td>
                <td>
                  {canWrite ? (
                    <input
                      data-testid={`qty-${idx}`}
                      value={item.quantity}
                      onChange={(e) => {
                        const items = [...(inv.items ?? [])];
                        items[idx] = { ...item, quantity: e.target.value };
                        setInv({ ...inv, items });
                      }}
                    />
                  ) : (
                    item.quantity
                  )}
                </td>
                <td>
                  {canWrite ? (
                    <input
                      data-testid={`price-${idx}`}
                      value={item.unit_price_gross ?? ""}
                      onChange={(e) => {
                        const items = [...(inv.items ?? [])];
                        items[idx] = { ...item, unit_price_gross: e.target.value };
                        setInv({ ...inv, items });
                      }}
                    />
                  ) : (
                    item.unit_price_gross
                  )}
                </td>
                <td>
                  {canWrite ? (
                    <select
                      data-testid={`discount-type-${idx}`}
                      value={item.discount_type ?? ""}
                      onChange={(e) => {
                        const items = [...(inv.items ?? [])];
                        items[idx] = {
                          ...item,
                          discount_type: e.target.value || null,
                          discount_unit_amount: null,
                          discount_percent: null,
                        };
                        setInv({ ...inv, items });
                      }}
                    >
                      <option value="">(incompleto)</option>
                      <option value="NONE">NONE</option>
                      <option value="UNIT_AMOUNT">€/un</option>
                      <option value="PERCENT">%</option>
                    </select>
                  ) : (
                    item.discount_type ?? "—"
                  )}
                </td>
                <td>
                  {canWrite && item.discount_type === "UNIT_AMOUNT" ? (
                    <input
                      data-testid={`discount-unit-${idx}`}
                      value={item.discount_unit_amount ?? ""}
                      onChange={(e) => {
                        const items = [...(inv.items ?? [])];
                        items[idx] = { ...item, discount_unit_amount: e.target.value };
                        setInv({ ...inv, items });
                      }}
                    />
                  ) : null}
                  {canWrite && item.discount_type === "PERCENT" ? (
                    <input
                      data-testid={`discount-pct-${idx}`}
                      value={item.discount_percent ?? ""}
                      onChange={(e) => {
                        const items = [...(inv.items ?? [])];
                        items[idx] = { ...item, discount_percent: e.target.value };
                        setInv({ ...inv, items });
                      }}
                    />
                  ) : null}
                  {!canWrite
                    ? item.discount_unit_amount ?? item.discount_percent ?? "—"
                    : null}
                </td>
                <td>{live.gross ?? item.line_gross_amount ?? "—"}</td>
                <td>{live.discount ?? item.line_discount_amount ?? "—"}</td>
                <td>{live.net ?? item.line_net_amount ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p data-testid="invoice-net">Líquido: {inv.net_amount ?? "—"}</p>
      {canWrite ? (
        <button type="button" data-testid="save-items" disabled={busy} onClick={() => void saveItems()}>
          Salvar itens
        </button>
      ) : null}

      <h2>Documento</h2>
      <ul>
        {inv.documents?.map((d) => (
          <li key={d.id}>{d.original_filename}</li>
        ))}
      </ul>
      {canWrite ? (
        <input
          data-testid="invoice-doc"
          type="file"
          onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
        />
      ) : null}

      <h2>Scadenze</h2>
      {canWrite ? (
        <div className="actions">
          <label>
            Modo{" "}
            <select
              data-testid="terms-mode"
              value={termMode}
              onChange={(e) => setTermMode(e.target.value as "PERCENT" | "AMOUNT")}
            >
              <option value="PERCENT">Percentual</option>
              <option value="AMOUNT">Valor</option>
            </select>
          </label>
        </div>
      ) : (
        <p>Modo: {inv.terms_mode}</p>
      )}
      {terms.map((t, idx) => (
        <div key={idx} className="actions">
          <input
            data-testid={`term-date-${idx}`}
            type="date"
            disabled={!canWrite}
            value={t.due_date}
            onChange={(e) => {
              const next = [...terms];
              next[idx] = { ...t, due_date: e.target.value };
              setTermsLocal(next);
            }}
          />
          {termMode === "PERCENT" ? (
            <input
              data-testid={`term-pct-${idx}`}
              disabled={!canWrite}
              value={t.percent}
              placeholder="%"
              onChange={(e) => {
                const next = [...terms];
                next[idx] = { ...t, percent: e.target.value };
                setTermsLocal(next);
              }}
            />
          ) : (
            <input
              data-testid={`term-amt-${idx}`}
              disabled={!canWrite}
              value={t.amount}
              placeholder="valor"
              onChange={(e) => {
                const next = [...terms];
                next[idx] = { ...t, amount: e.target.value };
                setTermsLocal(next);
              }}
            />
          )}
          <span data-testid={`term-preview-${idx}`}>{preview[idx] ?? "—"}</span>
        </div>
      ))}
      {canWrite ? (
        <button type="button" data-testid="save-terms" disabled={busy} onClick={() => void saveTerms()}>
          Salvar scadenze
        </button>
      ) : null}

      <h2>Payables</h2>
      {inv.status === "DRAFT" ? (
        <ul data-testid="payables-preview">
          {(inv.payables_preview?.length ? inv.payables_preview : preview.map((a, i) => ({ sequence: String(i + 1), amount: a, due_date: terms[i]?.due_date ?? "" }))).map(
            (p, i) => (
              <li key={i}>
                #{p.sequence} · {p.due_date} · {p.amount}
              </li>
            ),
          )}
        </ul>
      ) : (
        <ul data-testid="payables-list">
          {(inv.payables ?? []).map((p) => (
            <li key={p.id}>
              #{p.sequence} · {p.due_date} · {p.amount} · saldo {p.balance} · {p.status}
            </li>
          ))}
        </ul>
      )}

      {canIssue ? (
        <button
          type="button"
          data-testid="issue-invoice"
          disabled={busy || (inv.blockers?.length ?? 0) > 0}
          onClick={() => void onIssue()}
        >
          Emitir
        </button>
      ) : null}
      {(inv.blockers?.length ?? 0) > 0 && canIssue ? (
        <p className="muted" data-testid="issue-blocked-reason">
          Emitir bloqueado: {(inv.blockers ?? []).join("; ")}
        </p>
      ) : null}
    </section>
  );
}
