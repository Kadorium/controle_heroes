import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getPayable, type Payable } from "../billing/billingApi";
import { getSupplier } from "../catalog/catalogApi";
import { useSupplierSearch } from "../catalog/useCatalogSearch";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ConfirmationModal,
  ContextBreadcrumb,
  DateInput,
  ErrorState,
  FileUpload,
  FormField,
  LoadingState,
  MoneyDisplay,
  MoneyInput,
  Notice,
  PageHeader,
  SectionCard,
  SelectField,
  TextInput,
} from "../../ui";
import {
  canRegisterWithoutDoc,
  canWriteTreasury,
  registerPaymentJson,
  registerPaymentWithFile,
} from "./treasuryApi";

type Props = { user: User };

/** G02 — query contextual AP/Numerário → Novo pagamento (TARGET). */
export function PaymentCreatePage({ user }: Props) {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const paymentsReturn = buildReturnTo("/payments");
  const g02 = useMemo(
    () => ({
      supplier_id: params.get("supplier_id") ?? "",
      payable_id: params.get("payable_id") ?? "",
      amount: params.get("amount") ?? "",
      currency: params.get("currency") ?? "EUR",
      order_id: params.get("order_id") ?? "",
    }),
    [params],
  );
  const customsContext = Boolean(g02.payable_id && !g02.supplier_id);
  const hasG02 = Boolean(g02.supplier_id || g02.payable_id || g02.amount);

  const [payable, setPayable] = useState<Payable | null>(null);
  const [payableError, setPayableError] = useState<string | null>(null);
  const [payableLoading, setPayableLoading] = useState(customsContext);

  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [supplierId, setSupplierId] = useState(g02.supplier_id);
  const [supplierQ, setSupplierQ] = useState("");
  const searchedSuppliers = useSupplierSearch(supplierQ, { activeOnly: true, limit: 20 });
  const supplierOptions = useMemo(() => {
    const map = new Map<number, { id: number; name: string }>();
    for (const s of suppliers) map.set(s.id, s);
    for (const s of searchedSuppliers) map.set(s.id, { id: s.id, name: s.name });
    return [...map.values()];
  }, [suppliers, searchedSuppliers]);
  const [amount, setAmount] = useState(g02.amount || "1000");
  const [currency, setCurrency] = useState(g02.currency || "EUR");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [ref, setRef] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [withoutDoc, setWithoutDoc] = useState(false);
  const [withoutDocReason, setWithoutDocReason] = useState("DOC_OVERRIDE_UI");
  const [confirmWithoutDoc, setConfirmWithoutDoc] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const allowWithoutDoc = canRegisterWithoutDoc(user);

  useEffect(() => {
    if (!g02.supplier_id) return;
    void getSupplier(Number(g02.supplier_id))
      .then((s) => setSuppliers([{ id: s.id, name: s.name }]))
      .catch(() => undefined);
  }, [g02.supplier_id]);

  useEffect(() => {
    if (g02.supplier_id) setSupplierId(g02.supplier_id);
    if (g02.amount) setAmount(g02.amount);
    if (g02.currency) setCurrency(g02.currency);
  }, [g02.supplier_id, g02.amount, g02.currency]);

  useEffect(() => {
    if (!customsContext) return;
    const id = Number(g02.payable_id);
    setPayableLoading(true);
    setPayableError(null);
    void getPayable(id)
      .then((p) => {
        setPayable(p);
        setAmount(p.balance);
        setCurrency(p.currency);
      })
      .catch((e) => setPayableError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setPayableLoading(false));
  }, [customsContext, g02.payable_id]);

  if (!canWriteTreasury(user)) return <ErrorState message="Sem permissão para registrar pagamentos." />;
  if (customsContext && payableLoading) return <LoadingState message="Carregando obrigação…" />;
  if (customsContext && payableError) return <ErrorState message={payableError} />;

  const supplierName =
    suppliers.find((s) => String(s.id) === String(supplierId))?.name ||
    supplierOptions.find((s) => String(s.id) === String(supplierId))?.name ||
    (g02.supplier_id && suppliers.length === 0 ? "Fornecedor" : null);

  const customsBlocked =
    customsContext &&
    payable &&
    (payable.source_type !== "CUSTOMS_FUNDING" || payable.currency !== "BRL");

  function afterSave(pay: { id: number }) {
    const q = new URLSearchParams();
    if (g02.payable_id) q.set("payable_id", g02.payable_id);
    const suffix = q.toString() ? `?${q.toString()}` : "";
    nav(`/payments/${pay.id}${suffix}`, { state: { justRegistered: true } });
  }

  async function doRegister(opts: { withoutDocument: boolean }) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      if (opts.withoutDocument) {
        if (!withoutDocReason.trim()) throw new Error("Informe o motivo do override sem documento");
        const body = customsContext
          ? {
              payable_id: Number(g02.payable_id),
              amount,
              payment_date: date,
              external_reference: ref || undefined,
              register_without_document: true,
              reason_code: withoutDocReason.trim(),
            }
          : {
              supplier_id: Number(supplierId),
              amount,
              currency: currency || "EUR",
              payment_date: date,
              external_reference: ref || undefined,
              register_without_document: true,
              reason_code: withoutDocReason.trim(),
              order_id: g02.order_id ? Number(g02.order_id) : undefined,
            };
        const pay = await registerPaymentJson(body);
        afterSave(pay);
        return;
      }
      if (!file) throw new Error("Anexe o comprovante");
      const form = new FormData();
      form.append("amount", amount);
      form.append("payment_date", date);
      if (ref) form.append("external_reference", ref);
      form.append("file", file);
      if (customsContext) {
        form.append("payable_id", g02.payable_id);
      } else {
        form.append("supplier_id", supplierId);
        form.append("currency", currency || "EUR");
        if (g02.order_id) form.append("order_id", g02.order_id);
      }
      const pay = await registerPaymentWithFile(form);
      afterSave(pay);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    } finally {
      setBusy(false);
      setConfirmWithoutDoc(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (withoutDoc && allowWithoutDoc) {
      setConfirmWithoutDoc(true);
      return;
    }
    await doRegister({ withoutDocument: false });
  }

  return (
    <section className="panel dense page-form" data-testid="payment-create">
      <ContextBreadcrumb
        items={[
          { label: "Financeiro", to: paymentsReturn },
          { label: "Pagamentos realizados", to: paymentsReturn },
          { label: "Novo pagamento" },
        ]}
      />
      <PageHeader
        title="Novo pagamento"
        subtitle="Registrar pagamento — a alocação às obrigações é um passo separado"
        actions={
          <Link className="ui-button ui-button--secondary" to={paymentsReturn}>
            Voltar
          </Link>
        }
      />
      {customsContext && payable ? (
        <Notice tone="info" data-testid="g02-banner">
          Contexto do Numerário: {payable.payee_display_name || "favorecido"} · finalidade
          liquidação · valor sugerido{" "}
          <MoneyDisplay amount={payable.balance} currency={payable.currency} />. A obrigação
          permanece intacta até confirmar a aplicação.
        </Notice>
      ) : hasG02 ? (
        <Notice tone="info" data-testid="g02-banner">
          Contexto da fila: {supplierName || "fornecedor"}
          {g02.payable_id ? " · obrigação selecionada" : ""}
          {g02.order_id ? " · pedido vinculado" : ""} · valor sugerido{" "}
          <MoneyDisplay amount={g02.amount || null} currency={g02.currency || "EUR"} />. Revisar
          antes de registrar — a obrigação permanece intacta até a alocação.
        </Notice>
      ) : (
        <Notice tone="info" data-testid="g02-manual-banner">
          Sem contexto da fila. Preencha manualmente.
        </Notice>
      )}
      {customsBlocked ? (
        <Notice tone="warning" data-testid="customs-fx-blocked">
          Numerário em moeda estrangeira não é liquidável nesta versão.
        </Notice>
      ) : null}
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      <SectionCard title="Dados do pagamento">
        <form className="stack" onSubmit={(e) => void onSubmit(e)}>
          <div className="form-grid">
            {customsContext && payable ? (
              <>
                <FormField label="Favorecido">
                  <TextInput
                    data-testid="pay-payee-readonly"
                    value={payable.payee_display_name || ""}
                    readOnly
                  />
                </FormField>
                <FormField label="CNPJ / tax ID">
                  <TextInput
                    data-testid="pay-tax-readonly"
                    value={payable.payee_tax_id || "—"}
                    readOnly
                  />
                </FormField>
                <FormField label="Finalidade">
                  <TextInput data-testid="pay-purpose-readonly" value="Liquidação" readOnly />
                </FormField>
                <FormField label="Moeda">
                  <TextInput data-testid="pay-currency" value={payable.currency} readOnly />
                </FormField>
              </>
            ) : (
              <>
                <FormField label="Fornecedor" htmlFor="pay-supplier-q">
                  <TextInput
                    id="pay-supplier-q"
                    data-testid="pay-supplier-search"
                    placeholder="Buscar fornecedor…"
                    value={supplierQ}
                    onChange={(e) => setSupplierQ(e.target.value)}
                  />
                </FormField>
                <FormField label="Fornecedor" htmlFor="pay-supplier" required>
                  <SelectField
                    id="pay-supplier"
                    data-testid="pay-supplier"
                    required
                    value={supplierId}
                    onChange={(e) => {
                      const next = e.target.value;
                      setSupplierId(next);
                      const picked = supplierOptions.find((s) => String(s.id) === next);
                      if (picked) {
                        setSuppliers((prev) =>
                          prev.some((p) => p.id === picked.id) ? prev : [...prev, picked],
                        );
                      }
                    }}
                    options={[
                      { value: "", label: "Selecione" },
                      ...supplierOptions.map((s) => ({ value: String(s.id), label: s.name })),
                    ]}
                  />
                </FormField>
                <FormField label="Moeda" htmlFor="pay-currency">
                  <TextInput
                    id="pay-currency"
                    data-testid="pay-currency"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  />
                </FormField>
              </>
            )}
            <FormField label="Data" htmlFor="pay-date" required>
              <DateInput
                id="pay-date"
                data-testid="pay-date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </FormField>
            <FormField label="Valor" htmlFor="pay-amount" required>
              <MoneyInput
                id="pay-amount"
                data-testid="pay-amount"
                currency={customsContext && payable ? payable.currency : currency}
                value={amount}
                onValueChange={setAmount}
                required
              />
            </FormField>
            <FormField label="Referência" htmlFor="pay-ref">
              <TextInput
                id="pay-ref"
                data-testid="pay-ref"
                value={ref}
                onChange={(e) => setRef(e.target.value)}
              />
            </FormField>
          </div>
          {allowWithoutDoc ? (
            <div className="stack">
              <label className="stack-row">
                <input
                  type="checkbox"
                  data-testid="register-without-doc"
                  checked={withoutDoc}
                  onChange={(e) => setWithoutDoc(e.target.checked)}
                />
                Registrar sem documento (requer permissão)
              </label>
              {withoutDoc ? (
                <FormField label="Motivo do override" htmlFor="pay-without-reason" required>
                  <TextInput
                    id="pay-without-reason"
                    data-testid="pay-without-reason"
                    value={withoutDocReason}
                    onChange={(e) => setWithoutDocReason(e.target.value)}
                  />
                </FormField>
              ) : null}
            </div>
          ) : null}
          {!withoutDoc ? (
            <FormField label="Comprovante" required>
              <FileUpload
                data-testid="pay-doc"
                fileName={file?.name}
                onFileChange={setFile}
                label="Anexar comprovante"
              />
            </FormField>
          ) : null}
          <Button type="submit" data-testid="save-payment" busy={busy} disabled={Boolean(customsBlocked)}>
            Registrar
          </Button>
        </form>
      </SectionCard>

      <ConfirmationModal
        open={confirmWithoutDoc}
        title="Registrar sem documento"
        confirmLabel="Confirmar registro"
        busy={busy}
        onCancel={() => setConfirmWithoutDoc(false)}
        onConfirm={() => void doRegister({ withoutDocument: true })}
      >
        <p>
          Override com permissão <code>treasury:register_without_doc</code>. Motivo:{" "}
          {withoutDocReason.trim() || "—"}.
        </p>
      </ConfirmationModal>
    </section>
  );
}
