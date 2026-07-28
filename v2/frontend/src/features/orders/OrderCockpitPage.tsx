import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  KpiStrip,
  LoadingState,
  MoneyDisplay,
  PageHeader,
  StatusBadge,
} from "../../ui";
import { fetchOrderSummary, type OrderCockpit } from "../reporting/reportingApi";
import { OrderDetailPage } from "../orders/OrderDetailPage";

type Props = { user: User };

function canReadReporting(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("reporting:read");
}

export function OrderCockpitPage({ user }: Props) {
  const { orderId } = useParams();
  const id = Number(orderId);
  const [data, setData] = useState<OrderCockpit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCommercial, setShowCommercial] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    if (!canReadReporting(user)) {
      // fallback: commercial detail only
      setLoading(false);
      setShowCommercial(true);
      return;
    }
    setLoading(true);
    void fetchOrderSummary(id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [id, user]);

  if (!canReadReporting(user)) {
    return <OrderDetailPage user={user} />;
  }

  const commercial = (data?.commercial ?? {}) as Record<string, unknown>;
  const kpis = data?.kpis ?? {};

  return (
    <section className="panel dense" data-testid="order-cockpit">
      <ContextBreadcrumb
        items={[
          { label: "Ordens", to: "/orders" },
          { label: String(commercial.code ?? `#${id}`) },
        ]}
      />
      <PageHeader
        title={`Cockpit · ${String(commercial.code ?? id)}`}
        subtitle={String(commercial.supplier_name ?? "")}
        actions={
          <button type="button" className="btn" onClick={() => setShowCommercial((v) => !v)}>
            {showCommercial ? "Ocultar comercial" : "Comercial / edição"}
          </button>
        }
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {data ? (
        <>
          <div className="stack-row">
            <StatusBadge status={String(commercial.status ?? "")} />
            <span className="muted">Atualizado {String(commercial.updated_at ?? "—")}</span>
          </div>
          <KpiStrip
            items={[
              { label: "Pedido", value: String(kpis.ordered ?? "—") },
              { label: "Faturado", value: String(kpis.invoiced ?? "—") },
              { label: "Pago (alloc)", value: String(kpis.paid ?? "—"), hint: "Só via allocations" },
              { label: "Saldo", value: String(kpis.balance ?? "—") },
              { label: "Próx. venc.", value: String(kpis.next_due ?? "—") },
              { label: "FX exposição", value: String(kpis.fx_exposure ?? "—") },
              { label: "FX realizado", value: String(kpis.fx_realized ?? "—") },
            ]}
          />
          {data.alerts?.length ? (
            <ul className="alert-list" data-testid="cockpit-alerts">
              {data.alerts.map((a) => (
                <li key={a.code}>
                  {a.href ? <Link to={a.href}>{a.message}</Link> : a.message}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="Sem alertas" />
          )}

          <div className="cockpit-grid">
            <section>
              <h2>Financeiro</h2>
              <h3>Invoices</h3>
              <ul>
                {((data.billing.invoices as Array<Record<string, unknown>>) ?? []).map((inv) => (
                  <li key={String(inv.id)}>
                    <Link to={`/invoices/${inv.id}`}>
                      {String(inv.invoice_number)} · <StatusBadge status={String(inv.status)} />
                    </Link>
                  </li>
                ))}
              </ul>
              <h3>Payables</h3>
              <ul>
                {((data.billing.payables as Array<Record<string, unknown>>) ?? []).map((p) => (
                  <li key={String(p.id)}>
                    <Link to={`/payables?order_id=${id}`}>
                      #{String(p.id)} · {String(p.due_date)} ·{" "}
                      <MoneyDisplay amount={String(p.balance)} currency={String(p.currency)} />
                    </Link>
                    {" · "}
                    <Link to={`/payables/${p.id}/fx`}>FX</Link>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h2>Tesouraria</h2>
              <p>
                Pago via allocations:{" "}
                <MoneyDisplay amount={String((data.treasury as Record<string, unknown>).paid_via_allocations)} />
              </p>
              <h3>Payments</h3>
              <ul>
                {((data.treasury.payments as Array<Record<string, unknown>>) ?? []).map((p) => (
                  <li key={String(p.id)}>
                    <Link to={`/payments/${p.id}`}>
                      #{String(p.id)} · <MoneyDisplay amount={String(p.amount)} currency={String(p.currency)} /> ·
                      residual {String(p.amount_unallocated)}
                    </Link>
                  </li>
                ))}
              </ul>
              <h3>Candidatos unallocated</h3>
              <p className="muted">Não são relações com a ordem.</p>
              <ul>
                {((data.treasury.unallocated_candidates as Array<Record<string, unknown>>) ?? []).map((c) => (
                  <li key={String(c.payment_id)}>
                    Payment #{String(c.payment_id)} · residual {String(c.amount_unallocated)}
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h2>Documentos / Audit</h2>
              <h3>Documentos (resumo)</h3>
              <ul>
                {(((data.documents as Record<string, unknown>).items as Array<Record<string, unknown>>) ?? []).map(
                  (d) => (
                    <li key={String(d.id)}>
                      #{String(d.id)} · {String(d.filename)}
                    </li>
                  ),
                )}
              </ul>
              <h3>Audit (últimos)</h3>
              <ul>
                {(((data.audit as Record<string, unknown>).items as Array<Record<string, unknown>>) ?? []).map((a) => (
                  <li key={String(a.id)}>
                    {String(a.action)} · {String(a.created_at)}
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      ) : null}
      {showCommercial ? (
        <div className="commercial-embed" data-testid="commercial-embed">
          <OrderDetailPage user={user} />
        </div>
      ) : null}
    </section>
  );
}
