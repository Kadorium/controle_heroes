import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  closureApi,
  documentsApi,
  financeApi,
  invoicesApi,
  type DocumentAttachment,
  type Payment,
  type TimelineEvent,
} from "../../api";
import { Badge, Button, EditableCell, LoadingState, useToast } from "../../components";
import { InvoiceAmountField } from "../../components/InvoiceAmountField";
import {
  emptyDash,
  formatMoney,
  invoiceTypeLabel,
  payStatusLabel,
  productModelLabel,
} from "../../i18n/glossario";
import { fmtDate, fmtDateTime, isPlannedPayment } from "../../utils/formatDate";
import { formatTimelineEvent } from "../../utils/timelineFormat";
import { ItalyOverrideModal, type ItalyOverrideTarget } from "./ItalyOverrideModal";
import { LockedCell } from "./orderCentralItemsShared";
import { computeOpSummary } from "./orderCentralItemsUtils";
import { useOrderCentral } from "./OrderCentralContext";
import { useFxRate } from "../../context/FxRateContext";
import {
  canSubmitInvoiceAmount,
  nextInvoiceSuffix,
  orderRemainingToInvoice,
  resolveInvoiceAmount,
  suggestInvoiceNumber,
  type InvoiceAmountMode,
} from "./novaOrdemInvoice";

/** Papel típico da fatura na ordem (antecipo → chegada → saldo 30/60d). */
function invoiceStageHint(type: string | null | undefined, seq: number): string {
  const t = (type ?? "").toUpperCase();
  if (t === "ANTECIPO") return "Antecipo / acconto";
  if (t === "SALDO") return "Saldo (na chegada)";
  if (t === "COMPLEMENTAR") return "Complementar (30/60 dias)";
  if (t === "PROFORMA") return "Proforma";
  if (t === "CREDITO") return "Crédito";
  if (t === "AJUSTE") return "Ajuste";
  return `${seq}ª fatura`;
}

interface Props {
  importationId: number;
}

export function OrderCentralOverview({ importationId }: Props) {
  const navigate = useNavigate();
  const toast = useToast();
  const { data, loading, error: centralError, reloadCentral } = useOrderCentral();
  const [overrideTarget, setOverrideTarget] = useState<ItalyOverrideTarget | null>(null);
  const [docs, setDocs] = useState<DocumentAttachment[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [addingInvoice, setAddingInvoice] = useState(false);
  const [invNumber, setInvNumber] = useState("");
  const [invNumberTouched, setInvNumberTouched] = useState(false);
  const [invType, setInvType] = useState("ANTECIPO");
  const [invAmount, setInvAmount] = useState("");
  const [invAmountMode, setInvAmountMode] = useState<InvoiceAmountMode>("EUR");
  const [invDue, setInvDue] = useState("");
  const [submittingInvoice, setSubmittingInvoice] = useState(false);
  const { reference: fxReference } = useFxRate();
  const [error, setError] = useState("");

  function reloadDocs() {
    documentsApi.list("importation_order", String(importationId)).then(setDocs).catch(() => undefined);
  }

  useEffect(() => {
    reloadDocs();
    closureApi.timeline(importationId).then((t) => setTimeline(t.slice(0, 8))).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importationId]);

  const blockARows = useMemo(() => {
    if (!data) return [];
    const rows: Array<{
      key: string; date: string | null; invoiceNumber: string; qty: number | null;
      qtyItemId: number | null; invoiceId: number; model: string; acconto: string;
      accontoRimasto: string; status: string; isFirst: boolean; isAntecipo: boolean;
      invoiceType: string; seq: number;
    }> = [];
    data.invoices.forEach((inv, invIdx) => {
      const isAntecipo = inv.invoice_type === "ANTECIPO";
      const acconto = inv.paid_total ? formatMoney(inv.paid_total, inv.currency) : emptyDash(null);
      const rimasto = inv.balance != null ? formatMoney(inv.balance, inv.currency) : emptyDash(null);
      const status = payStatusLabel(Number(inv.balance ?? 0) === 0 ? "PAID" : "PENDING");
      const seq = invIdx + 1;
      if (inv.items.length === 0) {
        rows.push({ key: `${inv.id}-0`, date: inv.invoice_date, invoiceNumber: inv.invoice_number, qty: null, qtyItemId: null, invoiceId: inv.id, model: emptyDash(null), acconto, accontoRimasto: rimasto, status, isFirst: true, isAntecipo, invoiceType: inv.invoice_type, seq });
        return;
      }
      inv.items.forEach((ii, idx) => {
        rows.push({ key: `${inv.id}-${ii.id}`, date: idx === 0 ? (inv.invoice_date ?? inv.payment_due_date) : null, invoiceNumber: idx === 0 ? inv.invoice_number : "", qty: ii.quantity, qtyItemId: ii.id, invoiceId: inv.id, model: ii.description ?? ii.product_sku ?? emptyDash(null), acconto: idx === 0 ? acconto : "", accontoRimasto: idx === 0 ? rimasto : "", status: idx === 0 ? status : "", isFirst: idx === 0, isAntecipo, invoiceType: inv.invoice_type, seq });
      });
    });
    return rows;
  }, [data]);

  const invoiceStages = useMemo(() => {
    if (!data) return [];
    const sorted = [...data.invoices].sort((a, b) => {
      const da = a.invoice_date ?? "9999";
      const db = b.invoice_date ?? "9999";
      if (da !== db) return da < db ? -1 : 1;
      return a.id - b.id;
    });
    return sorted.map((inv, idx) => {
      const bal = Number(inv.balance ?? 0);
      const paid = Number(inv.paid_total ?? 0);
      const state: "PAID" | "PARTIAL" | "PENDING" =
        inv.balance != null && bal === 0 ? "PAID" : paid > 0 ? "PARTIAL" : "PENDING";
      const displayDate = inv.invoice_date ?? inv.payment_due_date ?? null;
      return { ...inv, seq: idx + 1, state, displayDate };
    });
  }, [data]);

  const opSummary = useMemo(() => {
    if (!data) return { ordered: 0, invoiced: 0, shipped: 0, toDispatch: 0 };
    return data.models.reduce(
      (acc, m) => ({
        ordered: acc.ordered + (m.quantity_ordered ?? 0),
        invoiced: acc.invoiced + (m.quantity_invoiced ?? 0),
        shipped: acc.shipped + (m.quantity_shipped ?? 0),
        toDispatch: acc.toDispatch + (m.to_dispatch ?? 0),
      }),
      { ordered: 0, invoiced: 0, shipped: 0, toDispatch: 0 },
    );
  }, [data]);

  const itemsOpSummary = useMemo(() => computeOpSummary(data?.models ?? []), [data?.models]);

  async function liquidate(p: Payment) {
    try {
      const inv = data?.invoices.find((i) => i.id === p.invoice_id);
      let exchangeRate: string | undefined = inv?.expected_exchange_rate ?? undefined;
      try {
        const ref = await financeApi.fxReference();
        if (ref.rate) exchangeRate = ref.rate;
      } catch {
        /* mantém câmbio da fatura */
      }
      await financeApi.updatePayment(p.id, {
        payment_date: new Date().toISOString().slice(0, 10),
        receipt_reference: `LIQ-${p.id}`,
        ...(exchangeRate ? { exchange_rate: exchangeRate } : {}),
      });
      toast.success("Pagamento liquidado");
      reloadCentral();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Não foi possível liquidar o pagamento.");
    }
  }

  async function savePaymentField(p: Payment, patch: Record<string, string | null>) {
    await financeApi.updatePayment(p.id, patch);
    reloadCentral();
  }

  const orderNetEur = useMemo(() => {
    if (!data) return null;
    const est = data.order.estimated_total;
    if (est != null && est !== "") return Number(est);
    return null;
  }, [data]);

  const remainingToInvoice = useMemo(() => {
    if (!data) return null;
    const invoiced = data.kpis.total_invoiced != null ? Number(data.kpis.total_invoiced) : null;
    return orderRemainingToInvoice(orderNetEur, invoiced);
  }, [data, orderNetEur]);

  const provisionRateStr = useMemo(() => {
    if (!data) return "";
    const fromInv = [...data.invoices].reverse().find((i) => i.expected_exchange_rate)?.expected_exchange_rate;
    if (fromInv) return fromInv;
    if (fxReference?.rate) return fxReference.rate;
    return "";
  }, [data, fxReference?.rate]);

  const provisionRateNum = useMemo(() => {
    const n = Number(String(provisionRateStr).replace(",", "."));
    return Number.isNaN(n) ? null : n;
  }, [provisionRateStr]);

  useEffect(() => {
    if (!data || invNumberTouched) return;
    const po = data.order.po_number;
    const suffix = nextInvoiceSuffix(data.invoices, po);
    setInvNumber(suggestInvoiceNumber(po, suffix));
    const n = data.invoices.length;
    setInvType(n === 0 ? "ANTECIPO" : n === 1 ? "SALDO" : "COMPLEMENTAR");
  }, [data, invNumberTouched]);

  async function submitNewInvoice() {
    if (!data) return;
    if (!invNumber.trim()) {
      toast.error("Informe o número da fatura.");
      return;
    }
    if (!canSubmitInvoiceAmount(invAmountMode, invAmount, remainingToInvoice, provisionRateNum)) {
      toast.error("Informe valor e câmbio provisionado válidos.");
      return;
    }
    const resolved = resolveInvoiceAmount(invAmountMode, invAmount, remainingToInvoice, provisionRateNum);
    setSubmittingInvoice(true);
    let createdInvoiceId: number | null = null;
    try {
      const inv = await invoicesApi.create({
        importation_id: importationId,
        invoice_type: invType,
        invoice_number: invNumber.trim(),
        invoice_date: invDue || null,
        amount:
          resolved.invoiceAmountOrderCurrency !== null
            ? String(resolved.invoiceAmountOrderCurrency)
            : null,
        currency: data.kpis.currency,
        expected_exchange_rate: provisionRateStr || null,
      });
      createdInvoiceId = inv.id;
      if (invDue && resolved.paymentAmountBrl !== null) {
        try {
          await financeApi.createPayment({
            invoice_id: inv.id,
            payment_type: "ADVANCE",
            due_date: invDue,
            amount_foreign: String(resolved.paymentAmountBrl),
            currency_foreign: "BRL",
          });
        } catch (payErr) {
          toast.error(
            payErr instanceof Error
              ? `Fatura ${invNumber} criada, mas pagamento falhou: ${payErr.message}`
              : "Fatura criada, mas pagamento planejado falhou.",
          );
          reloadCentral();
          return;
        }
      }
      toast.success("Fatura registrada");
      setAddingInvoice(false);
      setInvAmount("");
      setInvDue("");
      setInvNumberTouched(false);
      reloadCentral();
    } catch (e) {
      if (createdInvoiceId) {
        toast.error("Fatura criada, mas houve erro em passo posterior. Revise na aba Financeiro.");
      } else {
        toast.error(e instanceof Error ? e.message : "Não foi possível criar a fatura.");
      }
    } finally {
      setSubmittingInvoice(false);
    }
  }

  async function uploadDoc(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await documentsApi.upload(file, "importation_order", String(importationId));
      toast.success("Documento anexado");
      reloadDocs();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível anexar o documento.");
    } finally {
      e.target.value = "";
    }
  }

  if (loading) return <LoadingState label="Carregando visão geral..." />;
  if (centralError || error) return <p className="error">{centralError || error}</p>;
  if (!data) return <LoadingState label="Carregando visão geral..." />;

  const { kpis, models, legacy_sheet_summary } = data;
  const planned = data.payments_planned ?? [];
  const settled = data.payments_settled ?? [];

  return (
    <div className="order-central-overview">
      <ItalyOverrideModal
        importationId={importationId}
        target={overrideTarget}
        onClose={() => setOverrideTarget(null)}
        onSaved={reloadCentral}
      />

      {/* 4. Resumo operacional */}
      <div className="oc-section">
        <div className="oc-section__head"><h3>Resumo operacional</h3></div>
        <div className="oc-summary-grid">
          <div className="oc-stat"><span className="oc-stat__l">Qtd pedida</span><span className="oc-stat__v">{opSummary.ordered || emptyDash(null)}</span></div>
          <div className="oc-stat"><span className="oc-stat__l">Qtd faturada</span><span className="oc-stat__v">{opSummary.invoiced || emptyDash(null)}</span></div>
          <div className="oc-stat"><span className="oc-stat__l">Qtd despachada</span><span className="oc-stat__v">{opSummary.shipped || emptyDash(null)}</span></div>
          <div className="oc-stat"><span className="oc-stat__l">A despachar</span><span className="oc-stat__v">{opSummary.toDispatch || emptyDash(null)}</span></div>
          <div className="oc-stat"><span className="oc-stat__l">Produtos/Modelos</span><span className="oc-stat__v">{models.length || emptyDash(null)}</span></div>
          {legacy_sheet_summary?.versato_amount && (
            <div className="oc-stat" title="Valor informado na planilha Heroes; não equivale a pagamento oficial sem comprovante.">
              <span className="oc-stat__l">Versato Heroes</span>
              <span className="oc-stat__v">{formatMoney(legacy_sheet_summary.versato_amount, legacy_sheet_summary.versato_currency ?? kpis.currency)}</span>
            </div>
          )}
        </div>
      </div>

      {/* 5. Faturas + Itens */}
      <div className="oc-section">
        <div className="oc-section__head">
          <h3>Faturas · acconto · crédito por {productModelLabel().toLowerCase()}</h3>
          <span className="oc-section__count">{data.invoices.length} faturas</span>
        </div>
        {invoiceStages.length > 0 && (
          <>
            <div className="inv-stages">
              {invoiceStages.map((s) => (
                <div key={s.id} className={`inv-stage inv-stage--${s.state.toLowerCase()}`}>
                  <div className="inv-stage__top">
                    <span className="inv-stage__seq">Fatura {s.seq}</span>
                    <Badge tone={s.state === "PAID" ? "success" : s.state === "PARTIAL" ? "info" : "warning"}>
                      {s.state === "PAID" ? "Quitada" : s.state === "PARTIAL" ? "Parcial" : "Em aberto"}
                    </Badge>
                  </div>
                  <div className="inv-stage__role">{invoiceStageHint(s.invoice_type, s.seq)}</div>
                  <div className="inv-stage__num">
                    {s.invoice_number || emptyDash(null)} ·{" "}
                    {s.displayDate ? fmtDate(s.displayDate) : "sem data"}
                  </div>
                  <div className="inv-stage__amounts">
                    <span><i>Valor</i> {formatMoney(s.amount, s.currency)}</span>
                    <span><i>Pago</i> {formatMoney(s.paid_total, s.currency)}</span>
                    <span className="inv-stage__bal"><i>Saldo</i> {formatMoney(s.balance, s.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        <div className="sheet-grid-wrap">
          <table className="sheet-grid">
            <thead>
              <tr>
                <th>Etapa</th>
                <th>Data</th>
                <th>Nº fatura</th>
                <th className="num">Qtd</th>
                <th>{productModelLabel()}</th>
                <th className="num">Acconto</th>
                <th className="num">Acconto rimasto</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {blockARows.length === 0 ? (
                <tr><td colSpan={8}>Nenhuma fatura registrada</td></tr>
              ) : (
                blockARows.map((r) => (
                  <tr key={r.key} className={r.isFirst ? "sheet-row--invhead" : ""}>
                    <td>
                      {r.isFirst ? (
                        <span className="inv-tag" title={invoiceStageHint(r.invoiceType, r.seq)}>
                          <b>Fatura {r.seq}</b>
                          <span className="inv-tag__type">{invoiceTypeLabel(r.invoiceType)}</span>
                        </span>
                      ) : ""}
                    </td>
                    <td>{r.isFirst ? (r.date ? fmtDate(r.date) : emptyDash(null)) : ""}</td>
                    <td>
                      {r.invoiceNumber ? (
                        <LockedCell
                          onOverride={r.isFirst ? () => setOverrideTarget({ entityType: "invoice", entityId: r.invoiceId, fieldName: "invoice_number", fieldLabel: "Nº fatura", currentValue: r.invoiceNumber }) : undefined}
                        >
                          {r.invoiceNumber}
                        </LockedCell>
                      ) : ""}
                    </td>
                    <td className="num">
                      {r.qty != null ? (
                        <LockedCell onOverride={r.qtyItemId ? () => setOverrideTarget({ entityType: "invoice_item", entityId: r.qtyItemId!, fieldName: "quantity", fieldLabel: "Quantidade", currentValue: String(r.qty) }) : undefined}>
                          {r.qty}
                        </LockedCell>
                      ) : emptyDash(null)}
                    </td>
                    <td>{r.model}</td>
                    <td className="num c-acconto">{r.acconto ? <LockedCell>{r.acconto}</LockedCell> : ""}</td>
                    <td className="num c-acconto">{r.accontoRimasto ? <LockedCell>{r.accontoRimasto}</LockedCell> : ""}</td>
                    <td>{r.status ? <Badge tone="success">{r.status}</Badge> : ""}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>Totais</td>
                <td className="num">{blockARows.reduce((s, r) => s + (r.qty ?? 0), 0) || emptyDash(null)}</td>
                <td></td>
                <td className="num">{formatMoney(kpis.total_invoiced, kpis.currency)}</td>
                <td className="num">{formatMoney(kpis.consolidated_balance, kpis.currency)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* 6. Pagamentos */}
      <div className="oc-section">
        <div className="oc-section__head">
          <h3>Pagamentos</h3>
          <div className="oc-actbar" style={{ margin: 0 }}>
            <Button variant="secondary" className="ui-btn--sm" onClick={() => setAddingInvoice((v) => !v)}>
              {addingInvoice ? "Cancelar" : "+ Nova fatura"}
            </Button>
          </div>
        </div>
        {addingInvoice && data && (
          <div className="oc-invoice-form">
            <div className="ux-grid-2 nova-ordem__finance-grid">
              <div className="ux-field">
                <label htmlFor="oc-inv-number">Nº fatura</label>
                <input
                  id="oc-inv-number"
                  value={invNumber}
                  onChange={(e) => {
                    setInvNumberTouched(true);
                    setInvNumber(e.target.value);
                  }}
                />
              </div>
              <div className="ux-field">
                <label htmlFor="oc-inv-type">Tipo</label>
                <select id="oc-inv-type" value={invType} onChange={(e) => setInvType(e.target.value)}>
                  <option value="ANTECIPO">{invoiceTypeLabel("ANTECIPO")}</option>
                  <option value="SALDO">{invoiceTypeLabel("SALDO")}</option>
                  <option value="COMPLEMENTAR">{invoiceTypeLabel("COMPLEMENTAR")}</option>
                  <option value="PROFORMA">{invoiceTypeLabel("PROFORMA")}</option>
                </select>
              </div>
              <InvoiceAmountField
                mode={invAmountMode}
                value={invAmount}
                baseEur={remainingToInvoice}
                provisionRate={provisionRateStr}
                onModeChange={setInvAmountMode}
                onValueChange={setInvAmount}
              />
              <div className="ux-field">
                <label htmlFor="oc-inv-due">Vencimento do pagamento planejado</label>
                <input id="oc-inv-due" type="date" value={invDue} onChange={(e) => setInvDue(e.target.value)} />
              </div>
            </div>
            <Button
              className="ui-btn--sm"
              loading={submittingInvoice}
              disabled={
                !canSubmitInvoiceAmount(invAmountMode, invAmount, remainingToInvoice, provisionRateNum)
              }
              onClick={() => void submitNewInvoice()}
            >
              Salvar fatura
            </Button>
          </div>
        )}
        <div className="sheet-grid-wrap">
          <table className="sheet-grid">
            <thead>
              <tr>
                <th>Fatura</th>
                <th>Status</th>
                <th>Vencimento</th>
                <th>Pago em</th>
                <th className="num">Valor</th>
                <th>Comprovante</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {[...planned, ...settled].length === 0 ? (
                <tr><td colSpan={7}>Nenhum pagamento</td></tr>
              ) : (
                [...planned, ...settled].map((p) => {
                  const isPlanned = isPlannedPayment(p);
                  return (
                    <tr key={p.id}>
                      <td>{(p as Payment & { invoice_number?: string }).invoice_number ?? emptyDash(null)}</td>
                      <td><Badge status={isPlanned ? "PENDING" : "FULL_PAID"}>{isPlanned ? payStatusLabel("PLANNED") : payStatusLabel("SETTLED")}</Badge></td>
                      <td>
                        {isPlanned ? (
                          <EditableCell type="date" value={p.due_date ?? ""} display={p.due_date ? fmtDate(p.due_date) : undefined} onSave={(v) => savePaymentField(p, { due_date: v || null })} />
                        ) : (p.due_date ? fmtDate(p.due_date) : emptyDash(null))}
                      </td>
                      <td>{p.payment_date ? fmtDate(p.payment_date) : emptyDash(null)}</td>
                      <td className="num">{formatMoney(p.amount_foreign, p.currency_foreign ?? kpis.currency)}</td>
                      <td>
                        {isPlanned ? emptyDash(null) : (
                          <EditableCell value={p.receipt_reference ?? ""} onSave={(v) => savePaymentField(p, { receipt_reference: v || null })} placeholder="referência" />
                        )}
                      </td>
                      <td>
                        {isPlanned ? <Button variant="secondary" className="ui-btn--sm" onClick={() => liquidate(p)}>Liquidar</Button> : "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 7. Produtos — resumo */}
      <div className="oc-section">
        <div className="oc-section__head">
          <h3>Produtos e quantidades</h3>
          <Button
            variant="secondary"
            className="ui-btn--sm"
            onClick={() => navigate(`/importacoes/${importationId}/itens`)}
          >
            Ver produtos e quantidades
          </Button>
        </div>
        <p className="meta">
          {models.length} {productModelLabel().toLowerCase()} · {itemsOpSummary.ordered} un. pedidas ·{" "}
          {itemsOpSummary.toDispatch} a despachar
        </p>
      </div>

      {/* 9. Documentos principais */}
      <div className="oc-section">
        <div className="oc-section__head">
          <h3>Documentos</h3>
          <label className="ui-btn ui-btn--secondary ui-btn--sm" style={{ cursor: "pointer" }}>
            + Anexar documento
            <input type="file" style={{ display: "none" }} onChange={uploadDoc} />
          </label>
        </div>
        {docs.length === 0 ? (
          <p className="meta">Nenhum documento anexado.</p>
        ) : (
          <div className="sheet-grid-wrap">
            <table className="sheet-grid">
              <thead><tr><th>Arquivo</th><th>Tipo</th><th>Versão</th></tr></thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id}><td>{d.original_filename}</td><td>{d.document_type ?? emptyDash(null)}</td><td>v{d.version}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 10. Histórico resumido */}
      <div className="oc-section">
        <div className="oc-section__head"><h3>Histórico recente</h3></div>
        {timeline.length === 0 ? (
          <p className="meta">Sem eventos recentes.</p>
        ) : (
          <ul className="hub-timeline">
            {timeline.map((e, i) => {
              const f = formatTimelineEvent(e);
              return (
                <li key={i}>
                  <time>{fmtDateTime(e.timestamp)}</time>
                  <strong>{f.title}</strong>
                  <span>{f.detail}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
