import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  Button,
  DateInput,
  EmptyState,
  FormField,
  LoadingState,
  MoneyDisplay,
  MoneyInput,
  Notice,
  OperationalTable,
  SectionCard,
  SelectField,
  TextInput,
  formatDateOnly,
  formatMoney,
} from "../../ui";
import { canWriteOrders } from "./orderTotals";
import {
  getPaymentSchedule,
  setPaymentSchedule,
  type PaymentScheduleView,
} from "./ordersApi";

type DraftLine = {
  due_date: string;
  condition_text: string;
  percent: string;
  amount: string;
};

type Props = {
  user: User;
  orderId: number;
  orderCurrency: string;
  orderStatus: string;
  orderVersion: number;
  onSaved: () => Promise<void> | void;
};

function emptyLine(): DraftLine {
  return { due_date: "", condition_text: "", percent: "", amount: "" };
}

function toDraft(view: PaymentScheduleView): DraftLine[] {
  if (!view.lines.length) return [emptyLine()];
  return view.lines.map((ln) => ({
    due_date: ln.due_date ?? "",
    condition_text: ln.condition_text ?? "",
    percent: ln.percent ?? "",
    amount: ln.amount ?? "",
  }));
}

function coherenceCopy(view: PaymentScheduleView): { tone: "info" | "warning"; text: string } | null {
  if (!view.lines.length || !view.coherence) return null;
  if (view.coherence === "unverifiable") {
    return {
      tone: "info",
      text: "Coerência não verificável — total comercial incompleto. Ausência não é zero.",
    };
  }
  if (view.coherence === "divergent") {
    return {
      tone: "warning",
      text: `Divergente do total comercial (delta ${formatMoney(view.delta, view.currency)}).`,
    };
  }
  return { tone: "info", text: "Alinhado ao total comercial." };
}

export function OrderPaymentSchedulePanel({
  user,
  orderId,
  orderCurrency,
  orderStatus,
  orderVersion,
  onSaved,
}: Props) {
  const canWrite = canWriteOrders(user) && (orderStatus === "DRAFT" || orderStatus === "CONFIRMED");
  const [view, setView] = useState<PaymentScheduleView | null>(null);
  const [mode, setMode] = useState<"PERCENT" | "AMOUNT">("PERCENT");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const next = await getPaymentSchedule(orderId);
      setView(next);
      setMode(next.mode === "AMOUNT" ? "AMOUNT" : "PERCENT");
      setLines(toDraft(next));
      setEditing(false);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function save(nextLines: DraftLine[], nextMode: "PERCENT" | "AMOUNT" | null) {
    if (busy) return;
    if (orderStatus === "CONFIRMED" && !reason.trim()) {
      setError("Informe o motivo para alterar o cronograma de um pedido confirmado.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payloadLines =
        nextMode == null
          ? []
          : nextLines.map((ln) => ({
              due_date: ln.due_date || null,
              condition_text: ln.condition_text.trim() || null,
              percent: nextMode === "PERCENT" ? ln.percent.trim() || null : null,
              amount: nextMode === "AMOUNT" ? ln.amount.trim() || null : null,
            }));
      const next = await setPaymentSchedule(orderId, {
        expected_version: orderVersion,
        mode: nextMode,
        lines: payloadLines,
        reason_code: orderStatus === "CONFIRMED" ? reason.trim() : null,
      });
      setView(next);
      setMode(next.mode === "AMOUNT" ? "AMOUNT" : "PERCENT");
      setLines(toDraft(next));
      setEditing(false);
      setReason("");
      await onSaved();
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          await onSaved();
          await reload();
          setError("Conflito de versão — estado recarregado. Revise e grave de novo.");
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  const empty = !view?.lines.length;
  const banner = view ? coherenceCopy(view) : null;

  return (
    <SectionCard
      title="Cronograma de pagamento"
      data-testid="order-schedule"
      actions={
        canWrite && !loading ? (
          empty && !editing ? (
            <Button
              data-testid="order-schedule-start"
              onClick={() => {
                setEditing(true);
                setLines([emptyLine()]);
                setMode("PERCENT");
              }}
            >
              Definir cronograma
            </Button>
          ) : (
            <div className="stack-row">
              {view?.lines.length ? (
                <Button
                  variant="secondary"
                  busy={busy}
                  data-testid="order-schedule-clear"
                  onClick={() => void save([], null)}
                >
                  Limpar
                </Button>
              ) : null}
              <Button
                busy={busy}
                data-testid="order-schedule-save"
                onClick={() => void save(lines, mode)}
              >
                Salvar cronograma
              </Button>
            </div>
          )
        ) : undefined
      }
    >
      <p className="muted">
        Planejamento comercial do pedido. Não é pagamento, adiantamento nem conta a pagar.
      </p>
      {loading ? <LoadingState message="Carregando cronograma…" /> : null}
      {error ? (
        <Notice tone="danger" data-testid="order-schedule-error">
          {error}
        </Notice>
      ) : null}
      {!loading && empty && !editing ? (
        <div data-testid="order-schedule-empty">
          <EmptyState message="Sem cronograma — a previsão não duplica antecipo nem obrigação." />
        </div>
      ) : null}
      {!loading && (editing || !empty) ? (
        <>
          {canWrite ? (
            <div className="form-inline stack-row">
              <FormField label="Modo" htmlFor="order-schedule-mode">
                <SelectField
                  id="order-schedule-mode"
                  data-testid="order-schedule-mode"
                  value={mode}
                  onChange={(e) => {
                    setMode(e.target.value as "PERCENT" | "AMOUNT");
                    setEditing(true);
                  }}
                  options={[
                    { value: "PERCENT", label: "Percentual" },
                    { value: "AMOUNT", label: "Valor" },
                  ]}
                />
              </FormField>
            </div>
          ) : (
            <p className="muted">Modo: {view?.mode === "AMOUNT" ? "Valor" : view?.mode === "PERCENT" ? "Percentual" : "—"}</p>
          )}
          {orderStatus === "CONFIRMED" && canWrite ? (
            <FormField label="Motivo da alteração" htmlFor="order-schedule-reason">
              <TextInput
                id="order-schedule-reason"
                data-testid="order-schedule-reason"
                value={reason}
                maxLength={64}
                placeholder="Obrigatório em pedido confirmado"
                onChange={(e) => setReason(e.target.value)}
              />
            </FormField>
          ) : null}
          {banner ? (
            <Notice tone={banner.tone} data-testid="order-schedule-coherence">
              {banner.text}
            </Notice>
          ) : null}
          <OperationalTable density="standard">
            <thead>
              <tr>
                <th>Data</th>
                <th>Condição</th>
                <th className="num">{mode === "PERCENT" ? "%" : "Valor"}</th>
                <th className="num">Derivado</th>
                {canWrite ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {lines.map((ln, idx) => (
                <tr key={idx}>
                  <td>
                    {canWrite ? (
                      <DateInput
                        data-testid={`order-schedule-date-${idx}`}
                        value={ln.due_date}
                        onChange={(e) => {
                          const next = [...lines];
                          next[idx] = { ...ln, due_date: e.target.value };
                          setLines(next);
                          setEditing(true);
                        }}
                      />
                    ) : (
                      formatDateOnly(ln.due_date) || "—"
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <TextInput
                        data-testid={`order-schedule-cond-${idx}`}
                        value={ln.condition_text}
                        maxLength={256}
                        placeholder="ex. bonifico anticipato"
                        onChange={(e) => {
                          const next = [...lines];
                          next[idx] = { ...ln, condition_text: e.target.value };
                          setLines(next);
                          setEditing(true);
                        }}
                      />
                    ) : (
                      ln.condition_text || "—"
                    )}
                  </td>
                  <td className="num">
                    {canWrite && mode === "PERCENT" ? (
                      <TextInput
                        data-testid={`order-schedule-pct-${idx}`}
                        className="num"
                        value={ln.percent}
                        placeholder="%"
                        onChange={(e) => {
                          const next = [...lines];
                          next[idx] = { ...ln, percent: e.target.value };
                          setLines(next);
                          setEditing(true);
                        }}
                      />
                    ) : null}
                    {canWrite && mode === "AMOUNT" ? (
                      <MoneyInput
                        data-testid={`order-schedule-amt-${idx}`}
                        currency={orderCurrency}
                        value={ln.amount}
                        onValueChange={(v) => {
                          const next = [...lines];
                          next[idx] = { ...ln, amount: v };
                          setLines(next);
                          setEditing(true);
                        }}
                      />
                    ) : null}
                    {!canWrite && mode === "PERCENT" ? `${ln.percent || "—"}%` : null}
                    {!canWrite && mode === "AMOUNT" ? (
                      <MoneyDisplay amount={ln.amount || null} currency={orderCurrency} />
                    ) : null}
                  </td>
                  <td className="num" data-testid={`order-schedule-derived-${idx}`}>
                    {view?.lines[idx]?.derived_amount ? (
                      <MoneyDisplay amount={view.lines[idx].derived_amount} currency={orderCurrency} />
                    ) : (
                      "—"
                    )}
                  </td>
                  {canWrite ? (
                    <td>
                      <Button
                        variant="ghost"
                        data-testid={`order-schedule-remove-${idx}`}
                        onClick={() => {
                          const next = lines.filter((_, i) => i !== idx);
                          setLines(next.length ? next : [emptyLine()]);
                          setEditing(true);
                        }}
                      >
                        Remover
                      </Button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </OperationalTable>
          {canWrite ? (
            <Button
              variant="secondary"
              data-testid="order-schedule-add"
              onClick={() => {
                setLines([...lines, emptyLine()]);
                setEditing(true);
              }}
            >
              Adicionar parcela
            </Button>
          ) : null}
        </>
      ) : null}
    </SectionCard>
  );
}
