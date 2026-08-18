import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  Button,
  ConfirmationModal,
  DateInput,
  DocumentActions,
  EmptyState,
  FileUpload,
  FormField,
  MoneyDisplay,
  MoneyInput,
  Notice,
  RateInput,
  SectionCard,
  TextInput,
  formatDateOnly,
  formatMoney,
  formatRate,
  parseMoneyInput,
} from "../../ui";
import { canCancelTreasury, canWriteTreasury } from "./treasuryApi";
import { canWriteFx, getQuoteForDate } from "./fxApi";
import {
  cancelOrderAdvance,
  listOrderAdvances,
  registerOrderAdvanceJson,
  registerOrderAdvanceWithFile,
  type OrderAdvance,
  type OrderAdvancesResponse,
} from "./advanceApi";

type Props = {
  user: User;
  orderId: number;
  orderCurrency: string;
  orderStatus: string;
};

type BrlSuggestion = {
  asOf: string;
  rate: string;
  brl: string;
  source: string | null;
};

function canFxWithoutDoc(user: User) {
  return user.role === "admin" || user.permissions.includes("treasury:fx_without_document");
}

/** Painel de adiantamento (crédito) — NÃO cria Payable. */
export function OrderAdvancesPanel({ user, orderId, orderCurrency, orderStatus }: Props) {
  const canWrite = canWriteTreasury(user) && canWriteFx(user);
  const canCancel = canCancelTreasury(user);
  const canWithoutDoc = canFxWithoutDoc(user);
  const readonly = orderStatus === "CANCELLED" || !canWrite;

  const [data, setData] = useState<OrderAdvancesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState("");
  const [brlAmount, setBrlAmount] = useState("");
  const [paymentDate, setPaymentDate] = useState("");
  const [executionDate, setExecutionDate] = useState("");
  const [externalRef, setExternalRef] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fxUploadKey, setFxUploadKey] = useState(0);
  const [brlSuggestion, setBrlSuggestion] = useState<BrlSuggestion | null>(null);
  const [brlSuggestionMissing, setBrlSuggestionMissing] = useState<string | null>(null);
  const [brlSuggestionApplied, setBrlSuggestionApplied] = useState(false);

  const [cancelTarget, setCancelTarget] = useState<OrderAdvance | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  function resetAdvanceForm() {
    setAmount("");
    setRate("");
    setBrlAmount("");
    setPaymentDate("");
    setExecutionDate("");
    setExternalRef("");
    setFile(null);
    setFxUploadKey((k) => k + 1);
    setBrlSuggestion(null);
    setBrlSuggestionMissing(null);
    setBrlSuggestionApplied(false);
  }

  const reload = useCallback(async () => {
    try {
      const row = await listOrderAdvances(orderId);
      setData(row);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }, [orderId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  // V3 A4 — sugestão de BRL a partir de FxMarketQuote do dia (não autofill silencioso).
  useEffect(() => {
    const eur = parseMoneyInput(amount);
    if (!eur || Number(eur) <= 0 || !executionDate) {
      setBrlSuggestion(null);
      setBrlSuggestionMissing(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const q = await getQuoteForDate(executionDate, orderCurrency || "EUR");
        if (cancelled) return;
        if (!q.rate || q.status === "missing") {
          setBrlSuggestion(null);
          setBrlSuggestionMissing(
            `Sem cotação de mercado para ${formatDateOnly(executionDate)} — informe o BRL do extrato ou a taxa.`,
          );
          return;
        }
        const brl = (Number(eur) * Number(q.rate)).toFixed(2);
        setBrlSuggestionMissing(null);
        setBrlSuggestion({
          asOf: executionDate,
          rate: q.rate,
          brl,
          source: q.source,
        });
      } catch {
        if (!cancelled) {
          setBrlSuggestion(null);
          setBrlSuggestionMissing(
            `Não foi possível obter cotação para ${formatDateOnly(executionDate)}.`,
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [amount, executionDate, orderCurrency]);

  const previewBrl = (() => {
    const eur = parseMoneyInput(amount);
    const r = parseMoneyInput(rate);
    if (!eur || !r || brlAmount.trim()) return null;
    return (Number(eur) * Number(r)).toFixed(2);
  })();

  const previewRate = (() => {
    const eur = parseMoneyInput(amount);
    const brl = parseMoneyInput(brlAmount);
    if (!eur || !brl || Number(eur) <= 0) return null;
    return (Number(brl) / Number(eur)).toFixed(6);
  })();

  async function onSubmit() {
    const eur = parseMoneyInput(amount);
    if (!eur || Number(eur) <= 0) {
      setError("Informe o valor em EUR");
      return;
    }
    if (!paymentDate || !executionDate) {
      setError("Informe data do pagamento e data da execução de câmbio");
      return;
    }
    const rateApi = parseMoneyInput(rate);
    const brlApi = parseMoneyInput(brlAmount);
    if (!rateApi && !brlApi) {
      setError("Informe a taxa ou o valor em BRL (extrato)");
      return;
    }
    if (!file && !canWithoutDoc) {
      setError("Anexe o PDF de câmbio ou use perfil autorizado sem documento");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      if (file) {
        const form = new FormData();
        form.append("amount", eur);
        form.append("payment_date", paymentDate);
        form.append("execution_date", executionDate);
        if (rateApi) form.append("rate", rateApi);
        if (brlApi) form.append("brl_amount", brlApi);
        form.append("currency", orderCurrency);
        if (externalRef.trim()) form.append("external_reference", externalRef.trim());
        form.append("file", file);
        await registerOrderAdvanceWithFile(orderId, form);
      } else {
        await registerOrderAdvanceJson(orderId, {
          amount: eur,
          payment_date: paymentDate,
          execution_date: executionDate,
          rate: rateApi || undefined,
          brl_amount: brlApi || undefined,
          currency: orderCurrency,
          external_reference: externalRef.trim() || undefined,
          register_without_fx_document: true,
          reason_code: "ORDER_ADVANCE",
        });
      }
      resetAdvanceForm();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao registrar");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmCancel() {
    if (!cancelTarget || busy) return;
    const reason = cancelReason.trim();
    if (!reason) {
      setError("Informe o motivo do cancelamento");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await cancelOrderAdvance(orderId, cancelTarget.payment_id, {
        expected_version: cancelTarget.version,
        reason,
      });
      setData(next);
      setCancelTarget(null);
      setCancelReason("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao cancelar");
    } finally {
      setBusy(false);
    }
  }

  const cons = data?.consolidated;

  return (
    <SectionCard title="Adiantamentos (crédito)" data-testid="order-advances">
      <Notice tone="info" data-testid="order-advances-credit-notice">
        Adiantamento é crédito (dinheiro já saiu). Não gera título em Contas a pagar.
      </Notice>

      {error ? (
        <Notice tone="danger" data-testid="order-advances-error">
          {error}
        </Notice>
      ) : null}

      {cons && cons.count > 0 ? (
        <div className="summary-grid" data-testid="order-advances-consolidated">
          <div>
            <span className="muted">Total adiantado (EUR)</span>
            <div data-testid="adv-total-eur">
              <MoneyDisplay amount={cons.total_eur} currency={orderCurrency} />
            </div>
          </div>
          <div>
            <span className="muted">Total adiantado (BRL)</span>
            <div data-testid="adv-total-brl">
              <MoneyDisplay amount={cons.total_brl} currency="BRL" />
            </div>
          </div>
          <div>
            <span className="muted">Câmbio médio ponderado</span>
            <div data-testid="adv-weighted-rate">
              {cons.weighted_avg_rate ? formatRate(cons.weighted_avg_rate, 6) : "—"}
            </div>
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              Ponderado = BRL ÷ EUR. O custo real é a soma em BRL, não média × total.
            </p>
          </div>
        </div>
      ) : (
        <EmptyState message="Nenhum adiantamento registrado" />
      )}

      {(data?.advances?.length ?? 0) > 0 ? (
        <ul className="plain-list" data-testid="order-advances-list">
          {data!.advances.map((a) => (
            <li key={a.payment_id} data-testid={`order-advance-${a.payment_id}`}>
              <div className="stack-row" style={{ alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <span>
                  {formatDateOnly(a.payment_date)} · {formatMoney(a.amount, a.currency)}
                  {a.brl_amount ? ` → ${formatMoney(a.brl_amount, "BRL")}` : ""}
                  {a.rate ? ` · taxa ${formatRate(a.rate, 6)}` : ""}
                  {a.execution_date && a.execution_date !== a.payment_date
                    ? ` · câmbio em ${formatDateOnly(a.execution_date)}`
                    : ""}
                </span>
                {a.fx_documents?.map((d) => (
                  <DocumentActions
                    key={d.id}
                    documentId={d.id}
                    filename={d.original_filename}
                    data-testid={`adv-fx-doc-${d.id}`}
                  />
                ))}
                {canCancel && orderStatus !== "CANCELLED" ? (
                  <Button
                    type="button"
                    variant="secondary"
                    data-testid={`adv-cancel-${a.payment_id}`}
                    disabled={busy}
                    onClick={() => {
                      setCancelTarget(a);
                      setCancelReason("");
                      setError(null);
                    }}
                  >
                    Cancelar
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {(data?.settlements?.length ?? 0) > 0 ? (
        <div data-testid="order-settlements">
          <h3 className="section-subtitle">Pagamentos de saldo deste pedido</h3>
          <p className="muted">
            Quitação de obrigação. Não entra no total adiantado.
          </p>
          <ul className="plain-list" data-testid="order-settlements-list">
            {data!.settlements!.map((s) => (
              <li key={s.payment_id} data-testid={`order-settlement-${s.payment_id}`}>
                {formatDateOnly(s.payment_date)} · {formatMoney(s.amount, s.currency)}
                {s.brl_amount ? ` → ${formatMoney(s.brl_amount, "BRL")}` : ""}
                {s.rate ? ` · taxa ${formatRate(s.rate, 6)}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!readonly ? (
        <div className="form-grid" data-testid="order-advances-form">
          <FormField label="Valor (EUR)">
            <MoneyInput
              data-testid="adv-amount"
              value={amount}
              onValueChange={setAmount}
            />
          </FormField>
          <FormField label="Taxa EUR→BRL (opcional se informar BRL)">
            <RateInput
              data-testid="adv-rate"
              value={rate}
              onValueChange={setRate}
              fractionDigits={6}
            />
          </FormField>
          <FormField label="Valor BRL do extrato (opcional se informar taxa)">
            <MoneyInput
              data-testid="adv-brl"
              value={brlAmount}
              onValueChange={(v) => {
                setBrlAmount(v);
                setBrlSuggestionApplied(false);
              }}
            />
          </FormField>
          <FormField label="Data do pagamento">
            <DateInput
              data-testid="adv-payment-date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
            />
          </FormField>
          <FormField label="Data da execução de câmbio">
            <DateInput
              data-testid="adv-execution-date"
              value={executionDate}
              onChange={(e) => {
                setExecutionDate(e.target.value);
                setBrlSuggestionApplied(false);
              }}
            />
          </FormField>
          <FormField label="Referência (opcional)">
            <TextInput
              data-testid="adv-external-ref"
              value={externalRef}
              onChange={(e) => setExternalRef(e.target.value)}
            />
          </FormField>
          {brlSuggestion ? (
            <Notice tone="warning" data-testid="adv-brl-suggestion">
              <strong>Sugestão do sistema (não é o extrato).</strong> Cotação{" "}
              {formatDateOnly(brlSuggestion.asOf)}
              {brlSuggestion.source ? ` · ${brlSuggestion.source}` : ""}: taxa{" "}
              {formatRate(brlSuggestion.rate, 6)} → {formatMoney(brlSuggestion.brl, "BRL")}. O valor
              verdadeiro é o do seu extrato bancário.
              <div className="stack-row" style={{ marginTop: "0.5rem", gap: "0.5rem" }}>
                <Button
                  type="button"
                  variant="secondary"
                  data-testid="adv-brl-suggestion-apply"
                  disabled={busy}
                  onClick={() => {
                    setBrlAmount(brlSuggestion.brl);
                    setRate("");
                    setBrlSuggestionApplied(true);
                  }}
                >
                  Preencher BRL com a sugestão
                </Button>
                {brlSuggestionApplied ? (
                  <span className="muted" data-testid="adv-brl-suggestion-applied">
                    Sugestão aplicada — confira e sobrescreva se o extrato for diferente.
                  </span>
                ) : null}
              </div>
            </Notice>
          ) : null}
          {brlSuggestionMissing ? (
            <Notice tone="info" data-testid="adv-brl-suggestion-missing">
              {brlSuggestionMissing}
            </Notice>
          ) : null}
          {previewBrl ? (
            <p className="muted" data-testid="adv-preview-brl">
              BRL derivado da taxa: {formatMoney(previewBrl, "BRL")} (pode sobrescrever com o
              extrato)
            </p>
          ) : null}
          {previewRate && brlAmount.trim() ? (
            <p className="muted" data-testid="adv-preview-rate">
              Taxa derivada de EUR+BRL: {formatRate(previewRate, 6)}
            </p>
          ) : null}
          <div className="order-advance-fx-attach" data-testid="adv-fx-attach">
            <p className="order-advance-fx-attach-title">
              Comprovante de câmbio deste adiantamento
            </p>
            <p className="muted" data-testid="adv-fx-attach-hint">
              PDF do fechamento desta transferência. Não use o anexo de Documentos do
              pedido.
            </p>
            <FileUpload
              key={fxUploadKey}
              data-testid="adv-fx-upload"
              name="advance-fx-document"
              accept="application/pdf,.pdf"
              label="Anexar PDF de câmbio deste adiantamento"
              fileName={file?.name ?? null}
              disabled={busy}
              onFileChange={(f) => setFile(f)}
            />
          </div>
          <Button
            data-testid="adv-submit"
            disabled={busy}
            onClick={() => void onSubmit()}
          >
            Registrar adiantamento
          </Button>
        </div>
      ) : null}

      <ConfirmationModal
        open={cancelTarget != null}
        title="Cancelar adiantamento"
        confirmLabel="Cancelar adiantamento"
        busy={busy}
        initialFocusSelector="#adv-cancel-reason"
        onCancel={() => {
          setCancelTarget(null);
          setCancelReason("");
        }}
        onConfirm={() => void onConfirmCancel()}
      >
        <p data-testid="adv-cancel-confirm-copy">
          Cancelar este adiantamento? O valor sai do consolidado.
        </p>
        {cancelTarget ? (
          <p className="muted">
            {formatMoney(cancelTarget.amount, cancelTarget.currency)}
            {cancelTarget.brl_amount
              ? ` → ${formatMoney(cancelTarget.brl_amount, "BRL")}`
              : ""}
            {cancelTarget.rate ? ` · taxa ${formatRate(cancelTarget.rate, 6)}` : ""}
          </p>
        ) : null}
        <FormField label="Motivo (obrigatório)" htmlFor="adv-cancel-reason">
          <TextInput
            id="adv-cancel-reason"
            data-testid="adv-cancel-reason"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder="Ex.: taxa digitada errada — era 6,02"
          />
        </FormField>
      </ConfirmationModal>
    </SectionCard>
  );
}
