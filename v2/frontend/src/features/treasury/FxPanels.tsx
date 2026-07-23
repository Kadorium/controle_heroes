import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  canReadFx,
  canRefreshFxQuote,
  canWriteFx,
  fmtFx,
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

  const rateLabel = quote?.rate ?? "—";
  const stale = quote?.stale ? " · stale" : "";
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

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="fx-metric">
      <span className="fx-metric-label">{label}</span>
      <strong data-benchmark={hint}>{value}</strong>
    </div>
  );
}

export function PayableFxPanel({
  user,
  payableId,
}: {
  user: User;
  payableId: number;
}) {
  const [view, setView] = useState<PayableFxView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rate, setRate] = useState("6.00");
  const [kind, setKind] = useState("INITIAL");
  const [reason, setReason] = useState("");
  const [manualMkt, setManualMkt] = useState("6.25");

  async function reload() {
    setView(await getPayableFxView(payableId));
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [payableId]);

  if (!canReadFx(user)) return null;
  if (!view) return <p className="muted">Carregando FX…</p>;

  return (
    <section className="fx-panel" data-testid="payable-fx-panel">
      <h2>FX — três visões</h2>
      {error ? <div className="error">{error}</div> : null}
      <div className="fx-grid">
        <Metric label="Taxa original (INITIAL)" value={fmtFx(view.initial_planned_rate)} />
        <Metric label="Current forecast" value={fmtFx(view.current_forecast_rate)} />
        <Metric
          label={`Online (${view.market.status}${view.market.stale ? ", stale" : ""})`}
          value={fmtFx(view.market.rate)}
        />
        <Metric label="Open foreign" value={fmtFx(view.open_foreign)} />
        <Metric label="BRL projetado (open×current)" value={fmtFx(view.projected_open_brl)} />
        <Metric label="BRL online (open×market)" value={fmtFx(view.market_open_brl)} />
        <Metric label="BRL realizado" value={fmtFx(view.realized_brl)} />
        <Metric
          label="Resultado realizado vs reference"
          value={fmtFx(view.realized_result_vs_reference)}
          hint="frozen_reference"
        />
        <Metric
          label="Resultado realizado vs initial"
          value={fmtFx(view.realized_result_vs_initial)}
          hint="initial"
        />
        <Metric
          label="Online vs current"
          value={fmtFx(view.online_result_vs_current)}
          hint="current"
        />
        <Metric
          label="Online vs initial"
          value={fmtFx(view.online_result_vs_initial)}
          hint="initial"
        />
        <Metric label="Total vs current" value={fmtFx(view.total_vs_current)} hint="current" />
        <Metric label="Total vs initial" value={fmtFx(view.total_vs_initial)} hint="initial" />
      </div>

      {canWriteFx(user) ? (
        <form
          className="fx-form"
          data-testid="fx-plan-form"
          onSubmit={(e) => {
            e.preventDefault();
            void (async () => {
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
              }
            })();
          }}
        >
          <h3>Taxa projetada</h3>
          <label>
            Kind
            <select data-testid="fx-plan-kind" value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="INITIAL">INITIAL</option>
              <option value="REFORECAST">REFORECAST</option>
              <option value="CORRECTION">CORRECTION</option>
            </select>
          </label>
          <label>
            Rate
            <input data-testid="fx-plan-rate" value={rate} onChange={(e) => setRate(e.target.value)} />
          </label>
          {kind !== "INITIAL" ? (
            <label>
              Reason
              <input
                data-testid="fx-plan-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
          ) : null}
          <button type="submit" data-testid="fx-plan-save">
            Salvar plano
          </button>
        </form>
      ) : null}

      {canWriteFx(user) ? (
        <form
          className="fx-form"
          data-testid="fx-manual-quote-form"
          onSubmit={(e) => {
            e.preventDefault();
            void (async () => {
              setError(null);
              try {
                await postManualQuote(manualMkt);
                await reload();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Erro");
              }
            })();
          }}
        >
          <h3>Cotação manual (Inc-4A)</h3>
          <label>
            Market rate
            <input
              data-testid="fx-manual-rate"
              value={manualMkt}
              onChange={(e) => setManualMkt(e.target.value)}
            />
          </label>
          <button type="submit" data-testid="fx-manual-save">
            Gravar cotação
          </button>
        </form>
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
  if (!view) return <p className="muted">Carregando FX…</p>;
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
    <section className="fx-panel" data-testid="payment-fx-panel">
      <h2>FX realizado</h2>
      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}
      <ul data-testid="fx-exec-list">
        {fxView.executions.map((ex) => (
          <li key={ex.id}>
            Exec #{ex.id} · {ex.foreign_amount} @ {ex.rate} = R$ {ex.brl_amount}
          </li>
        ))}
      </ul>
      <ul data-testid="fx-alloc-vals">
        {fxView.allocations.map((a) => (
          <li key={a.allocation_id}>
            Alloc #{a.allocation_id} → payable #{a.payable_id}
            {a.valuation
              ? ` · vs ref ${a.valuation.realized_result_vs_reference} (freeze ${a.valuation.planned_rate_used_at_realization})`
              : " · sem valuation"}
          </li>
        ))}
      </ul>
      {canWriteFx(user) && fxView.executions.length === 0 ? (
        <form className="fx-form" data-testid="fx-exec-form" onSubmit={(e) => void onRegisterExec(e)}>
          <h3>Registrar execução</h3>
          <label>
            Foreign amount
            <input
              data-testid="fx-exec-amount"
              value={foreignAmt}
              placeholder={fxView.amount}
              onChange={(e) => setForeignAmt(e.target.value)}
            />
          </label>
          <label>
            Rate
            <input data-testid="fx-exec-rate" value={rate} onChange={(e) => setRate(e.target.value)} />
          </label>
          <label>
            Evidência
            <input
              data-testid="fx-exec-doc"
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <button type="submit" data-testid="fx-exec-save" disabled={busy}>
            Registrar + vincular + freeze
          </button>
        </form>
      ) : null}
    </section>
  );
}
