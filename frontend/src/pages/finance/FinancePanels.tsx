import { useCallback, useEffect, useState } from "react";
import {
  financeApi,
  importationsApi,
  invoicesApi,
  suppliersApi,
  type BrazilAccount,
  type Credit,
  type Discount,
  type Expense,
  type FinancialSummary,
  type Importation,
  type ImportationItem,
  type Invoice,
  type Payment,
} from "../../api";
import { EXPENSE_TYPE_LABELS } from "../../constants/demoScenarios";
import { invoiceTypeLabel, modalLabel, payStatusLabel, shipmentStatusLabel } from "../../i18n/glossario";
import { fmtDate, isPlannedPayment } from "../../utils/formatDate";
import { Badge, Button, EmptyState, LoadingState, Table, useToast } from "../../components";

export type FinanceTab = "pagamentos" | "descontos" | "creditos" | "conta-br" | "despesas";

const TABS: { id: FinanceTab; label: string }[] = [
  { id: "pagamentos", label: "Pagamentos" },
  { id: "descontos", label: "Descontos" },
  { id: "creditos", label: "Créditos Heroes" },
  { id: "conta-br", label: "Conta corrente BR" },
  { id: "despesas", label: "Despesas Brasil" },
];

interface Scope {
  mode: "global" | "importation";
  importationId?: number;
  importation?: Importation;
  invoices?: Invoice[];
  items?: ImportationItem[];
  summary?: FinancialSummary | null;
  currency?: string;
  supplierId?: number;
  onReload?: () => Promise<void>;
}

export function FinanceTabBar({
  active,
  onChange,
}: {
  active: FinanceTab;
  onChange: (t: FinanceTab) => void;
}) {
  return (
    <div className="finance-tabs" role="tablist">
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={active === t.id}
          className={`finance-tabs__btn${active === t.id ? " finance-tabs__btn--active" : ""}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function InfoBanner({ children }: { children: React.ReactNode }) {
  return <p className="finance-info-banner">{children}</p>;
}

// ── Pagamentos ─────────────────────────────────────────────────────────────

export function PaymentsPanel({ scope }: { scope: Scope }) {
  const toast = useToast();
  const [importations, setImportations] = useState<Importation[]>([]);
  const [selectedImp, setSelectedImp] = useState(scope.importationId ? String(scope.importationId) : "");
  const [invoices, setInvoices] = useState<Invoice[]>(scope.invoices ?? []);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [selectedInv, setSelectedInv] = useState("");
  const [payAmount, setPayAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [paymentDate, setPaymentDate] = useState("");
  const [receiptRef, setReceiptRef] = useState("");
  const [plannedOnly, setPlannedOnly] = useState(false);
  const [loading, setLoading] = useState(false);

  const impId = scope.mode === "importation" ? scope.importationId : Number(selectedImp);

  const loadPayments = useCallback(async (invoiceList: Invoice[]) => {
    if (!invoiceList.length) {
      setPayments([]);
      return;
    }
    const all = await Promise.all(invoiceList.map((i) => financeApi.listPayments(i.id)));
    setPayments(all.flat().sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? "")));
  }, []);

  useEffect(() => {
    if (scope.mode === "global") {
      importationsApi.list().then(setImportations).catch(() => {});
    }
  }, [scope.mode]);

  useEffect(() => {
    if (scope.mode === "importation" && scope.invoices) {
      setInvoices(scope.invoices);
      loadPayments(scope.invoices);
      return;
    }
    if (!impId) {
      setInvoices([]);
      setPayments([]);
      return;
    }
    invoicesApi.list(impId).then((inv) => {
      setInvoices(inv);
      loadPayments(inv);
    });
  }, [impId, scope.mode, scope.invoices, loadPayments]);

  async function registerPayment(e: React.FormEvent) {
    e.preventDefault();
    try {
      const payload: Record<string, unknown> = {
        invoice_id: Number(selectedInv),
        payment_type: "PARTIAL",
        amount_foreign: payAmount || null,
        due_date: dueDate || null,
      };
      if (paymentDate) payload.payment_date = paymentDate;
      if (receiptRef) payload.receipt_reference = receiptRef;
      if (!plannedOnly && !receiptRef) payload.receipt_reference = "UI-REGISTRO";
      await financeApi.createPayment(payload);
      toast.success(plannedOnly ? "Pagamento planejado registrado" : "Pagamento registrado");
      setPayAmount("");
      setDueDate("");
      setPaymentDate("");
      setReceiptRef("");
      await loadPayments(invoices);
      await scope.onReload?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao registrar pagamento");
    }
  }

  async function liquidatePayment(p: Payment) {
    try {
      await financeApi.updatePayment(p.id, {
        payment_date: new Date().toISOString().slice(0, 10),
        receipt_reference: `LIQ-${p.id}`,
      });
      toast.success("Pagamento liquidado");
      await loadPayments(invoices);
      await scope.onReload?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao liquidar");
    }
  }

  const invoiceLabel = (id: number) => invoices.find((i) => i.id === id)?.invoice_number ?? String(id);

  return (
    <section className="finance-panel">
      <div className="finance-banners">
        <InfoBanner>Planejado não reduz saldo · Liquidado reduz.</InfoBanner>
        <InfoBanner>Crédito ≠ desconto — crédito é saldo do fornecedor; desconto reduz valor da fatura.</InfoBanner>
        <InfoBanner>Vencimento ≠ data real de pagamento — use a coluna &quot;Pago em&quot; para liquidação.</InfoBanner>
      </div>
      {scope.summary && (
        <p className="finance-summary-line">
          Faturado: {scope.summary.total_invoiced} · Pago: {scope.summary.total_paid} · Descontos:{" "}
          {scope.summary.total_discounts} · Saldo: {scope.summary.consolidated_balance ?? "—"}
        </p>
      )}
      <form className="inline-form" onSubmit={registerPayment}>
        {scope.mode === "global" && (
          <select value={selectedImp} onChange={(e) => setSelectedImp(e.target.value)} required>
            <option value="">Importação</option>
            {importations.map((i) => (
              <option key={i.id} value={i.id}>
                {i.po_number}
              </option>
            ))}
          </select>
        )}
        <select value={selectedInv} onChange={(e) => setSelectedInv(e.target.value)} required>
          <option value="">Fatura</option>
          {invoices.map((i) => (
            <option key={i.id} value={i.id}>
              {i.invoice_number}
            </option>
          ))}
        </select>
        <input placeholder="Valor" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} />
        <input type="date" title="Vencimento" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        <input
          type="date"
          title="Data do pagamento"
          value={paymentDate}
          onChange={(e) => setPaymentDate(e.target.value)}
        />
        <input
          placeholder="Comprovante"
          value={receiptRef}
          onChange={(e) => setReceiptRef(e.target.value)}
          disabled={plannedOnly}
        />
        <label className="inline-check">
          <input type="checkbox" checked={plannedOnly} onChange={(e) => setPlannedOnly(e.target.checked)} />
          Só planejado
        </label>
        <Button type="submit">{plannedOnly ? "Planejar pagamento" : "Registrar pagamento"}</Button>
      </form>
      {loading ? (
        <LoadingState label="Carregando pagamentos..." />
      ) : payments.length === 0 ? (
        <EmptyState title="Nenhum pagamento" description="Registre um pagamento planejado ou liquidado." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Fatura</th>
              <th>Tipo</th>
              <th>Status</th>
              <th>Vencimento</th>
              <th>Pago em</th>
              <th>Valor</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{invoiceLabel(p.invoice_id)}</td>
                <td>{payStatusLabel(p.payment_type)}</td>
                <td>{p.payment_date ? "Liquidado" : p.due_date ? "Planejado" : "Pendente"}</td>
                <td>{fmtDate(p.due_date)}</td>
                <td>{fmtDate(p.payment_date)}</td>
                <td>{p.amount_foreign ?? "—"}</td>
                <td>
                  {isPlannedPayment(p) ? (
                    <Button type="button" variant="secondary" onClick={() => liquidatePayment(p)}>
                      Liquidar
                    </Button>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}

// ── Descontos ──────────────────────────────────────────────────────────────

export function DiscountsPanel({ scope }: { scope: Scope }) {
  const toast = useToast();
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [importations, setImportations] = useState<Importation[]>([]);
  const [selectedImp, setSelectedImp] = useState(scope.importationId ? String(scope.importationId) : "");
  const [invoices, setInvoices] = useState<Invoice[]>(scope.invoices ?? []);
  const [items, setItems] = useState<ImportationItem[]>(scope.items ?? []);
  const [loading, setLoading] = useState(true);
  const [invoiceId, setInvoiceId] = useState("");
  const [itemId, setItemId] = useState("");
  const [dtype, setDtype] = useState("GLOBAL");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [docRef, setDocRef] = useState("");

  const impId = scope.mode === "importation" ? scope.importationId : Number(selectedImp);

  const reload = useCallback(async () => {
    if (!impId) {
      setDiscounts([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setDiscounts(await financeApi.listDiscounts({ importationId: impId }));
      if (scope.mode === "global") {
        setInvoices(await invoicesApi.list(impId));
        setItems(await importationsApi.items(impId));
      }
    } finally {
      setLoading(false);
    }
  }, [impId, scope.mode]);

  useEffect(() => {
    if (scope.mode === "global") {
      importationsApi.list().then(setImportations).catch(() => {});
    }
    if (scope.invoices) setInvoices(scope.invoices);
    if (scope.items) setItems(scope.items);
  }, [scope.mode, scope.invoices, scope.items]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const inv = invoices.find((i) => i.id === Number(invoiceId));
    if (!inv) return;
    try {
      await financeApi.createDiscount({
        invoice_id: Number(invoiceId),
        discount_type: dtype,
        amount: amount || null,
        currency: inv.currency,
        reason: reason || null,
        source_document_ref: docRef || null,
        importation_item_id: itemId ? Number(itemId) : null,
      });
      toast.success("Desconto registrado — reduz saldo da invoice");
      setAmount("");
      setReason("");
      setDocRef("");
      await reload();
      await scope.onReload?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao registrar desconto");
    }
  }

  const invoiceLabel = (id: number) => invoices.find((i) => i.id === id)?.invoice_number ?? String(id);

  return (
    <section className="finance-panel">
      <InfoBanner>
        Desconto reduz o saldo da invoice e o custo conforme regra atual.{" "}
        <strong>Não é crédito Heroes</strong> — crédito é compensação separada.
      </InfoBanner>
      {scope.mode === "global" && (
        <select value={selectedImp} onChange={(e) => setSelectedImp(e.target.value)} className="finance-select-imp">
          <option value="">Selecione a importação</option>
          {importations.map((i) => (
            <option key={i.id} value={i.id}>
              {i.po_number}
            </option>
          ))}
        </select>
      )}
      {!impId ? (
        <EmptyState title="Selecione uma importação" description="Descontos são vinculados a invoices." />
      ) : (
        <>
      <form className="inline-form" onSubmit={submit}>
        <select value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} required>
          <option value="">Fatura</option>
          {invoices.map((i) => (
            <option key={i.id} value={i.id}>
              {i.invoice_number}
            </option>
          ))}
        </select>
        <select value={dtype} onChange={(e) => setDtype(e.target.value)}>
          <option value="GLOBAL">Global (invoice)</option>
          <option value="ITEM">Por item</option>
        </select>
        {dtype === "ITEM" && items.length > 0 && (
          <select value={itemId} onChange={(e) => setItemId(e.target.value)} required>
            <option value="">Item</option>
            {items.map((it) => (
              <option key={it.id} value={it.id}>
                Item #{it.id}
              </option>
            ))}
          </select>
        )}
        <input placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input placeholder="Motivo" value={reason} onChange={(e) => setReason(e.target.value)} />
        <input placeholder="Documento / referência" value={docRef} onChange={(e) => setDocRef(e.target.value)} />
        <Button type="submit">Registrar desconto</Button>
      </form>
      {loading ? (
        <LoadingState label="Carregando descontos..." />
      ) : discounts.length === 0 ? (
        <EmptyState title="Nenhum desconto" description="Descontos aparecem aqui após registro." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Tipo</th>
              <th>Valor</th>
              <th>Motivo</th>
              <th>Documento</th>
            </tr>
          </thead>
          <tbody>
            {discounts.map((d) => (
              <tr key={d.id}>
                <td>{invoiceLabel(d.invoice_id)}</td>
                <td>{d.discount_type}</td>
                <td>
                  {d.amount ?? "—"} {d.currency}
                </td>
                <td>{d.reason ?? "—"}</td>
                <td>{d.source_document_ref ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
        </>
      )}
    </section>
  );
}

export function CreditsPanel({ scope }: { scope: Scope }) {
  const toast = useToast();
  const [credits, setCredits] = useState<Credit[]>([]);
  const [importations, setImportations] = useState<Importation[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>(scope.invoices ?? []);
  const [loading, setLoading] = useState(true);
  const [applyCreditId, setApplyCreditId] = useState<number | null>(null);
  const [applyAmount, setApplyAmount] = useState("");
  const [applyImp, setApplyImp] = useState(scope.importationId ? String(scope.importationId) : "");
  const [applyInv, setApplyInv] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const creds = await financeApi.listCredits(scope.supplierId);
      setCredits(creds);
      if (scope.mode === "global") {
        setImportations(await importationsApi.list());
      }
    } finally {
      setLoading(false);
    }
  }, [scope.supplierId, scope.mode]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (applyImp) {
      invoicesApi.list(Number(applyImp)).then(setInvoices);
    }
  }, [applyImp]);

  async function applyCredit(e: React.FormEvent) {
    e.preventDefault();
    if (!applyCreditId) return;
    try {
      await financeApi.applyCredit(applyCreditId, {
        importation_id: Number(applyImp),
        invoice_id: applyInv ? Number(applyInv) : null,
        amount: applyAmount,
      });
      toast.success("Crédito aplicado — não altera invoice automaticamente como desconto");
      setApplyCreditId(null);
      setApplyAmount("");
      await reload();
      await scope.onReload?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao aplicar crédito");
    }
  }

  const statusLabel = (s: string) => {
    if (s === "AVAILABLE") return "Disponível";
    if (s === "PARTIAL") return "Parcialmente usado";
    if (s === "USED") return "Usado";
    return s;
  };

  return (
    <section className="finance-panel">
      <InfoBanner>
        Crédito Heroes é compensação com saldo próprio.{" "}
        <strong>Não vira desconto automaticamente</strong> na invoice.
      </InfoBanner>
      {loading ? (
        <LoadingState label="Carregando créditos..." />
      ) : credits.length === 0 ? (
        <EmptyState title="Nenhum crédito" description="Créditos Heroes aparecem após registro ou importação." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Original</th>
              <th>Usado</th>
              <th>Disponível</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {credits.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>
                  {c.amount} {c.currency}
                </td>
                <td>{c.amount_used ?? "—"}</td>
                <td>{c.amount_available}</td>
                <td>
                  <Badge
                    tone={
                      c.status === "AVAILABLE"
                        ? "success"
                        : c.status === "USED"
                          ? "neutral"
                          : "warning"
                    }
                  >
                    {statusLabel(c.status)}
                  </Badge>
                </td>
                <td>
                  {c.status === "USED" ? (
                    <span className="meta">Crédito esgotado</span>
                  ) : Number(c.amount_available) > 0 ? (
                    <Button type="button" variant="secondary" onClick={() => setApplyCreditId(c.id)}>
                      Aplicar
                    </Button>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      {applyCreditId != null && (
        <form className="inline-form finance-apply-form" onSubmit={applyCredit}>
          <strong>Aplicar crédito #{applyCreditId}</strong>
          {scope.mode === "global" && (
            <select value={applyImp} onChange={(e) => setApplyImp(e.target.value)} required>
              <option value="">Importação</option>
              {importations.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.po_number}
                </option>
              ))}
            </select>
          )}
          <select value={applyInv} onChange={(e) => setApplyInv(e.target.value)}>
            <option value="">Invoice (opcional)</option>
            {invoices.map((i) => (
              <option key={i.id} value={i.id}>
                {i.invoice_number}
              </option>
            ))}
          </select>
          <input
            placeholder="Valor a usar"
            value={applyAmount}
            onChange={(e) => setApplyAmount(e.target.value)}
            required
          />
          <Button type="submit">Confirmar uso</Button>
          <Button type="button" variant="ghost" onClick={() => setApplyCreditId(null)}>
            Cancelar
          </Button>
        </form>
      )}
    </section>
  );
}

// ── Conta corrente BR ──────────────────────────────────────────────────────

export function BrazilAccountPanel({ scope }: { scope: Scope }) {
  const toast = useToast();
  const [accounts, setAccounts] = useState<BrazilAccount[]>([]);
  const [suppliers, setSuppliers] = useState<Array<{ id: number; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [supplierId, setSupplierId] = useState(scope.supplierId ? String(scope.supplierId) : "");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [finImpact, setFinImpact] = useState("");
  const [fiscalImpact, setFiscalImpact] = useState("");
  const [docRef, setDocRef] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setAccounts(await financeApi.listBrazilAccounts(scope.supplierId));
      if (!scope.supplierId) {
        const sups = await suppliersApi.list();
        setSuppliers(sups.map((s) => ({ id: s.id, name: s.name })));
      }
    } finally {
      setLoading(false);
    }
  }, [scope.supplierId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await financeApi.createBrazilAccount({
        supplier_id: Number(supplierId),
        description,
        amount,
        currency: "BRL",
        financial_impact_estimated: finImpact || null,
        fiscal_impact_estimated: fiscalImpact || null,
        origin_importation_id: scope.importationId ?? null,
        source_document_ref: docRef || null,
      });
      toast.success("Lançamento de conta corrente registrado");
      setDescription("");
      setAmount("");
      setFinImpact("");
      setFiscalImpact("");
      setDocRef("");
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao registrar");
    }
  }

  return (
    <section className="finance-panel">
      <InfoBanner>
        Conta corrente Brasil registra compensação local.{" "}
        <strong>Não é desconto automático</strong> na invoice. Política fiscal definitiva ainda pendente
        (F0-007) — impacto fiscal é estimado.
      </InfoBanner>
      <form className="inline-form" onSubmit={submit}>
        {!scope.supplierId && (
          <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} required>
            <option value="">Fornecedor</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        )}
        <input placeholder="Descrição" value={description} onChange={(e) => setDescription(e.target.value)} required />
        <input placeholder="Valor (BRL)" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        <input placeholder="Impacto financeiro est." value={finImpact} onChange={(e) => setFinImpact(e.target.value)} />
        <input placeholder="Impacto fiscal est." value={fiscalImpact} onChange={(e) => setFiscalImpact(e.target.value)} />
        <input placeholder="Documento / referência" value={docRef} onChange={(e) => setDocRef(e.target.value)} />
        <Button type="submit">Registrar lançamento</Button>
      </form>
      {loading ? (
        <LoadingState label="Carregando conta corrente..." />
      ) : accounts.length === 0 ? (
        <EmptyState title="Nenhum lançamento" description="Registre compensações Brasil aqui." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Descrição</th>
              <th>Valor</th>
              <th>Impacto fin.</th>
              <th>Impacto fiscal</th>
              <th>Disponível</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td>{a.description}</td>
                <td>
                  {a.amount} {a.currency}
                </td>
                <td>{a.financial_impact_estimated ?? "—"}</td>
                <td>{a.fiscal_impact_estimated ?? "—"}</td>
                <td>{a.amount_available}</td>
                <td>{a.status}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}

// ── Despesas Brasil ────────────────────────────────────────────────────────

export function ExpensesPanel({ scope }: { scope: Scope }) {
  const toast = useToast();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [importations, setImportations] = useState<Importation[]>([]);
  const [selectedImp, setSelectedImp] = useState(scope.importationId ? String(scope.importationId) : "");
  const [loading, setLoading] = useState(true);
  const [expType, setExpType] = useState("FREIGHT");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [docRef, setDocRef] = useState("");
  const [inLc, setInLc] = useState(true);

  const impId = scope.mode === "importation" ? scope.importationId : Number(selectedImp);

  useEffect(() => {
    if (scope.mode === "global") {
      importationsApi.list().then(setImportations).catch(() => {});
    }
  }, [scope.mode]);

  const reload = useCallback(async () => {
    if (!impId) {
      setExpenses([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setExpenses(await financeApi.listExpenses(impId));
    } finally {
      setLoading(false);
    }
  }, [impId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!impId) return;
    try {
      await financeApi.createExpense({
        importation_id: impId,
        expense_type: expType,
        description: description || null,
        amount: amount || null,
        currency: "BRL",
        source_document_ref: docRef || null,
        is_included_in_landed_cost: inLc,
      });
      toast.success("Despesa registrada");
      setDescription("");
      setAmount("");
      setDocRef("");
      await reload();
      await scope.onReload?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao registrar despesa");
    }
  }

  if (!impId) {
    return (
      <section className="finance-panel">
        {scope.mode === "global" && (
          <select value={selectedImp} onChange={(e) => setSelectedImp(e.target.value)} className="finance-select-imp">
            <option value="">Selecione a importação</option>
            {importations.map((i) => (
              <option key={i.id} value={i.id}>
                {i.po_number}
              </option>
            ))}
          </select>
        )}
        <EmptyState
          title="Selecione uma importação"
          description="Despesas Brasil são registradas por importação."
        />
      </section>
    );
  }

  return (
    <section className="finance-panel">
      {scope.mode === "global" && (
        <select value={selectedImp} onChange={(e) => setSelectedImp(e.target.value)} className="finance-select-imp">
          <option value="">Importação</option>
          {importations.map((i) => (
            <option key={i.id} value={i.id}>
              {i.po_number}
            </option>
          ))}
        </select>
      )}
      <form className="inline-form" onSubmit={submit}>
        <select value={expType} onChange={(e) => setExpType(e.target.value)}>
          {Object.entries(EXPENSE_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <input placeholder="Descrição" value={description} onChange={(e) => setDescription(e.target.value)} />
        <input placeholder="Valor (BRL)" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input
          placeholder={expType === "CUSTOMS_AGENT" ? "Evidência (obrigatório)" : "Evidência / NF"}
          value={docRef}
          onChange={(e) => setDocRef(e.target.value)}
          required={expType === "CUSTOMS_AGENT"}
        />
        <label className="inline-check">
          <input type="checkbox" checked={inLc} onChange={(e) => setInLc(e.target.checked)} />
          Entra no landed cost
        </label>
        <Button type="submit">Registrar despesa</Button>
      </form>
      {loading ? (
        <LoadingState label="Carregando despesas..." />
      ) : expenses.length === 0 ? (
        <EmptyState title="Nenhuma despesa" description="Frete, despachante e demais custos Brasil." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Descrição</th>
              <th>Valor</th>
              <th>Landed cost</th>
              <th>Evidência</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((ex) => (
              <tr key={ex.id}>
                <td>{EXPENSE_TYPE_LABELS[ex.expense_type] ?? ex.expense_type}</td>
                <td>{ex.description ?? "—"}</td>
                <td>
                  {ex.amount ?? "—"} {ex.currency}
                </td>
                <td>{ex.is_included_in_landed_cost ? "Sim" : "Não"}</td>
                <td>{ex.source_document_ref ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}

export function FinanceTabContent({ tab, scope }: { tab: FinanceTab; scope: Scope }) {
  switch (tab) {
    case "pagamentos":
      return <PaymentsPanel scope={scope} />;
    case "descontos":
      return <DiscountsPanel scope={scope} />;
    case "creditos":
      return <CreditsPanel scope={scope} />;
    case "conta-br":
      return <BrazilAccountPanel scope={scope} />;
    case "despesas":
      return <ExpensesPanel scope={scope} />;
    default:
      return null;
  }
}
