import { useLocation, useParams } from "react-router-dom";
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
  RowLink,
  SectionCard,
  StatusBadge,
  SummaryGrid,
  cockpitAlertLabel,
  formatDateOnly,
  formatMoney,
  paymentAllocationStateLabel,
} from "../../ui";
import { fetchOrderSummary, type OrderCockpit } from "../reporting/reportingApi";
import { withContextReturn } from "../../navigation/contextReturn";
import { buildReturnTo } from "../../navigation/returnState";
import { RecordWorkHeader, focusRecordSection, type RecordAction, type RecordTopic } from "../../ui/RecordWorkHeader";
import { canNavigate } from "../../app-shell/navigation";
import { useRead } from "../inventory/stockRead";
import type { OrderQtyRow } from "../billing/billingApi";
import type { ApQueueResponse } from "../reporting/reportingApi";
import { accountsWorkState, billingWorkState } from "./orderWorkState";

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
  const [loadedData, setData] = useState<OrderCockpit | null>(null);
  const data=loadedData?.order_id===id?loadedData:null;
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const billingAllowed=canNavigate(user,"billing:read"), treasuryAllowed=canNavigate(user,"treasury:read");
  const qtys=useRead<OrderQtyRow[]>(billingAllowed?`/api/orders/${id}/invoiced-quantities`:null);
  const accounts=useRead<ApQueueResponse>(billingAllowed && canReadReporting(user)?`/api/reporting/ap-queue?order_id=${id}&pending=ALL&limit=1`:null);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    if (!canReadReporting(user)) {
      setLoading(false);
      setError("Sem permissão reporting para o cockpit");
      return;
    }
    let cancelled=false;setLoading(true);setError(null);
    void fetchOrderSummary(id)
      .then(value=>{if(!cancelled)setData(value);})
      .catch((e) => {if(!cancelled)setError(e instanceof Error ? e.message : "Erro");})
      .finally(() => {if(!cancelled)setLoading(false);});
    return()=>{cancelled=true;};
  }, [id, user]);

  useEffect(()=>{if(!data||!location.hash)return;const timer=window.setTimeout(()=>focusRecordSection(location.hash),80);return()=>window.clearTimeout(timer);},[data?.order_id,location.hash]);

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

  const billing=qtys.data?billingWorkState(qtys.data,String(commercial.status)):null;
  const accountState=accounts.data?accountsWorkState(accounts.data):null;
  const topics:RecordTopic[]=[];
  if(data){
    if(canNavigate(user,"orders:read"))topics.push({id:"items",label:"Itens",state:"Consultar itens",result:`${commercial.items_count ?? "Não informado"} linhas no pedido`,tone:"info",href:`/orders/${id}/commercial#order-items`});
    if(billingAllowed)topics.push({id:"billing",label:"Faturamento",state:qtys.busy?"Carregando":qtys.error?"Erro na consulta":billing?.state||"Sem informação",result:qtys.error||billing?.result||"Consultando quantidades por item",tone:qtys.busy?"loading":qtys.error?"error":billing?.tone||"empty",href:"#cockpit-billing"});
    if(billingAllowed)topics.push({id:"accounts",label:"Contas e pagamentos",state:accounts.busy?"Carregando":accounts.error?"Erro na consulta":accountState?.state||"Sem informação",result:accounts.error||accountState?.result||"Consultar contas do pedido",tone:accounts.busy?"loading":accounts.error?"error":accountState?.tone||"empty",href:"#cockpit-accounts"});
    if(treasuryAllowed)topics.push({id:"credit",label:"Crédito",state:kpis.advanced_credit==null?"Sem informação":Number(kpis.advanced_credit)>0?"Crédito disponível":"Sem crédito no resumo",result:kpiValue(kpis.advanced_credit,currency),tone:kpis.advanced_credit==null?"empty":"info",href:"#cockpit-treasury"});
  }
  const primary:RecordAction|undefined=accountState?.overdue?{label:"Ver contas vencidas",href:`/payables?order_id=${id}&pending=OVERDUE`}:String(commercial.status)==="DRAFT" && canWriteOrders(user)?{label:"Revisar pedido",href:`/orders/${id}/commercial`}:billing?.eligible && canNavigate(user,"billing:write")?{label:"Faturar itens",href:`/orders/${id}/commercial#order-invoices`}:undefined;
  const more:RecordAction[]=[
    ...(treasuryAllowed?[{label:"Adiantamentos",href:`/orders/${id}/commercial#order-advances`,testId:"cockpit-advances-link"}]:[]),
    ...(billingAllowed?[{label:"Ver contas do pedido",href:`/payables?order_id=${id}&pending=ALL`}]:[]),
    ...(canWriteOrders(user) && String(commercial.status)==="CONFIRMED"?[{label:"Encerrar pedido…",href:`/orders/${id}/commercial`,testId:"cockpit-close-link"}]:[]),
    ...(canWriteOrders(user) && String(commercial.status)==="CLOSED"?[{label:"Reabrir pedido…",href:`/orders/${id}/commercial`,testId:"cockpit-reopen-link"}]:[]),
  ];

  return (
    <section className="panel dense page-detail detail-shell record-detail-page" data-testid="order-cockpit">
      <ContextBreadcrumb
        items={[
          { label: "Compras", to: ordersReturn },
          { label: "Pedidos", to: ordersReturn },
          { label: orderTitle },
        ]}
      />
      <RecordWorkHeader title={orderTitle} context={[commercial.supplier_name?String(commercial.supplier_name):null,currency].filter(Boolean).join(" · ")} status={data?<StatusBadge status={String(commercial.status)} entity="order"/>:null} primary={primary} secondary={canNavigate(user,"orders:read")?{label:canWriteOrders(user)?"Abrir comercial":"Consultar pedido",href:`/orders/${id}/commercial`,testId:"cockpit-commercial-link"}:undefined} more={more} topics={topics}/>
      {loading ? <LoadingState message="Carregando cockpit…" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {data ? (
        <>
          {Number(kpis.balance) > 0 &&
          (String(commercial.status) === "CONFIRMED" || String(commercial.status) === "CLOSED") ? (
            <Notice tone="warning" data-testid="close-open-ap-notice">
              {String(commercial.status) === "CLOSED"
                ? `Pedido encerrado com ${kpiValue(kpis.balance, currency)} em contas a pagar em aberto. Encerrar o comercial não quita essas obrigações.`
                : `Há ${kpiValue(kpis.balance, currency)} em contas a pagar em aberto. Encerrar o pedido comercial não quita essas obrigações.`}
            </Notice>
          ) : null}
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
                    <div key={a.code} data-testid={`cockpit-alert-${a.code}`}>
                      {a.href ? <RowLink to={a.href}>{label}</RowLink> : label}
                    </div>
                  );
                })}
              </div>
            </Notice>
          ) : null}

          <div className="cockpit-grid">
            {billingAllowed && <SectionCard id="cockpit-billing" title="Faturamento">
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
                          <RowLink to={withContextReturn(`/invoices/${inv.id}`,`/orders/${id}#cockpit-billing`)}>{String(inv.invoice_number)}</RowLink>
                        </td>
                        <td>
                          <StatusBadge status={String(inv.status)} entity="invoice" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </OperationalTable>
              )}
              <h3 id="cockpit-accounts" className="section-subtitle">Obrigações</h3>
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
            </SectionCard>}

            {treasuryAllowed && <SectionCard id="cockpit-treasury" title="Tesouraria">
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
            </SectionCard>}

            <AuditDocumentsBlock documents={documents} audit={audit} />
          </div>
        </>
      ) : null}
    </section>
  );
}
