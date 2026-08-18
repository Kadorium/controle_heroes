import { Link, useLocation, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  AuditDocumentsBlock,
  ContextBreadcrumb,
  ErrorState,
  KpiStrip,
  LoadingState,
  MoneyDisplay,
  Notice,
  OperationalTable,
  PageHeader,
  RowLink,
  SectionCard,
  StatusBadge,
  SummaryGrid,
  cockpitAlertLabel,
  formatDateOnly,
  formatDateTime,
  formatMoney,
  paymentAllocationStateLabel,
} from "../../ui";
import { fetchOrderSummary, type OrderCockpit } from "../reporting/reportingApi";
import { buildReturnTo } from "../../navigation/returnState";

type Props = { user: User };

function canReadReporting(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("reporting:read");
}

function canWriteOrders(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("orders:write");
}

function kpiValue(
  value: string | null | undefined,
  currency?: string | null,
  opts?: { date?: boolean },
) {
  if (value === null || value === undefined || value === "") return "—";
  if (opts?.date) return formatDateOnly(value);
  if (currency) return formatMoney(value, currency);
  return formatMoney(value);
}

export function OrderCockpitPage({ user }: Props) {
  const { orderId } = useParams();
  const location = useLocation();
  const id = Number(orderId);
  const [data, setData] = useState<OrderCockpit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    if (!canReadReporting(user)) {
      setLoading(false);
      setError("Sem permissão reporting para o cockpit");
      return;
    }
    setLoading(true);
    void fetchOrderSummary(id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [id, user]);

  const commercial = (data?.commercial ?? {}) as Record<string, unknown>;
  const currency = String(commercial.currency ?? "EUR");
  const kpis = data?.kpis ?? {};
  const fromState = (location.state as { returnTo?: string } | null)?.returnTo;
  const ordersReturn =
    typeof fromState === "string" && fromState.startsWith("/orders")
      ? fromState
      : buildReturnTo("/orders");

  const invoices = ((data?.billing.invoices as Array<Record<string, unknown>>) ?? []);
  const payables = ((data?.billing.payables as Array<Record<string, unknown>>) ?? []);
  const payments = ((data?.treasury.payments as Array<Record<string, unknown>>) ?? []);
  const candidates = ((data?.treasury.unallocated_candidates as Array<Record<string, unknown>>) ?? []);
  const documents = ((((data?.documents as Record<string, unknown>)?.items as Array<Record<string, unknown>>) ?? [])).map(
    (d) => ({
      id: d.id as string | number | undefined,
      name: String(d.filename ?? ""),
      uploadedAt: d.created_at ? String(d.created_at) : null,
    }),
  );
  const audit = ((((data?.audit as Record<string, unknown>)?.items as Array<Record<string, unknown>>) ?? [])).map(
    (a) => ({
      id: a.id as string | number | undefined,
      action: String(a.action ?? ""),
      at: a.created_at ? String(a.created_at) : null,
      actor: a.actor_label ? String(a.actor_label) : null,
    }),
  );

  const orderTitle =
    typeof commercial.code === "string" && commercial.code.trim()
      ? String(commercial.code)
      : "Pedido";

  return (
    <section className="panel dense page-detail detail-shell" data-testid="order-cockpit">
      <ContextBreadcrumb
        items={[
          { label: "Compras", to: ordersReturn },
          { label: "Pedidos", to: ordersReturn },
          { label: orderTitle },
        ]}
      />
      <PageHeader
        title={orderTitle}
        subtitle={[
          commercial.supplier_name ? String(commercial.supplier_name) : null,
          currency,
          "Somente leitura",
        ]
          .filter(Boolean)
          .join(" · ")}
        actions={
          <div className="stack-row page-header-actions">
            <Link
              className="ui-button ui-button--secondary"
              to={`/orders/${id}/commercial#order-advances`}
              data-testid="cockpit-advances-link"
            >
              Adiantamentos
            </Link>
            {canWriteOrders(user) ? (
              <Link
                className="ui-button"
                to={`/orders/${id}/commercial`}
                data-testid="cockpit-commercial-link"
              >
                Abrir comercial
              </Link>
            ) : null}
          </div>
        }
      />
      {loading ? <LoadingState message="Carregando cockpit…" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {data ? (
        <>
          <div className="stack-row">
            <StatusBadge status={String(commercial.status ?? "")} entity="order" />
            <span className="muted">Atualizado {formatDateTime(String(commercial.updated_at ?? ""))}</span>
          </div>
          <KpiStrip
            items={[
              { label: "Pedido", value: kpiValue(kpis.ordered, currency) },
              { label: "Faturado", value: kpiValue(kpis.invoiced, currency) },
              {
                label: "Pago (alocado)",
                value: kpiValue(kpis.paid, currency),
                hint: "Via alocações em obrigações",
              },
              {
                label: "Adiantado (crédito)",
                value: kpiValue(kpis.advanced_credit, currency),
                hint: "Saiu do caixa; ainda não quitou obrigação",
              },
              { label: "Saldo", value: kpiValue(kpis.balance, currency), hint: "Saldo aberto em obrigações" },
              { label: "Próx. venc.", value: kpiValue(kpis.next_due, undefined, { date: true }) },
              {
                label: "Exposição FX",
                value: kpiValue(kpis.fx_exposure, currency),
                hint: "Saldo aberto nas obrigações, na moeda do pedido",
              },
              {
                label: "Custo BRL",
                value: kpiValue(kpis.cost_brl, "BRL"),
                hint: "Soma dos câmbios deste pedido. Não é média × EUR.",
              },
            ]}
          />
          <SectionCard title="Cronograma de pagamento" data-testid="cockpit-schedule">
            <p className="muted">
              Planejamento comercial. Não entra em Pago, Adiantado nem Exposição FX.
            </p>
            {!(data.schedule?.lines?.length) ? (
              <p className="muted" data-testid="cockpit-schedule-empty">
                Sem cronograma cadastrado.
              </p>
            ) : (
              <>
                {data.schedule.coherence === "unverifiable" ? (
                  <Notice tone="info" data-testid="cockpit-schedule-coherence">
                    Coerência não verificável — total comercial incompleto. Ausência não é zero.
                  </Notice>
                ) : null}
                {data.schedule.coherence === "divergent" ? (
                  <Notice tone="warning" data-testid="cockpit-schedule-coherence">
                    Divergente do total comercial (delta{" "}
                    {kpiValue(data.schedule.delta, data.schedule.currency ?? currency)}).
                  </Notice>
                ) : null}
                {data.schedule.coherence === "aligned" ? (
                  <Notice tone="info" data-testid="cockpit-schedule-coherence">
                    Alinhado ao total comercial.
                  </Notice>
                ) : null}
                <OperationalTable density="standard">
                  <thead>
                    <tr>
                      <th>Quando</th>
                      <th className="num">
                        {data.schedule.mode === "AMOUNT" ? "Valor" : "%"}
                      </th>
                      <th className="num">Derivado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.schedule.lines ?? []).map((ln, idx) => (
                      <tr key={String(ln.sequence ?? idx)}>
                        <td>
                          {[ln.due_date ? formatDateOnly(ln.due_date) : null, ln.condition_text]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </td>
                        <td className="num">
                          {data.schedule?.mode === "AMOUNT"
                            ? kpiValue(ln.amount, data.schedule.currency ?? currency)
                            : ln.percent
                              ? `${ln.percent}%`
                              : "—"}
                        </td>
                        <td className="num">
                          {kpiValue(ln.derived_amount, data.schedule?.currency ?? currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </OperationalTable>
              </>
            )}
          </SectionCard>
          {data.alerts?.length ? (
            <Notice tone="warning" title="Pendências" data-testid="cockpit-alerts">
              <div className="stack">
                {data.alerts.map((a) => {
                  const label = cockpitAlertLabel(a.code, a.message);
                  return (
                    <div key={a.code}>
                      {a.href ? <RowLink to={a.href}>{label}</RowLink> : label}
                    </div>
                  );
                })}
              </div>
            </Notice>
          ) : null}

          <div className="cockpit-grid">
            <SectionCard title="Faturamento">
              <h3 className="section-subtitle">Faturas</h3>
              {invoices.length === 0 ? (
                <p className="muted">Nenhuma fatura</p>
              ) : (
                <OperationalTable density="standard" data-testid="cockpit-invoices">
                  <thead>
                    <tr>
                      <th>Número</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={String(inv.id)}>
                        <td>
                          <RowLink to={`/invoices/${inv.id}`}>{String(inv.invoice_number)}</RowLink>
                        </td>
                        <td>
                          <StatusBadge status={String(inv.status)} entity="invoice" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </OperationalTable>
              )}
              <h3 className="section-subtitle">Obrigações</h3>
              {payables.length === 0 ? (
                <p className="muted">Nenhuma obrigação</p>
              ) : (
                <OperationalTable density="standard" data-testid="cockpit-payables">
                  <thead>
                    <tr>
                      <th>Vencimento</th>
                      <th className="num">Saldo</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {payables.map((p) => (
                      <tr key={String(p.id)}>
                        <td>
                          <RowLink to={`/payables?order_id=${id}`}>
                            {formatDateOnly(String(p.due_date))}
                          </RowLink>
                        </td>
                        <td className="num">
                          <MoneyDisplay amount={String(p.balance)} currency={String(p.currency)} />
                        </td>
                        <td>
                          <RowLink to={`/payables/${p.id}/fx`}>Câmbio</RowLink>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </OperationalTable>
              )}
            </SectionCard>

            <SectionCard title="Tesouraria">
              <SummaryGrid
                items={[
                  {
                    label: "Pago via alocações",
                    value: (
                      <MoneyDisplay
                        amount={String((data.treasury as Record<string, unknown>).paid_via_allocations)}
                        currency={currency}
                      />
                    ),
                  },
                  {
                    label: "Adiantado (crédito)",
                    value: (
                      <MoneyDisplay
                        amount={String(
                          (data.treasury as Record<string, unknown>).advanced_credit ?? "0.00",
                        )}
                        currency={currency}
                      />
                    ),
                  },
                  {
                    label: "Custo BRL (soma dos câmbios)",
                    value: (
                      <MoneyDisplay
                        amount={String((data.treasury as Record<string, unknown>).cost_brl ?? "0.00")}
                        currency="BRL"
                      />
                    ),
                  },
                  {
                    label: "Câmbio médio ponderado",
                    value: String(
                      (data.treasury as Record<string, unknown>).cost_weighted_avg_rate ?? "—",
                    ),
                  },
                ]}
              />
              <h3 className="section-subtitle">Pagamentos realizados deste pedido</h3>
              {payments.length === 0 ? (
                <p className="muted">Nenhum pagamento realizado</p>
              ) : (
                <OperationalTable density="standard" data-testid="cockpit-payments">
                  <thead>
                    <tr>
                      <th className="num">Valor</th>
                      <th>Registro</th>
                      <th>Estado</th>
                      <th className="num">Aberto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((p) => {
                      const cancelled = String(p.status) === "CANCELLED";
                      const residual = p.amount_unallocated;
                      const state = paymentAllocationStateLabel({
                        status: String(p.status),
                        amount_allocated: p.amount_allocated as string | undefined,
                        amount_unallocated: residual as string | undefined,
                      });
                      return (
                        <tr key={String(p.id)} data-payment-status={String(p.status)}>
                          <td className="num">
                            <RowLink to={`/payments/${p.id}`}>
                              <MoneyDisplay amount={String(p.amount)} currency={String(p.currency)} />
                            </RowLink>
                          </td>
                          <td>
                            <StatusBadge status={String(p.status)} entity="payment" />
                          </td>
                          <td>
                            <span data-testid={`cockpit-payment-state-${p.id}`}>{state}</span>
                          </td>
                          <td className="num">
                            {cancelled || residual == null || residual === "" ? (
                              <span className="muted" data-testid="cockpit-payment-residual-na">
                                —
                              </span>
                            ) : (
                              <MoneyDisplay amount={String(residual)} currency={String(p.currency)} />
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </OperationalTable>
              )}
              <h3 className="section-subtitle">Candidatos a alocação (fornecedor)</h3>
              <Notice tone="info" data-testid="cockpit-candidates-notice">
                Mesmo fornecedor e moeda — podem ser de outros pedidos. Não substituem a lista
                de pagamentos deste pedido.
              </Notice>
              {candidates.length === 0 ? (
                <p className="muted">Nenhum candidato</p>
              ) : (
                <OperationalTable density="standard" data-testid="cockpit-candidates">
                  <thead>
                    <tr>
                      <th className="num">Residual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c) => (
                      <tr key={String(c.payment_id)}>
                        <td className="num">
                          <RowLink to={`/payments/${c.payment_id}`}>
                            <MoneyDisplay
                              amount={String(c.amount_unallocated)}
                              currency={String(c.currency ?? currency)}
                            />
                          </RowLink>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </OperationalTable>
              )}
            </SectionCard>

            <AuditDocumentsBlock documents={documents} audit={audit} />
          </div>
        </>
      ) : null}
    </section>
  );
}
