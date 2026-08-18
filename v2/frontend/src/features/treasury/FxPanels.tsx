
import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  Button,
  FileUpload,
  FormField,
  LoadingState,
  MoneyInput,
  Notice,
  RateInput,
  SectionCard,
  SelectField,
  SummaryGrid,
  TextInput,
  formatMoney,
  formatRate,
} from "../../ui";
import {
  canReadFx,
  canRefreshFxQuote,
  canWriteFx,
  getLatestQuote,
  getPayableFxView,
  getPaymentFxView,
  linkExecutionAllocation,
  completeValuation,
  postFxPlan,
  postManualQuote,
  refreshQuote,
  registerFxExecutionWithDoc,
  type PayableFxView,
  type PaymentFxView,
  type FxMarketQuote,
} from "./fxApi";

/** Strip no shell: refresh no mount + clique (Inc-4B UX). */
export function FxQuoteStrip({ user }: { user: User }) {
  const [quote, setQuote] = useState<FxMarketQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canRead = canReadFx(user);
  const canRefresh = canRefreshFxQuote(user);

  const load = useCallback(async () => {
    if (!canRead) return;
    try {
      const q = await getLatestQuote("EUR");
      setQuote(q);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }, [canRead]);

  const doRefresh = useCallback(async () => {
    if (!canRefresh) return;
    setBusy(true);
    setError(null);
    try {
      const q = await refreshQuote("EUR");
      setQuote(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha no refresh");
      await load();
    } finally {
      setBusy(false);
    }
  }, [canRefresh, load]);

  useEffect(() => {
    if (!canRefresh) {
      void load();
      return;
    }
    void doRefresh();
  }, [canRefresh, doRefresh, load]);

  if (!canRead) return null;

  const rateLabel = formatRate(quote?.rate ?? null, 4);
  const stale = quote?.stale ? " · desatualizado" : "";
  const src = quote?.source ? ` · ${quote.source}` : "";

  return (
    <button
      type="button"
      className="fx-quote-strip"
      data-testid="fx-quote-strip"
      disabled={busy || !canRefresh}
      title={error || "Clique para atualizar cotação EUR/BRL"}
      onClick={() => void doRefresh()}
    >
      EUR/BRL {rateLabel}
      {stale}
      {src}
      {error ? ` · ${error}` : ""}
    </button>
  );
}

function fxMoney(value: string | null | undefined, currency?: string) {
  return formatMoney(value, currency);
}

function fxRate(value: string | null | undefined) {
  return formatRate(value, 4);
}

export function PayableFxPanel({
  user,
  payableId,
  reloadToken = 0,
}: {
  user: User;
  payableId: number;
  reloadToken?: number;
}) {
  const [view, setView] = useState<PayableFxView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rate, setRate] = useState("6.00");
  const [kind, setKind] = useState("INITIAL");
  const [reason, setReason] = useState("");
  const [manualMkt, setManualMkt] = useState("6.25");
  const [busy, setBusy] = useState(false);

  async function reload() {
    setView(await getPayableFxView(payableId));
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [payableId, reloadToken]);

  if (!canReadFx(user)) return null;
  if (!view) return <LoadingState message="Carregando câmbio…" />;

  const marketStatusLabel =
    view.market.status === "fresh"
      ? "atualizada"
      : view.market.status === "stale"
        ? "desatualizada"
        : view.market.status;
  const marketStale = view.market.stale ? " · desatualizado" : "";

  return (
    <section className="fx-panel stack" data-testid="payable-fx-panel">
      <h2 className="section-card-title">Visões de câmbio</h2>
      {error ? (
        <Notice tone="danger">{error}</Notice>
      ) : null}
      <div className="fx-columns">
        <SectionCard title="Planejado">
          <SummaryGrid
            items={[
              { label: "Taxa original", value: fxRate(view.initial_planned_rate) },
              { label: "Projeção atual", value: fxRate(view.current_forecast_rate) },
              { label: "Saldo em moeda", value: fxMoney(view.open_foreign) },
              { label: "BRL projetado", value: fxMoney(view.projected_open_brl, "BRL") },
            ]}
          />
        </SectionCard>
        <SectionCard title="Mercado">
          <SummaryGrid
            items={[
              {
                label: `Cotação online (${marketStatusLabel}${marketStale})`,
                value: fxRate(view.market.rate),
              },
              { label: "BRL a mercado", value: fxMoney(view.market_open_brl, "BRL") },
              { label: "Online vs projeção", value: fxMoney(view.online_result_vs_current, "BRL") },
              { label: "Online vs original", value: fxMoney(view.online_result_vs_initial, "BRL") },
            ]}
          />
        </SectionCard>
        <SectionCard title="Executado e avaliação">
          <SummaryGrid
            items={[
              { label: "Custo BRL (soma dos câmbios)", value: fxMoney(view.cost_brl, "BRL") },
              { label: "BRL das valuations (P&L)", value: fxMoney(view.realized_brl, "BRL") },
              {
                label: "Resultado vs referência",
                value: fxMoney(view.realized_result_vs_reference, "BRL"),
              },
              {
                label: "Resultado vs original",
                value: fxMoney(view.realized_result_vs_initial, "BRL"),
              },
              { label: "Total vs projeção", value: fxMoney(view.total_vs_current, "BRL") },
              { label: "Total vs original", value: fxMoney(view.total_vs_initial, "BRL") },
            ]}
          />
        </SectionCard>
      </div>

      {canWriteFx(user) ? (
        <SectionCard title="Taxa projetada">
          <form
            className="fx-form"
            data-testid="fx-plan-form"
            onSubmit={(e) => {
              e.preventDefault();
              void (async () => {
                setBusy(true);
                setError(null);
                try {
                  await postFxPlan(payableId, {
                    kind,
                    rate,
                    effective_from: new Date().toISOString().slice(0, 10),
                    reason_code: kind === "INITIAL" ? undefined : reason || "MARKET_UPDATE",
                  });
                  await reload();
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Erro");
                } finally {
                  setBusy(false);
                }
              })();
            }}
          >
            <FormField label="Tipo" htmlFor="fx-plan-kind">
              <SelectField
                id="fx-plan-kind"
                data-testid="fx-plan-kind"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                options={[
                  { value: "INITIAL", label: "Inicial" },
                  { value: "REFORECAST", label: "Replanejar" },
                  { value: "CORRECTION", label: "Corrigir" },
                ]}
              />
            </FormField>
            <FormField label="Taxa" htmlFor="fx-plan-rate">
              <RateInput
                id="fx-plan-rate"
                data-testid="fx-plan-rate"
                value={rate}
                onValueChange={setRate}
                fractionDigits={4}
              />
            </FormField>
            {kind !== "INITIAL" ? (
              <FormField label="Motivo" htmlFor="fx-plan-reason">
                <TextInput
                  id="fx-plan-reason"
                  data-testid="fx-plan-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </FormField>
            ) : null}
            <Button type="submit" data-testid="fx-plan-save" busy={busy}>
              Salvar plano
            </Button>
          </form>
        </SectionCard>
      ) : null}

      {canWriteFx(user) ? (
        <SectionCard title="Cotação manual">
          <form
            className="fx-form"
            data-testid="fx-manual-quote-form"
            onSubmit={(e) => {
              e.preventDefault();
              void (async () => {
                setBusy(true);
                setError(null);
                try {
                  await postManualQuote(manualMkt);
                  await reload();
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Erro");
                } finally {
                  setBusy(false);
                }
              })();
            }}
          >
            <FormField label="Taxa de mercado" htmlFor="fx-manual-rate">
              <RateInput
                id="fx-manual-rate"
                data-testid="fx-manual-rate"
                value={manualMkt}
                onValueChange={setManualMkt}
                fractionDigits={4}
              />
            </FormField>
            <Button type="submit" data-testid="fx-manual-save" busy={busy}>
              Atualizar cotação
            </Button>
          </form>
        </SectionCard>
      ) : null}
    </section>
  );
}

export function PaymentFxPanel({ user, paymentId }: { user: User; paymentId: number }) {
  const [view, setView] = useState<PaymentFxView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [foreignAmt, setForeignAmt] = useState("");
  const [rate, setRate] = useState("6.20");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setView(await getPaymentFxView(paymentId));
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [paymentId]);

  if (!canReadFx(user)) return null;
  if (!view) return <LoadingState message="Carregando câmbio…" />;
  const fxView = view;

  async function onRegisterExec(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Anexe evidência cambial");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("foreign_amount", foreignAmt || fxView.amount);
      form.append("rate", rate);
      form.append("execution_date", new Date().toISOString().slice(0, 10));
      form.append("file", file);
      const ex = await registerFxExecutionWithDoc(paymentId, form);
      for (const a of fxView.allocations) {
        if (a.execution_links.length) continue;
        await linkExecutionAllocation({
          fx_execution_id: ex.id,
          payment_allocation_id: a.allocation_id,
        });
        await completeValuation(a.allocation_id);
      }
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Câmbio realizado" data-testid="payment-fx-panel">
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      {fxView.executions.length === 0 ? (
        <p className="muted" data-testid="fx-exec-list">
          Nenhuma execução registrada
        </p>
      ) : (
        <table className="mini-table" data-testid="fx-exec-list">
          <thead>
            <tr>
              <th className="num">Valor</th>
              <th className="num">Taxa</th>
              <th className="num">BRL</th>
            </tr>
          </thead>
          <tbody>
            {fxView.executions.map((ex) => (
              <tr key={ex.id}>
                <td className="num">{formatMoney(ex.foreign_amount)}</td>
                <td className="num">{formatRate(ex.rate)}</td>
                <td className="num">{formatMoney(ex.brl_amount, "BRL")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <table className="mini-table" data-testid="fx-alloc-vals">
        <thead>
          <tr>
            <th>Alocação</th>
            <th className="num">Avaliação</th>
          </tr>
        </thead>
        <tbody>
          {fxView.allocations.map((a) => (
            <tr key={a.allocation_id}>
              <td>
                Parcela vinculada
              </td>
              <td className="num">
                {a.valuation
                  ? formatMoney(a.valuation.realized_result_vs_reference, "BRL")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {canWriteFx(user) && fxView.executions.length === 0 ? (
        <form className="fx-form" data-testid="fx-exec-form" onSubmit={(e) => void onRegisterExec(e)}>
          <h3 className="section-subtitle">Registrar execução</h3>
          <FormField label="Valor em moeda" htmlFor="fx-exec-amount">
            <MoneyInput
              id="fx-exec-amount"
              data-testid="fx-exec-amount"
              value={foreignAmt}
              onValueChange={setForeignAmt}
              placeholder={fxView.amount}
            />
          </FormField>
          <FormField label="Taxa" htmlFor="fx-exec-rate">
            <RateInput
              id="fx-exec-rate"
              data-testid="fx-exec-rate"
              value={rate}
              onValueChange={setRate}
              fractionDigits={4}
            />
          </FormField>
          <FormField label="Evidência">
            <FileUpload
              data-testid="fx-exec-doc"
              fileName={file?.name}
              onFileChange={setFile}
              label="Anexar evidência"
            />
          </FormField>
          <Button type="submit" data-testid="fx-exec-save" busy={busy}>
            Registrar e vincular
          </Button>
        </form>
      ) : null}
    </SectionCard>
  );
}
