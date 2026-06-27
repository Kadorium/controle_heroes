import { useEffect, useMemo, useRef, useState } from "react";
import {
  financeApi,
  importationsApi,
  invoicesApi,
  productsApi,
  suppliersApi,
  type BrazilAccount,
  type Product,
  type Supplier,
} from "../../api";
import { Button, ProductCombobox } from "../../components";
import { DEFAULT_IMPORT_CURRENCY } from "../../constants/currency";
import { emptyDash, formatAmount, formatMoney } from "../../i18n/glossario";
import {
  aggregateTotals,
  itemHasContent,
  lineTotals,
  parseDecimalInput,
  rateWithMarkup,
} from "./novaOrdemTotals";
import { dedupeSuppliersByName, pickHeroesSupplierId } from "./supplierUtils";
import { NovaOrdemFxSummary } from "./NovaOrdemFxSummary";
import { InvoiceAmountField } from "../../components/InvoiceAmountField";
import {
  canSubmitInvoiceAmount,
  nextInvoiceSuffix,
  resolveInvoiceAmount,
  suggestInvoiceNumber,
  type InvoiceAmountMode,
} from "./novaOrdemInvoice";
import { useFxRate } from "../../context/FxRateContext";

interface Props {
  onClose: () => void;
  onCreated: (importationId: number) => void;
}

interface ItemDraft {
  key: string;
  product_id: number | null;
  sku_code: string;
  description: string;
  quantity_ordered: string;
  unit_price_foreign: string;
  discount_amount_foreign: string;
}

function newItemRow(): ItemDraft {
  return {
    key: crypto.randomUUID(),
    product_id: null,
    sku_code: "",
    description: "",
    quantity_ordered: "",
    unit_price_foreign: "",
    discount_amount_foreign: "",
  };
}

function decimalOrNull(raw: string): string | null {
  const n = parseDecimalInput(raw);
  return n === null ? null : String(n);
}

export function NovaOrdemModal({ onClose, onCreated }: Props) {
  const poRef = useRef<HTMLInputElement>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [brazilAccounts, setBrazilAccounts] = useState<BrazilAccount[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [confirmEmptyItems, setConfirmEmptyItems] = useState(false);

  const [po, setPo] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [currency] = useState(DEFAULT_IMPORT_CURRENCY);
  const [incoterm, setIncoterm] = useState("FOB");
  const [notes, setNotes] = useState("");

  const [items, setItems] = useState<ItemDraft[]>([newItemRow()]);

  const [invNumber, setInvNumber] = useState("");
  const [invNumberTouched, setInvNumberTouched] = useState(false);
  const [invAmount, setInvAmount] = useState("");
  const [invAmountMode, setInvAmountMode] = useState<InvoiceAmountMode>("EUR");
  const [payDue, setPayDue] = useState("");

  const [markupPct, setMarkupPct] = useState("0");
  const [provisionRate, setProvisionRate] = useState("");
  const [rateManual, setRateManual] = useState(false);
  const { reference: fxReference } = useFxRate();

  const supplierOptions = useMemo(() => dedupeSuppliersByName(suppliers), [suppliers]);
  const totals = useMemo(() => aggregateTotals(items), [items]);

  const ccPreview = useMemo(() => {
    const active = brazilAccounts.filter((a) => a.is_active && Number(a.amount_available) > 0);
    if (!active.length) return null;
    const total = active.reduce((s, a) => s + Number(a.amount_available), 0);
    const cur = active[0]?.currency ?? currency;
    return formatMoney(total, cur);
  }, [brazilAccounts, currency]);

  useEffect(() => {
    Promise.all([suppliersApi.list(), productsApi.list()])
      .then(([sups, prods]) => {
        setSuppliers(sups);
        setProducts(prods);
        setSupplierId(pickHeroesSupplierId(sups));
      })
      .catch(() => undefined);
    poRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!supplierId) {
      setBrazilAccounts([]);
      return;
    }
    financeApi
      .listBrazilAccounts(Number(supplierId))
      .then(setBrazilAccounts)
      .catch(() => setBrazilAccounts([]));
  }, [supplierId]);

  useEffect(() => {
    if (!rateManual && fxReference?.rate) {
      applyRateFromReference(fxReference, markupPct, false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fxReference?.rate]);

  const refreshSuggestedInvoiceNumber = useMemo(
    () => async (poNumber: string) => {
      const trimmed = poNumber.trim();
      if (!trimmed) {
        if (!invNumberTouched) setInvNumber("");
        return;
      }
      try {
        const importations = await importationsApi.list();
        const existing = importations.find(
          (imp) => imp.is_active && imp.po_number.trim() === trimmed,
        );
        const invoices = existing ? await invoicesApi.list(existing.id) : [];
        const suffix = nextInvoiceSuffix(invoices, trimmed);
        if (!invNumberTouched) setInvNumber(suggestInvoiceNumber(trimmed, suffix));
      } catch {
        if (!invNumberTouched) setInvNumber(suggestInvoiceNumber(trimmed, "A"));
      }
    },
    [invNumberTouched],
  );

  useEffect(() => {
    void refreshSuggestedInvoiceNumber(po);
  }, [po, refreshSuggestedInvoiceNumber]);

  function applyRateFromReference(ref = fxReference, markup = markupPct, manual = rateManual) {
    if (manual || !ref?.rate) return;
    const base = parseDecimalInput(ref.rate);
    const m = parseDecimalInput(markup) ?? 0;
    const computed = rateWithMarkup(base, m);
    if (computed !== null) setProvisionRate(String(computed));
  }

  function onMarkupChange(value: string) {
    setMarkupPct(value);
    if (!rateManual && fxReference?.rate) {
      const base = parseDecimalInput(fxReference.rate);
      const m = parseDecimalInput(value) ?? 0;
      const computed = rateWithMarkup(base, m);
      if (computed !== null) setProvisionRate(String(computed));
    }
  }

  function onProvisionRateChange(value: string) {
    setRateManual(true);
    setProvisionRate(value);
  }

  function resetRateFromReference() {
    setRateManual(false);
    applyRateFromReference(fxReference, markupPct, false);
  }

  const canCreateBase = po.trim().length > 0 && supplierId !== "";

  function updateItem(key: string, patch: Partial<ItemDraft>) {
    setItems((rows) => rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function duplicateRow(key: string) {
    const src = items.find((r) => r.key === key);
    if (!src) return;
    setItems((rows) => {
      const idx = rows.findIndex((r) => r.key === key);
      const copy = { ...src, key: crypto.randomUUID() };
      const next = [...rows];
      next.splice(idx + 1, 0, copy);
      return next;
    });
  }

  function removeRow(key: string) {
    setItems((rows) => (rows.length <= 1 ? rows : rows.filter((r) => r.key !== key)));
  }

  function buildPayloadItems() {
    return items
      .filter(itemHasContent)
      .map((it) => ({
        product_id: it.product_id,
        description: it.description.trim() || it.sku_code.trim() || null,
        quantity_ordered: decimalOrNull(it.quantity_ordered),
        unit_price_foreign: decimalOrNull(it.unit_price_foreign),
        discount_amount_foreign: decimalOrNull(it.discount_amount_foreign),
      }));
  }

  async function doCreate() {
    setSaving(true);
    setError("");
    try {
      const payloadItems = buildPayloadItems();
      const imp = await importationsApi.create({
        po_number: po.trim(),
        supplier_id: Number(supplierId),
        currency,
        incoterm,
        estimated_total: totals.net !== null ? String(totals.net) : null,
        opening_exchange_rate: decimalOrNull(provisionRate),
        items: payloadItems,
      });
      if (notes.trim()) {
        await importationsApi.updateBrazilFields(imp.id, { brazil_operational_notes: notes.trim() });
      }
      let invoiceId: number | null = null;
      const rate = parseDecimalInput(provisionRate);
      const resolvedInv = resolveInvoiceAmount(invAmountMode, invAmount, totals.net, rate);
      if (invNumber.trim()) {
        const inv = await invoicesApi.create({
          importation_id: imp.id,
          invoice_type: "PROFORMA",
          invoice_number: invNumber.trim(),
          invoice_date: payDue || null,
          amount:
            resolvedInv.invoiceAmountOrderCurrency !== null
              ? String(resolvedInv.invoiceAmountOrderCurrency)
              : null,
          currency,
          expected_exchange_rate: decimalOrNull(provisionRate),
        });
        invoiceId = inv.id;
      }
      if (invoiceId && payDue && resolvedInv.paymentAmountBrl !== null) {
        await financeApi.createPayment({
          invoice_id: invoiceId,
          payment_type: "ADVANCE",
          due_date: payDue,
          amount_foreign: String(resolvedInv.paymentAmountBrl),
          currency_foreign: "BRL",
        });
      }
      onCreated(imp.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível criar a ordem.");
    } finally {
      setSaving(false);
      setConfirmEmptyItems(false);
    }
  }

  function handleSubmit() {
    if (!canCreateBase) {
      setError("Informe número da ordem e fornecedor.");
      return;
    }
    const hasItems = buildPayloadItems().length > 0;
    if (!hasItems && !confirmEmptyItems) {
      setConfirmEmptyItems(true);
      return;
    }
    void doCreate();
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="ux-modal ux-modal--wide" onClick={(e) => e.stopPropagation()}>
        <div className="ux-modal__head nova-ordem__modal-head">
          <div>
            <h2>Nova ordem</h2>
            <p className="meta" style={{ margin: "4px 0 0" }}>
              Planilha de abertura — complete o restante na Central da Ordem.
            </p>
          </div>
          <div className="nova-ordem__fx-head">
            <label className="nova-ordem__fx-head-field">
              <span>Mark-up %</span>
              <input
                type="text"
                inputMode="decimal"
                value={markupPct}
                onChange={(e) => onMarkupChange(e.target.value)}
                aria-label="Mark-up percentual sobre a cotação do header"
              />
            </label>
            <label className="nova-ordem__fx-head-field nova-ordem__fx-head-field--rate">
              <span>Câmbio provisionado</span>
              <input
                type="text"
                inputMode="decimal"
                value={provisionRate}
                onChange={(e) => onProvisionRateChange(e.target.value)}
                placeholder="EUR → BRL"
                aria-label="Taxa EUR para BRL provisionada na abertura"
              />
            </label>
            {rateManual && fxReference?.rate && (
              <Button variant="ghost" className="ui-btn--sm" onClick={resetRateFromReference}>
                Ref. + mark-up
              </Button>
            )}
          </div>
        </div>

        <div className="ux-modal__body nova-ordem">
          {error && <p className="error">{error}</p>}

          {confirmEmptyItems && (
            <div className="nova-ordem__confirm" role="alert">
              <p>Criar ordem <strong>sem itens</strong>? Você poderá adicioná-los depois na Central.</p>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <Button variant="secondary" onClick={() => setConfirmEmptyItems(false)}>
                  Voltar e adicionar itens
                </Button>
                <Button onClick={() => void doCreate()} loading={saving}>
                  Sim, criar sem itens
                </Button>
              </div>
            </div>
          )}

          <section className="nova-ordem__header">
            <div className="ux-grid-3">
              <div className="ux-field">
                <label htmlFor="nova-po">Número da ordem *</label>
                <input
                  id="nova-po"
                  ref={poRef}
                  value={po}
                  onChange={(e) => setPo(e.target.value)}
                  placeholder="ex.: 760"
                />
              </div>
              <div className="ux-field">
                <label htmlFor="nova-supplier">Fornecedor *</label>
                <select
                  id="nova-supplier"
                  value={supplierId}
                  onChange={(e) => setSupplierId(e.target.value)}
                >
                  <option value="">Selecionar…</option>
                  {supplierOptions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {s.country ? ` · ${s.country}` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div className="ux-field">
                <label>Moeda / Incoterm</label>
                <div className="nova-ordem__badges">
                  <span className="badge-pill">{currency}</span>
                  <input
                    className="nova-ordem__incoterm"
                    value={incoterm}
                    onChange={(e) => setIncoterm(e.target.value)}
                    aria-label="Incoterm"
                  />
                </div>
              </div>
            </div>
            {ccPreview && (
              <p className="nova-ordem__cc-pill meta">
                Conta corrente disponível (somente leitura): <strong>{ccPreview}</strong>
              </p>
            )}
            <div className="ux-field">
              <label htmlFor="nova-notes">Observação operacional (Brasil)</label>
              <input id="nova-notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Opcional" />
            </div>
          </section>

          <section className="nova-ordem__items">
            <div className="nova-ordem__items-head">
              <h3>Itens do pedido</h3>
              <Button variant="ghost" onClick={() => setItems((r) => [...r, newItemRow()])}>
                + Adicionar linha
              </Button>
            </div>
            <div className="nova-ordem__items-wrap sheet-grid-wrap">
              <table className="sheet-grid nova-ordem__grid">
                <thead>
                  <tr>
                    <th>Produto / SKU</th>
                    <th className="num">Qtd</th>
                    <th className="num">Preço €/un</th>
                    <th className="num">Desc. €/un</th>
                    <th className="num">Subtotal €</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((row, idx) => {
                    const lt = lineTotals(row);
                    const isLastRow = idx === items.length - 1;
                    return (
                      <tr key={row.key}>
                        <td>
                          <ProductCombobox
                            products={products}
                            value={row.sku_code}
                            productId={row.product_id}
                            onChange={({ text, product }) =>
                              updateItem(row.key, {
                                sku_code: text,
                                product_id: product?.id ?? null,
                                description: product?.description ?? row.description,
                              })
                            }
                          />
                        </td>
                        <td className="num">
                          <input
                            type="number"
                            className="nova-ordem__cell-input"
                            value={row.quantity_ordered}
                            onChange={(e) => updateItem(row.key, { quantity_ordered: e.target.value })}
                          />
                        </td>
                        <td className="num">
                          <input
                            type="text"
                            inputMode="decimal"
                            className="nova-ordem__cell-input"
                            value={row.unit_price_foreign}
                            onChange={(e) => updateItem(row.key, { unit_price_foreign: e.target.value })}
                          />
                        </td>
                        <td className="num">
                          <input
                            type="text"
                            inputMode="decimal"
                            className="nova-ordem__cell-input"
                            title="Desconto por unidade — multiplicado pela qtd na linha"
                            value={row.discount_amount_foreign}
                            onChange={(e) => updateItem(row.key, { discount_amount_foreign: e.target.value })}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && isLastRow) {
                                e.preventDefault();
                                setItems((r) => [...r, newItemRow()]);
                              }
                            }}
                          />
                        </td>
                        <td className="num" title={lt.gross !== null && lt.net !== null && lt.gross !== lt.net ? `Bruto: ${formatAmount(lt.gross)}` : undefined}>
                          {lt.net !== null ? formatAmount(lt.net) : emptyDash(null)}
                        </td>
                        <td className="nova-ordem__actions">
                          <button type="button" className="link-btn" onClick={() => duplicateRow(row.key)} title="Duplicar">
                            ⧉
                          </button>
                          <button
                            type="button"
                            className="link-btn"
                            onClick={() => removeRow(row.key)}
                            disabled={items.length <= 1}
                            title="Remover"
                          >
                            ×
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot className="nova-ordem__totals">
                  <tr>
                    <td colSpan={2}>
                      <strong>Totais (EUR)</strong>
                      {totals.quantity !== null && (
                        <span className="meta"> · {totals.quantity} un.</span>
                      )}
                    </td>
                    <td className="num">
                      Bruto: {totals.gross !== null ? formatAmount(totals.gross) : emptyDash(null)}
                    </td>
                    <td className="num">
                      Desc.: {totals.discounts !== null ? formatAmount(totals.discounts) : emptyDash(null)}
                    </td>
                    <td className="num">
                      <strong>
                        Líq.: {totals.net !== null ? formatAmount(totals.net) : emptyDash(null)}
                      </strong>
                    </td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
            <NovaOrdemFxSummary totals={totals} provisionRate={provisionRate} />
          </section>

          <details
            className="nova-ordem__finance"
            onToggle={(e) => {
              if ((e.target as HTMLDetailsElement).open && po.trim() && !invNumberTouched) {
                void refreshSuggestedInvoiceNumber(po);
              }
            }}
          >
            <summary>Financeiro inicial (opcional)</summary>
            <div className="ux-grid-2 nova-ordem__finance-grid">
              <div className="ux-field">
                <label htmlFor="nova-inv-number">Fatura PROFORMA — nº</label>
                <input
                  id="nova-inv-number"
                  value={invNumber}
                  onChange={(e) => {
                    setInvNumberTouched(true);
                    setInvNumber(e.target.value);
                  }}
                  placeholder={po.trim() ? `${po.trim()}A` : "ex.: 760A"}
                />
                <p className="meta nova-ordem__inv-hint">
                  Referência automática: número da ordem + próxima letra (A, B, C…).
                </p>
              </div>
              <InvoiceAmountField
                mode={invAmountMode}
                value={invAmount}
                baseEur={totals.net}
                provisionRate={provisionRate}
                onModeChange={setInvAmountMode}
                onValueChange={setInvAmount}
              />
              <div className="ux-field">
                <label htmlFor="nova-pay-due">Pagamento planejado — vencimento</label>
                <input id="nova-pay-due" type="date" value={payDue} onChange={(e) => setPayDue(e.target.value)} />
              </div>
            </div>
          </details>
        </div>

        <div className="ux-modal__foot">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} loading={saving} disabled={!canCreateBase || confirmEmptyItems}>
            Criar e abrir ordem
          </Button>
        </div>
      </div>
    </div>
  );
}
