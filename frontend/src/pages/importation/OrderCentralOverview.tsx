import { useEffect, useMemo, useState } from "react";
import {
  closureApi,
  documentsApi,
  financeApi,
  productsApi,
  type DocumentAttachment,
  type Payment,
  type TimelineEvent,
} from "../../api";
import { Badge, Button, EditableCell, LoadingState, useToast } from "../../components";
import {
  emptyDash,
  formatMoney,
  invoiceTypeLabel,
  payStatusLabel,
  productCategoryLabel,
  productModelLabel,
} from "../../i18n/glossario";
import { fmtDate, fmtDateTime, isPlannedPayment } from "../../utils/formatDate";
import { formatTimelineEvent } from "../../utils/timelineFormat";
import { ItalyOverrideModal, type ItalyOverrideTarget } from "./ItalyOverrideModal";
import { useOrderCentral } from "./OrderCentralContext";

const CATEGORY_OPTIONS = [
  { value: "RACKET", label: "Raquete" },
  { value: "BALL", label: "Bola" },
  { value: "BAG_ACCESSORY", label: "Bolsa/Acessório" },
  { value: "APPAREL", label: "Roupa" },
  { value: "PICKLEBALL", label: "Pickleball" },
  { value: "OTHER", label: "Outro" },
];

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

function heroesCell(value: string | null | undefined, heroesSource?: boolean) {
  if (value == null || value === "") return emptyDash(null);
  if (!heroesSource) return value;
  return (
    <span title="Origem: planilha Heroes — não equivale a dado oficial sem comprovante">
      {value}
      <span className="sheet-flag-it" style={{ marginLeft: 4 }}>H</span>
    </span>
  );
}

interface Props {
  importationId: number;
}

function LockedCell({ children, onOverride }: { children: React.ReactNode; onOverride?: () => void }) {
  if (!onOverride) {
    return (
      <span className="sheet-cell sheet-cell--locked" title="Campo origem Itália — não pode ser editado diretamente">
        {children}
        <span className="sheet-flag-it">IT</span>
      </span>
    );
  }
  return (
    <button
      type="button"
      className="sheet-cell sheet-cell--locked sheet-cell--locked-btn"
      title="Campo origem Itália. Não pode ser editado diretamente — use override auditado (motivo + anexo)."
      onClick={onOverride}
    >
      {children}
      <span className="sheet-flag-it">IT</span>
    </button>
  );
}

export function OrderCentralOverview({ importationId }: Props) {
  const toast = useToast();
  const { data, loading, error: centralError, reloadCentral } = useOrderCentral();
  const [overrideTarget, setOverrideTarget] = useState<ItalyOverrideTarget | null>(null);
  const [docs, setDocs] = useState<DocumentAttachment[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [addingPayment, setAddingPayment] = useState(false);
  const [newPayInvoice, setNewPayInvoice] = useState("");
  const [newPayDue, setNewPayDue] = useState("");
  const [newPayAmount, setNewPayAmount] = useState("");
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
        rows.push({ key: `${inv.id}-${ii.id}`, date: idx === 0 ? inv.invoice_date : null, invoiceNumber: idx === 0 ? inv.invoice_number : "", qty: ii.quantity, qtyItemId: ii.id, invoiceId: inv.id, model: ii.description ?? ii.product_sku ?? emptyDash(null), acconto: idx === 0 ? acconto : "", accontoRimasto: idx === 0 ? rimasto : "", status: idx === 0 ? status : "", isFirst: idx === 0, isAntecipo, invoiceType: inv.invoice_type, seq });
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
      return { ...inv, seq: idx + 1, state };
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

  async function liquidate(p: Payment) {
    try {
      await financeApi.updatePayment(p.id, {
        payment_date: new Date().toISOString().slice(0, 10),
        receipt_reference: `LIQ-${p.id}`,
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

  async function submitNewPayment() {
    if (!newPayInvoice) {
      toast.error("Selecione a fatura do pagamento planejado.");
      return;
    }
    try {
      await financeApi.createPayment({
        invoice_id: Number(newPayInvoice),
        payment_type: "ADVANCE",
        due_date: newPayDue || null,
        amount_foreign: newPayAmount || null,
      });
      toast.success("Pagamento planejado adicionado");
      setAddingPayment(false);
      setNewPayInvoice("");
      setNewPayDue("");
      setNewPayAmount("");
      reloadCentral();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Não foi possível adicionar o pagamento.");
    }
  }

  async function saveCategory(productId: number | null, value: string) {
    if (!productId) {
      toast.error("Este item ainda não tem produto mapeado. Mapeie o SKU primeiro.");
      throw new Error("Sem produto mapeado");
    }
    await productsApi.update(productId, { category: value });
    reloadCentral();
  }

  async function saveSku(itemId: number, value: string) {
    await importationsApi.updateItemMapping(importationId, itemId, { supplier_sku: value || null });
    reloadCentral();
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
  if (!data) return null;

  const { kpis, models, legacy_sheet_summary } = data;
  const planned = data.payments_planned ?? [];
  const settled = data.payments_settled ?? [];
  const dispatchPending = (data.dispatch_pending ?? []) as Array<Record<string, unknown>>;

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
                    {s.invoice_number || emptyDash(null)} · {s.invoice_date ? fmtDate(s.invoice_date) : "sem data"}
                  </div>
                  <div className="inv-stage__amounts">
                    <span><i>Valor</i> {formatMoney(s.amount, s.currency)}</span>
                    <span><i>Pago</i> {formatMoney(s.paid_total, s.currency)}</span>
                    <span className="inv-stage__bal"><i>Saldo</i> {formatMoney(s.balance, s.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
            <p className="meta">
              Uma ordem costuma ter 3 faturas: <b>antecipo</b>, <b>na chegada</b> e <b>saldo (30/60 dias)</b>.
              Cada fatura tem seu próprio acconto e saldo.
            </p>
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
        <p className="meta"><span className="sheet-flag-it">IT</span> campo origem Itália — bloqueado; clique para override auditado (motivo + anexo).</p>
      </div>

      {/* 6. Pagamentos */}
      <div className="oc-section">
        <div className="oc-section__head">
          <h3>Pagamentos</h3>
          <div className="oc-actbar" style={{ margin: 0 }}>
            <Button variant="secondary" className="ui-btn--sm" onClick={() => setAddingPayment((v) => !v)}>
              {addingPayment ? "Cancelar" : "+ Pagamento planejado"}
            </Button>
          </div>
        </div>
        <p className="meta">Planejado não reduz saldo · Liquidado reduz · Vencimento ≠ data real de pagamento.</p>
        {addingPayment && (
          <div className="oc-actbar">
            <select className="input" value={newPayInvoice} onChange={(e) => setNewPayInvoice(e.target.value)}>
              <option value="">Fatura…</option>
              {data.invoices.map((inv) => (
                <option key={inv.id} value={inv.id}>{inv.invoice_number}</option>
              ))}
            </select>
            <input className="input" type="date" title="Vencimento" value={newPayDue} onChange={(e) => setNewPayDue(e.target.value)} />
            <input className="input" type="number" placeholder="Valor" value={newPayAmount} onChange={(e) => setNewPayAmount(e.target.value)} />
            <Button className="ui-btn--sm" onClick={submitNewPayment}>Salvar</Button>
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

      {/* 7. DA SPEDIRE / Despacho (origem Heroes) */}
      {dispatchPending.length > 0 && (
        <div className="oc-section">
          <div className="oc-section__head">
            <h3>DA SPEDIRE / Despacho (planilha Heroes)</h3>
            <span className="oc-section__count">{dispatchPending.length} linhas</span>
          </div>
          <div className="sheet-grid-wrap">
            <table className="sheet-grid">
              <thead>
                <tr>
                  <th>{productModelLabel()}</th>
                  <th>Categoria sugerida</th>
                  <th className="num">A despachar</th>
                  <th className="num">Preço listino</th>
                  <th className="num">Preço fattura</th>
                  <th className="num">Sconto</th>
                  <th>Revisão</th>
                </tr>
              </thead>
              <tbody>
                {dispatchPending.map((d, i) => (
                  <tr key={i}>
                    <td>{String(d.product_name_raw ?? emptyDash(null))}</td>
                    <td>{productCategoryLabel(d.product_category_suggested as string | null)}</td>
                    <td className="num">{(d.quantity_to_dispatch as number | null) ?? emptyDash(null)}</td>
                    <td className="num">{heroesCell(d.price_listino ? formatMoney(d.price_listino as string, kpis.currency) : null, true)}</td>
                    <td className="num">{heroesCell(d.price_fattura ? formatMoney(d.price_fattura as string, kpis.currency) : null, true)}</td>
                    <td className="num">{heroesCell(d.discount_unit ? formatMoney(d.discount_unit as string, kpis.currency) : null, true)}</td>
                    <td>{d.needs_review ? <Badge tone="warning">Revisar</Badge> : emptyDash(null)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 8. Produtos / Modelos */}
      <div className="oc-section">
        <div className="oc-section__head">
          <h3>Por {productModelLabel().toLowerCase()} · a despachar · preço e desconto</h3>
          <span className="oc-section__count">{models.length} {productModelLabel().toLowerCase()}</span>
        </div>
        <div className="sheet-grid-wrap">
          <table className="sheet-grid">
            <thead>
              <tr>
                <th className="sticky-col">{productModelLabel()}</th>
                <th>SKU mapeado</th>
                <th>Categoria</th>
                <th className="num">A despachar</th>
                <th className="num">Pedida</th>
                <th className="num">Faturada</th>
                <th className="num">Despachada</th>
                <th className="num">Nac./receb.</th>
                <th>Progresso</th>
                <th className="num">Preço listino</th>
                <th className="num">Preço fattura</th>
                <th className="num">Sconto</th>
              </tr>
            </thead>
            <tbody>
              {models.length === 0 ? (
                <tr><td colSpan={12}>Nenhum item na ordem</td></tr>
              ) : (
                models.map((m) => {
                  const ordered = m.quantity_ordered ?? 0;
                  const shipped = m.quantity_shipped ?? 0;
                  const pct = ordered > 0 ? Math.round((shipped / ordered) * 100) : 0;
                  const highlight = (m.to_dispatch ?? 0) > 0;
                  return (
                    <tr key={m.importation_item_id} className={highlight ? "sheet-row--dispatch" : ""}>
                      <td className="sticky-col"><b>{m.model_label ?? m.description ?? m.supplier_sku ?? `Item #${m.importation_item_id}`}</b></td>
                      <td>
                        <EditableCell value={m.supplier_sku ?? ""} onSave={(v) => saveSku(m.importation_item_id, v)} placeholder="—" />
                      </td>
                      <td>
                        <EditableCell
                          type="select"
                          options={CATEGORY_OPTIONS}
                          value={m.product_category ?? ""}
                          display={m.product_category ? productCategoryLabel(m.product_category) : undefined}
                          editable={!!m.product_id}
                          lockedReason={!m.product_id ? "Mapeie o SKU/produto antes de definir a categoria." : undefined}
                          onSave={(v) => saveCategory(m.product_id, v)}
                        />
                      </td>
                      <td className={`num${highlight ? " sheet-warn" : ""}`}>{m.to_dispatch ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_ordered ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_invoiced ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_shipped ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_stocked ?? m.quantity_nationalized ?? emptyDash(null)}</td>
                      <td>
                        <div className="sheet-prog">
                          <div className="sheet-prog__track"><div className="sheet-prog__fill" style={{ width: `${pct}%` }} /></div>
                          <span className="sheet-prog__pct">{pct}%</span>
                        </div>
                      </td>
                      <td className="num">{heroesCell(m.price_listino ? formatMoney(m.price_listino, kpis.currency) : null, m.heroes_source)}</td>
                      <td className="num">{heroesCell(m.price_fattura ? formatMoney(m.price_fattura, kpis.currency) : null, m.heroes_source)}</td>
                      <td className="num c-credito">{heroesCell(m.discount_unit ? formatMoney(m.discount_unit, kpis.currency) : null, m.heroes_source)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
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
