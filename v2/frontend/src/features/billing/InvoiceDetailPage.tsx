import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  cancelInvoice,
  createInvoice,
  getInvoice,
  issueInvoice,
  listOrderInvoices,
  replaceItems,
  setTerms,
  updateInvoice,
  uploadInvoiceDocument,
  invoicedQuantities,
  type Invoice,
  type InvoiceListItem,
  type OrderQtyRow,
} from "./billingApi";
import {
  canIssueBilling,
  canIssueWithoutDoc,
  canWriteBilling,
  lineAmounts,
  previewPercentPayables,
} from "./invoiceMath";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ConfirmationModal,
  ContextBreadcrumb,
  DateInput,
  DocumentActions,
  ErrorState,
  FileUpload,
  FormField,
  LoadingState,
  MoneyDisplay,
  MoneyInput,
  Notice,
  OperationalTable,
  PageHeader,
  RowLink,
  SectionCard,
  SelectField,
  StatusBadge,
  TextInput,
  compactQuantityWire,
  discountTypeLabel,
  formatDateOnly,
  formatQuantity,
  invoiceTypeLabel,
} from "../../ui";

type Props = { user: User };

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function OrderInvoicesPanel({ user, orderId, orderStatus }: Props & { orderId: number; orderStatus: string }) {
  const nav = useNavigate();
  const [rows, setRows] = useState<InvoiceListItem[]>([]);
  const [qtys, setQtys] = useState<OrderQtyRow[]>([]);
  const [number, setNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(todayIso());
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
      const inv = await createInvoice(orderId, {
        invoice_number: number.trim(),
        invoice_date: invoiceDate || undefined,
      });
      nav(`/invoices/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Faturas" data-testid="order-invoices">
      {error ? (
        <Notice tone="danger" data-testid="order-invoices-error">
          {error}
        </Notice>
      ) : null}

      {qtys.length > 0 ? (
        <OperationalTable density="standard" data-testid="invoiced-qty">
          <thead>
            <tr>
              <th>Item</th>
              <th className="num">Pedida</th>
              <th className="num">Faturada</th>
              <th className="num">Disponível</th>
            </tr>
          </thead>
          <tbody>
            {qtys.map((q) => (
              <tr key={q.order_item_id}>
                <td>#{q.order_item_id}</td>
                <td className="num">{formatQuantity(q.ordered_qty)}</td>
                <td className="num">{formatQuantity(q.issued_qty)}</td>
                <td className="num">{formatQuantity(q.available_qty)}</td>
              </tr>
            ))}
          </tbody>
        </OperationalTable>
      ) : null}

      {rows.length === 0 ? (
        <p className="muted">Nenhuma fatura</p>
      ) : (
        <OperationalTable density="standard">
          <thead>
            <tr>
              <th>Número</th>
              <th>Status</th>
              <th className="num">Líquido</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <Link to={`/invoices/${r.id}`}>{r.invoice_number}</Link>
                </td>
                <td>
                  <StatusBadge status={r.status} entity="invoice" />
                </td>
                <td className="num">
                  <MoneyDisplay amount={r.net_amount} currency={r.currency} />
                </td>
              </tr>
            ))}
          </tbody>
        </OperationalTable>
      )}

      {orderStatus === "CONFIRMED" && canWrite ? (
        <div className="stack-row form-inline">
          <TextInput
            data-testid="new-invoice-number"
            placeholder="Número da fatura"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
          />
          <DateInput
            data-testid="new-invoice-date"
            value={invoiceDate}
            onChange={(e) => setInvoiceDate(e.target.value)}
            aria-label="Data da fatura"
          />
          <Button
            type="button"
            data-testid="create-invoice"
            busy={busy}
            disabled={!number.trim()}
            onClick={() => void onCreate()}
          >
            Criar fatura
          </Button>
        </div>
      ) : null}
    </SectionCard>
  );
}

export function InvoiceDetailPage({ user }: Props) {
  const { invoiceId } = useParams();
  const id = Number(invoiceId);
  const [inv, setInv] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formBusy, setFormBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [confirmIssue, setConfirmIssue] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [issueWithoutDoc, setIssueWithoutDoc] = useState(false);
  const [withoutDocReason, setWithoutDocReason] = useState("DOC_OVERRIDE_UI");
  const [termMode, setTermMode] = useState<"PERCENT" | "AMOUNT">("PERCENT");
  const [headerDate, setHeaderDate] = useState("");
  const [terms, setTermsLocal] = useState<{ due_date: string; percent: string; amount: string }[]>([
    { due_date: "", percent: "30", amount: "" },
    { due_date: "", percent: "70", amount: "" },
  ]);
  const invoicesReturn = buildReturnTo("/invoices");
  async function reload() {
    const data = await getInvoice(id);
    const items = (data.items ?? []).map((it) => ({
      ...it,
      quantity: compactQuantityWire(it.quantity),
    }));
    setInv({ ...data, items });
    setHeaderDate(data.invoice_date ?? "");
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

  if (error && !inv) return <ErrorState message={error} />;
  if (!inv) return <LoadingState message="Carregando fatura…" />;

  const readonly = inv.status !== "DRAFT";
  const canWrite = canWriteBilling(user) && !readonly;
  const canIssue = canIssueBilling(user) && inv.status === "DRAFT";
  const canWithoutDoc = canIssueWithoutDoc(user);
  const canCancelDraft = canWriteBilling(user) && inv.status === "DRAFT";
  const orderCode = (inv as Invoice & { order_code?: string | null }).order_code;

  async function saveItems() {
    if (!inv || formBusy) return;
    setFormBusy(true);
    setError(null);
    try {
      const next = await replaceItems(
        inv.id,
        inv.version,
        (inv.items ?? []).map((i) => ({
          order_item_id: i.order_item_id,
          quantity: i.quantity,
          unit_price_gross: i.unit_price_gross,
          unit: i.unit ?? null,
          discount_type: i.discount_type,
          discount_unit_amount: i.discount_unit_amount,
          discount_percent: i.discount_percent,
        })),
      );
      const items = (next.items ?? []).map((it) => ({
        ...it,
        quantity: compactQuantityWire(it.quantity),
      }));
      setInv({ ...next, items });
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          const fresh = await getInvoice(id);
          setInv((prev) =>
            prev
              ? { ...prev, version: fresh.version, status: fresh.status, blockers: fresh.blockers }
              : fresh,
          );
          setError(
            "Conflito de versão — revisão atualizada. Seus rascunhos locais de itens foram preservados; salve novamente.",
          );
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setFormBusy(false);
    }
  }

  async function saveTerms() {
    if (!inv || formBusy) return;
    setFormBusy(true);
    setError(null);
    try {
      const cleaned = terms.filter((t) =>
        termMode === "PERCENT"
          ? Boolean(t.due_date && t.percent.trim())
          : Boolean(t.due_date && t.amount.trim()),
      );
      if (!cleaned.length) {
        setError("Informe ao menos uma parcela com data e valor/%");
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
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          const fresh = await getInvoice(id);
          setInv((prev) =>
            prev
              ? { ...prev, version: fresh.version, status: fresh.status, blockers: fresh.blockers }
              : fresh,
          );
          setError(
            "Conflito de versão — revisão atualizada. Condições locais preservadas; salve novamente.",
          );
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setFormBusy(false);
    }
  }

  async function onUpload(file: File | null) {
    if (!file || !inv || uploadBusy) return;
    setUploadBusy(true);
    setError(null);
    try {
      await uploadInvoiceDocument(inv.id, file);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setUploadBusy(false);
    }
  }

  async function onIssue() {
    if (!inv || formBusy) return;
    if (issueWithoutDoc && !withoutDocReason.trim()) {
      setError("Informe o motivo do override sem documento");
      return;
    }
    if (uploadBusy) {
      setError("Aguarde o upload do documento");
      return;
    }
    setFormBusy(true);
    setError(null);
    try {
      const next = await issueInvoice(inv.id, inv.version, {
        issue_without_document: issueWithoutDoc,
        reason_code: issueWithoutDoc ? withoutDocReason.trim() : undefined,
      });
      setInv(next);
      setConfirmIssue(false);
      setIssueWithoutDoc(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setFormBusy(false);
    }
  }

  async function onCancelDraft() {
    if (!inv || formBusy) return;
    setFormBusy(true);
    setError(null);
    try {
      const next = await cancelInvoice(inv.id, inv.version, "INVOICE_CANCEL_UI");
      setInv(next);
      setConfirmCancel(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setFormBusy(false);
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

  const draftPayables = inv.payables_preview?.length
    ? inv.payables_preview
    : preview.map((a, i) => ({
        sequence: String(i + 1),
        amount: a,
        due_date: terms[i]?.due_date ?? "",
      }));

  return (
    <section className="panel dense page-detail detail-shell" data-testid="invoice-detail">
      <ContextBreadcrumb
        items={[
          { label: "Compras", to: invoicesReturn },
          { label: "Faturas", to: invoicesReturn },
          { label: inv.invoice_number },
        ]}
      />
      <PageHeader
        title={`Fatura ${inv.invoice_number}`}
        subtitle={inv.currency}
        actions={
          <div className="stack-row page-header-actions">
            <Link className="ui-button ui-button--secondary" to={invoicesReturn}>
              Voltar à fila
            </Link>
            {canCancelDraft ? (
              <Button
                type="button"
                variant="secondary"
                data-testid="cancel-invoice"
                busy={formBusy}
                onClick={() => setConfirmCancel(true)}
              >
                Cancelar rascunho
              </Button>
            ) : null}
          </div>
        }
      />

      <SectionCard title="Cabeçalho" data-testid="invoice-header">
        <div className="form-grid">
          <FormField label="Tipo documental">
            <span data-testid="invoice-type-label">{invoiceTypeLabel(inv.invoice_type)}</span>
          </FormField>
          <FormField label="Status">
            <StatusBadge status={inv.status} entity="invoice" />
          </FormField>
          <FormField label="Moeda">
            <span>{inv.currency}</span>
          </FormField>
          <FormField label="Pedido">
            {orderCode ? (
              <RowLink to={`/orders/${inv.order_id}`}>{orderCode}</RowLink>
            ) : (
              "—"
            )}
          </FormField>
          <FormField label="Data da fatura" htmlFor="invoice-date-edit" hint="dd/mm/aaaa">
            {canWrite ? (
              <div className="stack-row form-inline">
                <DateInput
                  id="invoice-date-edit"
                  data-testid="invoice-date-edit"
                  value={headerDate}
                  onChange={(e) => setHeaderDate(e.target.value)}
                  aria-label="Data da fatura"
                />
                <Button
                  type="button"
                  data-testid="save-invoice-date"
                  busy={formBusy}
                  onClick={() => {
                    void (async () => {
                      setFormBusy(true);
                      setError(null);
                      try {
                        const next = await updateInvoice(inv.id, {
                          expected_version: inv.version,
                          invoice_date: headerDate || null,
                        });
                        const items = (next.items ?? []).map((it) => ({
                          ...it,
                          quantity: compactQuantityWire(it.quantity),
                        }));
                        setInv({ ...next, items });
                        setHeaderDate(next.invoice_date ?? "");
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Erro");
                      } finally {
                        setFormBusy(false);
                      }
                    })();
                  }}
                >
                  Salvar data
                </Button>
              </div>
            ) : (
              <span data-testid="invoice-date-readonly">{formatDateOnly(inv.invoice_date)}</span>
            )}
          </FormField>
          <FormField label="Líquido">
            <span data-testid="invoice-net">
              <MoneyDisplay amount={inv.net_amount} currency={inv.currency} />
            </span>
          </FormField>
        </div>
      </SectionCard>

      {readonly ? (
        <Notice tone="info" data-testid="invoice-readonly">
          Fatura somente leitura.
        </Notice>
      ) : null}

      {error ? (
        <Notice tone="danger" data-testid="invoice-error">
          {error}
        </Notice>
      ) : null}

      {inv.blockers?.length ? (
        <Notice tone="warning" title="Pendências" data-testid="invoice-blockers">
          <ul className="notice-list">
            {inv.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </Notice>
      ) : null}

      <SectionCard
        title="Itens"
        actions={
          canWrite ? (
            <Button type="button" data-testid="save-items" busy={formBusy} onClick={() => void saveItems()}>
              Salvar itens
            </Button>
          ) : undefined
        }
      >
        {canWrite ? (
          <Notice tone="info" data-testid="invoice-unit-inheritance-hint">
            Unidade documental: herdada do pedido na criação; override explícito ao editar e salvar.
          </Notice>
        ) : null}
        <OperationalTable density="finance" className="invoice-items-table" data-testid="invoice-items-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th className="num">Qtd</th>
              <th>Un.</th>
              <th className="num">Preço bruto</th>
              <th>Desconto</th>
              <th className="num">Valor desc.</th>
              <th className="num">Bruto</th>
              <th className="num">Desc.</th>
              <th className="num">Líquido</th>
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
                  <td className="num">
                    {canWrite ? (
                      <TextInput
                        data-testid={`qty-${idx}`}
                        className="num"
                        value={item.quantity}
                        onChange={(e) => {
                          const items = [...(inv.items ?? [])];
                          items[idx] = { ...item, quantity: e.target.value };
                          setInv({ ...inv, items });
                        }}
                      />
                    ) : (
                      formatQuantity(item.quantity)
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <TextInput
                        data-testid={`unit-${idx}`}
                        value={item.unit ?? ""}
                        placeholder="PZ"
                        maxLength={16}
                        title="Unidade documental (snapshot). Em branco no create herda do pedido; override explícito ao salvar."
                        onChange={(e) => {
                          const items = [...(inv.items ?? [])];
                          items[idx] = { ...item, unit: e.target.value || null };
                          setInv({ ...inv, items });
                        }}
                      />
                    ) : (
                      <span data-testid={`invoice-item-unit-${idx}`}>{item.unit ?? "—"}</span>
                    )}
                  </td>
                  <td className="num">
                    {canWrite ? (
                      <MoneyInput
                        data-testid={`price-${idx}`}
                        currency={inv.currency}
                        value={item.unit_price_gross ?? ""}
                        onValueChange={(v) => {
                          const items = [...(inv.items ?? [])];
                          items[idx] = { ...item, unit_price_gross: v };
                          setInv({ ...inv, items });
                        }}
                      />
                    ) : (
                      <MoneyDisplay amount={item.unit_price_gross} currency={inv.currency} />
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <SelectField
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
                        options={[
                          { value: "", label: "(incompleto)" },
                          { value: "NONE", label: "Nenhum" },
                          { value: "UNIT_AMOUNT", label: "Valor/un" },
                          { value: "PERCENT", label: "%" },
                        ]}
                      />
                    ) : (
                      discountTypeLabel(item.discount_type)
                    )}
                  </td>
                  <td className="num">
                    {canWrite && item.discount_type === "UNIT_AMOUNT" ? (
                      <MoneyInput
                        data-testid={`discount-unit-${idx}`}
                        currency={inv.currency}
                        value={item.discount_unit_amount ?? ""}
                        onValueChange={(v) => {
                          const items = [...(inv.items ?? [])];
                          items[idx] = { ...item, discount_unit_amount: v };
                          setInv({ ...inv, items });
                        }}
                      />
                    ) : null}
                    {canWrite && item.discount_type === "PERCENT" ? (
                      <TextInput
                        data-testid={`discount-pct-${idx}`}
                        className="num"
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
                  <td className="num">
                    <MoneyDisplay amount={live.gross ?? item.line_gross_amount} currency={inv.currency} />
                  </td>
                  <td className="num">
                    <MoneyDisplay amount={live.discount ?? item.line_discount_amount} currency={inv.currency} />
                  </td>
                  <td className="num">
                    <MoneyDisplay amount={live.net ?? item.line_net_amount} currency={inv.currency} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </OperationalTable>
      </SectionCard>

      <SectionCard title="Documento">
        {inv.documents?.length ? (
          <OperationalTable density="standard">
            <thead>
              <tr>
                <th scope="col">Arquivo</th>
              </tr>
            </thead>
            <tbody>
              {inv.documents.map((d) => (
                <tr key={d.id}>
                  <td>
                    <DocumentActions
                      documentId={d.id}
                      filename={d.original_filename}
                      mimeType={d.mime_type}
                      data-testid={`invoice-doc-actions-${d.id}`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        ) : (
          <p className="muted">Nenhum documento anexado</p>
        )}
        {canWrite ? (
          <FileUpload
            data-testid="invoice-doc"
            label="Anexar documento"
            disabled={uploadBusy}
            onFileChange={(file) => void onUpload(file)}
          />
        ) : null}
      </SectionCard>

      <SectionCard
        title="Condições de pagamento"
        actions={
          canWrite ? (
            <Button type="button" data-testid="save-terms" busy={formBusy} onClick={() => void saveTerms()}>
              Salvar condições
            </Button>
          ) : undefined
        }
      >
        {canWrite ? (
          <div className="form-inline stack-row">
            <label className="field-label">
              Modo{" "}
              <SelectField
                data-testid="terms-mode"
                value={termMode}
                onChange={(e) => setTermMode(e.target.value as "PERCENT" | "AMOUNT")}
                options={[
                  { value: "PERCENT", label: "Percentual" },
                  { value: "AMOUNT", label: "Valor" },
                ]}
              />
            </label>
          </div>
        ) : (
          <p className="muted">
            Modo:{" "}
            {inv.terms_mode === "PERCENT"
              ? "Percentual"
              : inv.terms_mode === "AMOUNT"
                ? "Valor"
                : inv.terms_mode}
          </p>
        )}

        <OperationalTable density="standard">
          <thead>
            <tr>
              <th>Vencimento</th>
              <th className="num">{termMode === "PERCENT" ? "%" : "Valor"}</th>
              <th className="num">Prévia</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((t, idx) => (
              <tr key={idx}>
                <td>
                  {canWrite ? (
                    <DateInput
                      data-testid={`term-date-${idx}`}
                      value={t.due_date}
                      onChange={(e) => {
                        const next = [...terms];
                        next[idx] = { ...t, due_date: e.target.value };
                        setTermsLocal(next);
                      }}
                    />
                  ) : (
                    <span data-testid={`term-date-${idx}`}>{formatDateOnly(t.due_date)}</span>
                  )}
                </td>
                <td className="num">
                  {canWrite && termMode === "PERCENT" ? (
                    <TextInput
                      data-testid={`term-pct-${idx}`}
                      className="num"
                      value={t.percent}
                      placeholder="%"
                      onChange={(e) => {
                        const next = [...terms];
                        next[idx] = { ...t, percent: e.target.value };
                        setTermsLocal(next);
                      }}
                    />
                  ) : null}
                  {canWrite && termMode === "AMOUNT" ? (
                    <MoneyInput
                      data-testid={`term-amt-${idx}`}
                      currency={inv.currency}
                      value={t.amount}
                      onValueChange={(v) => {
                        const next = [...terms];
                        next[idx] = { ...t, amount: v };
                        setTermsLocal(next);
                      }}
                    />
                  ) : null}
                  {!canWrite && termMode === "PERCENT" ? (
                    <span data-testid={`term-pct-${idx}`}>{formatQuantity(t.percent)}%</span>
                  ) : null}
                  {!canWrite && termMode === "AMOUNT" ? (
                    <span data-testid={`term-amt-${idx}`}>
                      <MoneyDisplay amount={t.amount} currency={inv.currency} />
                    </span>
                  ) : null}
                </td>
                <td className="num" data-testid={`term-preview-${idx}`}>
                  {preview[idx] ? (
                    <MoneyDisplay amount={preview[idx]} currency={inv.currency} />
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </OperationalTable>
      </SectionCard>

      <SectionCard title="Obrigações">
        {inv.status === "DRAFT" ? (
          <div data-testid="payables-preview">
            {draftPayables.length === 0 ? (
              <p className="muted">Nenhuma obrigação prevista</p>
            ) : (
              <OperationalTable density="standard">
                <thead>
                  <tr>
                    <th>Parcela</th>
                    <th>Vencimento</th>
                    <th className="num">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {draftPayables.map((p, i) => (
                    <tr key={i}>
                      <td>{p.sequence}</td>
                      <td>{formatDateOnly(p.due_date)}</td>
                      <td className="num">
                        <MoneyDisplay amount={p.amount} currency={inv.currency} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </OperationalTable>
            )}
          </div>
        ) : (
          <div data-testid="payables-list">
            {(inv.payables ?? []).length === 0 ? (
              <p className="muted">Nenhuma obrigação</p>
            ) : (
              <OperationalTable density="standard">
                <thead>
                  <tr>
                    <th>Parcela</th>
                    <th>Vencimento</th>
                    <th className="num">Valor</th>
                    <th className="num">Saldo</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(inv.payables ?? []).map((p) => (
                    <tr key={p.id}>
                      <td>{p.sequence}</td>
                      <td>{formatDateOnly(p.due_date)}</td>
                      <td className="num">
                        <MoneyDisplay amount={p.amount} currency={inv.currency} />
                      </td>
                      <td className="num">
                        <MoneyDisplay amount={p.balance} currency={inv.currency} />
                      </td>
                      <td>
                        <StatusBadge status={p.status} entity="payable" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </OperationalTable>
            )}
          </div>
        )}
      </SectionCard>

      {canIssue ? (
        <div className="stack-row page-actions">
          <Button
            type="button"
            data-testid="issue-invoice"
            busy={formBusy}
            disabled={(inv.blockers?.length ?? 0) > 0 || uploadBusy}
            onClick={() => setConfirmIssue(true)}
          >
            Emitir
          </Button>
        </div>
      ) : null}

      {(inv.blockers?.length ?? 0) > 0 && canIssue ? (
        <Notice tone="warning" data-testid="issue-blocked-reason">
          Emitir bloqueado: {(inv.blockers ?? []).join("; ")}
        </Notice>
      ) : null}

      <ConfirmationModal
        open={confirmIssue}
        title="Emitir fatura"
        confirmLabel="Emitir"
        busy={formBusy}
        onCancel={() => {
          setConfirmIssue(false);
          setIssueWithoutDoc(false);
        }}
        onConfirm={() => void onIssue()}
      >
        <p>
          Após a emissão a fatura fica somente leitura e as obrigações são criadas. Confirma?
        </p>
        {canWithoutDoc ? (
          <div className="stack" style={{ marginTop: "0.75rem" }}>
            <label className="stack-row">
              <input
                type="checkbox"
                data-testid="issue-without-doc"
                checked={issueWithoutDoc}
                onChange={(e) => setIssueWithoutDoc(e.target.checked)}
              />
              Emitir sem documento (requer permissão)
            </label>
            {issueWithoutDoc ? (
              <FormField label="Motivo do override" htmlFor="issue-without-reason" required>
                <TextInput
                  id="issue-without-reason"
                  data-testid="issue-without-reason"
                  value={withoutDocReason}
                  onChange={(e) => setWithoutDocReason(e.target.value)}
                />
              </FormField>
            ) : null}
          </div>
        ) : null}
        {(inv.payables_preview?.length ?? 0) > 0 ? (
          <OperationalTable density="standard" data-testid="issue-preview-payables">
            <thead>
              <tr>
                <th>Parcela</th>
                <th>Vencimento</th>
                <th className="num">Valor</th>
              </tr>
            </thead>
            <tbody>
              {inv.payables_preview!.map((p, i) => (
                <tr key={i}>
                  <td>{p.sequence}</td>
                  <td>{formatDateOnly(p.due_date)}</td>
                  <td className="num">
                    <MoneyDisplay amount={p.amount} currency={inv.currency} />
                  </td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        ) : (
          <p className="muted">Prévia de obrigações conforme condições salvas.</p>
        )}
      </ConfirmationModal>

      <ConfirmationModal
        open={confirmCancel}
        title="Cancelar rascunho"
        confirmLabel="Cancelar fatura"
        busy={formBusy}
        onCancel={() => setConfirmCancel(false)}
        onConfirm={() => void onCancelDraft()}
      >
        <p>Somente faturas em DRAFT podem ser canceladas. ISSUED permanece imutável.</p>
      </ConfirmationModal>
    </section>
  );
}
