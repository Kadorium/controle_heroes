import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, EmptyState, LoadingState, PageHeader, Table, useToast } from "../components";
import { FxPnlPanel } from "../components/FxPnlPanel";
import {
  financeApi,
  invoicesApi,
  type PayablesOrderBlock,
  type PayablesQueueResponse,
} from "../api";
import { emptyDash, formatAmount, formatMoney } from "../i18n/glossario";
import { fmtDate } from "../utils/formatDate";

type PayFilter = "all" | "overdue" | "due7" | "planned" | "settled";

const FILTERS: { id: PayFilter; label: string }[] = [
  { id: "all", label: "Todas" },
  { id: "overdue", label: "Vencidas" },
  { id: "due7", label: "Vencendo 7d" },
  { id: "planned", label: "Planejadas" },
  { id: "settled", label: "Liquidadas" },
];

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="payables-kpi">
      <div className="payables-kpi__label">{label}</div>
      <div className="payables-kpi__value">{value}</div>
      {hint && <div className="payables-kpi__hint">{hint}</div>}
    </div>
  );
}

function RateEditCell({
  invoiceId,
  value,
  onSaved,
}: {
  invoiceId: number;
  value: string | null;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [rate, setRate] = useState(value ?? "");
  const [reason, setReason] = useState("");

  async function save() {
    if (!reason.trim()) {
      toast.error("Informe o motivo da alteração de câmbio previsto.");
      return;
    }
    try {
      await invoicesApi.update(invoiceId, {
        expected_exchange_rate: rate.trim() || null,
        rate_change_reason: reason.trim(),
      });
      toast.success("Câmbio previsto atualizado");
      setEditing(false);
      setReason("");
      onSaved();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Não foi possível salvar.");
    }
  }

  if (!editing) {
    return (
      <button type="button" className="link-btn" onClick={() => { setRate(value ?? ""); setEditing(true); }}>
        {value ? formatAmount(value) : emptyDash(null)}
      </button>
    );
  }

  return (
    <div className="payables-rate-edit">
      <input type="text" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="Taxa" aria-label="Câmbio previsto" />
      <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Motivo" aria-label="Motivo da alteração" />
      <Button variant="secondary" className="ui-btn--sm" onClick={() => void save()}>Salvar</Button>
      <Button variant="ghost" className="ui-btn--sm" onClick={() => setEditing(false)}>Cancelar</Button>
    </div>
  );
}

function OrderBlock({
  order,
  expanded,
  onToggle,
  onReload,
}: {
  order: PayablesOrderBlock;
  expanded: boolean;
  onToggle: () => void;
  onReload: () => void;
}) {
  const navigate = useNavigate();
  const ops = order.finance_operational;

  return (
    <div className="payables-order">
      <button type="button" className="payables-order__head" onClick={onToggle} aria-expanded={expanded}>
        <span className="payables-order__chev">{expanded ? "▼" : "▶"}</span>
        <span className="payables-order__po">{order.po_number}</span>
        <span className="payables-order__sup">{order.supplier_name}</span>
        <span className="payables-order__meta">
          Provisão: {order.opening_exchange_rate ? formatAmount(order.opening_exchange_rate) : "—"}
        </span>
        <span className="payables-order__meta">
          Liquidado BRL: {ops?.settled_brl ? formatMoney(String(ops.settled_brl), "BRL") : "—"}
          {ops?.brl_is_estimated ? " (est.)" : ""}
        </span>
        {order.open_fx_exposure_brl && (
          <span className="payables-order__meta payables-order__meta--warn">
            Exposição: {formatMoney(order.open_fx_exposure_brl, "BRL")}
          </span>
        )}
        <Button
          variant="ghost"
          className="ui-btn--sm"
          onClick={(e) => { e.stopPropagation(); navigate(`/importacoes/${order.importation_id}/financeiro`); }}
        >
          Abrir ordem
        </Button>
      </button>

      {expanded && (
        <div className="payables-order__body order-queue__scroll">
          <Table>
            <thead>
              <tr>
                <th>Fatura</th>
                <th>Tipo</th>
                <th className="num">Valor EUR</th>
                <th className="num">Câmbio previsto</th>
                <th className="num">Saldo EUR</th>
                <th>Vencimento</th>
                <th className="num">Valor EUR (pag.)</th>
                <th className="num">Câmbio efetivo</th>
                <th className="num">Valor BRL</th>
                <th>Status</th>
                <th>Comprovante</th>
              </tr>
            </thead>
            <tbody>
              {order.invoices.map((inv) =>
                inv.payments.length === 0 ? (
                  <tr key={`inv-${inv.id}`}>
                    <td>
                      <button type="button" className="link-btn" onClick={() => navigate(`/importacoes/${order.importation_id}/invoices#fatura-${inv.id}`)}>
                        {inv.invoice_number ?? "—"}
                      </button>
                    </td>
                    <td>{inv.invoice_type ?? "—"}</td>
                    <td className="num">{inv.amount_eur ? formatMoney(inv.amount_eur, "EUR") : emptyDash(null)}</td>
                    <td className="num"><RateEditCell invoiceId={inv.id} value={inv.expected_exchange_rate} onSaved={onReload} /></td>
                    <td className="num">{inv.balance ? formatMoney(inv.balance, "EUR") : emptyDash(null)}</td>
                    <td colSpan={6} className="meta">Sem pagamentos</td>
                  </tr>
                ) : (
                  inv.payments.map((p, pi) => (
                    <tr key={p.id} className={pi > 0 ? "payables-pay-subrow" : undefined}>
                      {pi === 0 && (
                        <>
                          <td rowSpan={inv.payments.length}>
                            <button type="button" className="link-btn" onClick={() => navigate(`/importacoes/${order.importation_id}/invoices#fatura-${inv.id}`)}>
                              {inv.invoice_number ?? "—"}
                            </button>
                          </td>
                          <td rowSpan={inv.payments.length}>{inv.invoice_type ?? "—"}</td>
                          <td className="num" rowSpan={inv.payments.length}>
                            {inv.amount_eur ? formatMoney(inv.amount_eur, "EUR") : emptyDash(null)}
                          </td>
                          <td className="num" rowSpan={inv.payments.length}>
                            <RateEditCell invoiceId={inv.id} value={inv.expected_exchange_rate} onSaved={onReload} />
                          </td>
                          <td className="num" rowSpan={inv.payments.length}>
                            {inv.balance ? formatMoney(inv.balance, "EUR") : emptyDash(null)}
                          </td>
                        </>
                      )}
                      <td>{p.due_date ? fmtDate(p.due_date) : emptyDash(p.payment_date ? fmtDate(p.payment_date) : null)}</td>
                      <td className="num">{p.amount_foreign ? formatMoney(p.amount_foreign, p.currency_foreign ?? "EUR") : emptyDash(null)}</td>
                      <td className="num">{p.exchange_rate ? formatAmount(p.exchange_rate) : emptyDash(null)}</td>
                      <td className="num">
                        {p.display_brl ? (
                          <>
                            {formatMoney(p.display_brl, "BRL")}
                            {p.brl_is_estimated && <span className="payables-est-badge"> est.</span>}
                          </>
                        ) : emptyDash(null)}
                      </td>
                      <td><Badge status={p.is_settled ? "FULL_PAID" : "PENDING"}>{p.status_label}</Badge></td>
                      <td>{p.receipt_reference ?? emptyDash(null)}</td>
                    </tr>
                  ))
                ),
              )}
            </tbody>
          </Table>
        </div>
      )}
    </div>
  );
}

export function FinancePage() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const [data, setData] = useState<PayablesQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<PayFilter>("all");
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const load = useCallback(async (status?: PayFilter) => {
    setLoadError(null);
    const effective = status ?? filter;
    const statusParam = effective === "all" ? undefined : effective;
    try {
      const res = await financeApi.payablesQueue({ status: statusParam });
      setData(res);
      setExpanded((prev) => {
        const next = { ...prev };
        for (const o of res.orders) {
          if (next[o.importation_id] === undefined) next[o.importation_id] = true;
        }
        return next;
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Não foi possível carregar a fila financeira.";
      setLoadError(msg);
      setData(null);
      toastRef.current.error(msg);
    }
  }, [filter]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        await load();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [load]);

  const onFilterChange = (next: PayFilter) => {
    setFilter(next);
    setLoading(true);
    void (async () => {
      try {
        await load(next);
      } finally {
        setLoading(false);
      }
    })();
  };

  const kpis = data?.kpis;
  const pnl = data?.fx_pnl_summary;

  const dashboardPnl = useMemo(() => {
    if (!pnl) return null;
    if (pnl.pnl_realized_brl != null) return pnl;
    if (pnl.open_fx_exposure_brl != null) {
      return { ...pnl, pnl_realized_brl: null, pnl_total_brl: pnl.pnl_total_brl ?? null };
    }
    return pnl;
  }, [pnl]);

  if (loading) {
    return (
      <div>
        <PageHeader title="Financeiro Global" subtitle="Dashboard financeiro e fila de contas a pagar por ordem." />
        <LoadingState label="Carregando financeiro global..." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Financeiro Global" subtitle="Dashboard financeiro e fila operacional de contas a pagar agrupada por ordem." />

      {loadError && (
        <p className="error payables-load-error" role="alert">
          {loadError}
        </p>
      )}

      <section className="payables-dashboard" aria-label="Dashboard financeiro">
        <div className="payables-kpi-row">
          <KpiCard label="Total pago (BRL)" value={kpis?.total_settled_brl ? formatMoney(kpis.total_settled_brl, "BRL") : "—"} hint="Inclui BRL estimado quando acconto EUR" />
          <KpiCard label="Pendente (BRL)" value={kpis?.total_pending_brl ? formatMoney(kpis.total_pending_brl, "BRL") : "—"} />
          <KpiCard label="Vencendo 7d" value={kpis ? String(kpis.due_7d_count) : "—"} hint={kpis?.due_7d_brl ? formatMoney(kpis.due_7d_brl, "BRL") : undefined} />
          <KpiCard
            label="Exposição cambial aberta"
            value={kpis?.open_fx_exposure_brl ? formatMoney(kpis.open_fx_exposure_brl, "BRL") : "—"}
            hint="Acconti EUR sem liquidação BRL efetiva"
          />
          <KpiCard
            label="Ordens com provisão"
            value={kpis ? String(kpis.orders_with_provision) : "—"}
          />
        </div>

        {dashboardPnl && (dashboardPnl.pnl_total_brl != null || dashboardPnl.open_fx_exposure_brl != null || dashboardPnl.provision_rate != null) ? (
          <div className="fx-pnl-kpi">
            <div className="fx-pnl-kpi__title">
              PnL Cambial consolidado
              {pnl?.orders_with_pnl != null ? ` · ${pnl.orders_with_pnl} ordem(ns)` : ""}
            </div>
            <FxPnlPanel pnl={dashboardPnl} />
            {pnl?.pnl_realized_brl == null && pnl?.open_fx_exposure_brl != null && (
              <p className="meta payables-pnl-note">
                Sem pagamentos BRL efetivos — exposição cambial aberta: {formatMoney(pnl.open_fx_exposure_brl, "BRL")}
              </p>
            )}
          </div>
        ) : (
          <p className="meta payables-pnl-note">Defina câmbio de provisão nas ordens para habilitar PnL e BRL estimado.</p>
        )}
      </section>

      <section className="payables-section" aria-label="Contas a pagar">
        <h2 className="payables-section__title">Contas a pagar</h2>
        <div className="order-queue__filters">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={`order-queue__filter${filter === f.id ? " order-queue__filter--on" : ""}`}
              onClick={() => onFilterChange(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {!data?.orders.length ? (
          <EmptyState title="Nenhuma ordem com pagamentos" />
        ) : (
          <div className="payables-orders">
            {data.orders.map((order) => (
              <OrderBlock
                key={order.importation_id}
                order={order}
                expanded={!!expanded[order.importation_id]}
                onToggle={() => setExpanded((e) => ({ ...e, [order.importation_id]: !e[order.importation_id] }))}
                onReload={() => void load()}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
