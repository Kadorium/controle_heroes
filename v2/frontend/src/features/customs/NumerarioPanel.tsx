import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import {
  cancelFundingRequest,
  confirmFundingRequest,
  createFundingRequest,
  createPayee,
  listFundingRequests,
  listPayees,
  replaceExpenseLines,
  replaceTaxLines,
  replaceValueBases,
  type CustomsPayee,
  type FundingRequest,
} from "./customsApi";
import { canWriteCustoms, conflictMessage } from "./customsPermissions";
import { fundingStatusLabel } from "../inventory/inventoryLabels";
import {
  Button,
  EmptyState,
  ErrorState,
  FormField,
  formatMoney,
  LoadingState,
  Notice,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = {
  user: User;
  processId: number;
};

export function NumerarioPanel({ user, processId }: Props) {
  const writable = canWriteCustoms(user);
  const [fundings, setFundings] = useState<FundingRequest[] | undefined>(undefined);
  const [payees, setPayees] = useState<CustomsPayee[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [payeeName, setPayeeName] = useState("Bechtrans");
  const [bankName, setBankName] = useState("Banco Exemplo");
  const [pixKey, setPixKey] = useState("");
  const [declaredTotal, setDeclaredTotal] = useState("1500.00");
  const [currency, setCurrency] = useState("BRL");
  const [basisAmount, setBasisAmount] = useState("1000");
  const [taxAmount, setTaxAmount] = useState("300");
  const [expenseAmount, setExpenseAmount] = useState("200");
  const [emptyLineLabel, setEmptyLineLabel] = useState("Linha sem valor");

  const reload = useCallback(async () => {
    const [frs, ps] = await Promise.all([
      listFundingRequests(processId),
      listPayees(),
    ]);
    setFundings(frs);
    setPayees(ps);
  }, [processId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setError(null);
      try {
        await reload();
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reload]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (e) {
      setError(conflictMessage(e as Error & { status?: number; code?: string }));
    } finally {
      setBusy(false);
    }
  }

  if (error && fundings === undefined) return <ErrorState message={error} />;
  if (fundings === undefined) return <LoadingState message="Carregando Numerário…" />;

  const draft = fundings.find((f) => f.status === "DRAFT") ?? null;
  const selected = draft ?? fundings[0] ?? null;

  return (
    <div data-testid="customs-numerario-panel">
      {error ? (
        <Notice tone="danger" data-testid="numerario-error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Numerário">
        {fundings.length === 0 ? (
          <EmptyState
            title="Sem Numerário"
            message="Crie um favorecido e uma solicitação de Numerário para este processo."
          />
        ) : (
          <ul data-testid="numerario-list">
            {fundings.map((f) => (
              <li key={f.id} data-testid={`numerario-item-${f.id}`}>
                #{f.id} · {fundingStatusLabel(f.status)} · declarado{" "}
                {formatMoney(f.declared_total, f.currency)} · estruturado{" "}
                {formatMoney(f.structured_total, f.currency)} · divergência{" "}
                {formatMoney(f.divergence, f.currency)}
                {f.payee ? ` · ${f.payee.name}` : ""}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      {writable ? (
        <SectionCard title="Novo favorecido / Numerário">
          <div className="form-actions">
            <FormField label="Nome do payee">
              <TextInput
                value={payeeName}
                onChange={(e) => setPayeeName(e.target.value)}
                data-testid="numerario-payee-name"
              />
            </FormField>
            <FormField label="Banco">
              <TextInput
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
                data-testid="numerario-bank"
              />
            </FormField>
            <FormField label="PIX">
              <TextInput
                value={pixKey}
                onChange={(e) => setPixKey(e.target.value)}
                data-testid="numerario-pix"
              />
            </FormField>
            <FormField label="Moeda">
              <TextInput
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                data-testid="numerario-currency"
              />
            </FormField>
            <FormField label="Total declarado">
              <TextInput
                value={declaredTotal}
                onChange={(e) => setDeclaredTotal(e.target.value)}
                data-testid="numerario-declared"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy || !payeeName.trim()}
              data-testid="numerario-create"
              onClick={() =>
                void run(async () => {
                  const payee = await createPayee({
                    name: payeeName,
                    bank_name: bankName || null,
                    pix_key: pixKey || null,
                  });
                  await createFundingRequest(processId, {
                    payee_id: payee.id,
                    currency,
                    declared_total: declaredTotal,
                    reference: `NUM-${processId}`,
                  });
                })
              }
            >
              Criar favorecido + Numerário
            </Button>
          </div>
          {payees.length > 0 ? (
            <p data-testid="numerario-payee-count">{payees.length} favorecido(s) cadastrado(s)</p>
          ) : null}
        </SectionCard>
      ) : null}

      {selected && selected.status === "DRAFT" && writable ? (
        <SectionCard title={`Editar linhas — Numerário #${selected.id} (rascunho)`}>
          <div className="form-actions">
            <FormField label="Base (valor)">
              <TextInput
                value={basisAmount}
                onChange={(e) => setBasisAmount(e.target.value)}
                data-testid="numerario-basis"
              />
            </FormField>
            <FormField label="Tributo">
              <TextInput
                value={taxAmount}
                onChange={(e) => setTaxAmount(e.target.value)}
                data-testid="numerario-tax"
              />
            </FormField>
            <FormField label="Despesa">
              <TextInput
                value={expenseAmount}
                onChange={(e) => setExpenseAmount(e.target.value)}
                data-testid="numerario-expense"
              />
            </FormField>
            <FormField label="Linha vazia (label)">
              <TextInput
                value={emptyLineLabel}
                onChange={(e) => setEmptyLineLabel(e.target.value)}
                data-testid="numerario-empty-label"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy}
              data-testid="numerario-save-lines"
              onClick={() =>
                void run(async () => {
                  const v = selected.version;
                  let fr = await replaceValueBases(processId, selected.id, {
                    expected_version: v,
                    lines: [
                      {
                        position: 1,
                        label: "CIF",
                        code: "CIF",
                        amount: basisAmount.trim() || null,
                        currency,
                      },
                      {
                        position: 2,
                        label: emptyLineLabel,
                        code: "EMPTY",
                        amount: null,
                        currency,
                      },
                    ],
                  });
                  fr = await replaceTaxLines(processId, selected.id, {
                    expected_version: fr.version,
                    lines: [
                      {
                        position: 1,
                        label: "II",
                        code: "II",
                        amount: taxAmount.trim() || null,
                        currency,
                      },
                    ],
                  });
                  await replaceExpenseLines(processId, selected.id, {
                    expected_version: fr.version,
                    lines: [
                      {
                        position: 1,
                        label: "Despachante",
                        code: "DSP",
                        amount: expenseAmount.trim() || null,
                        currency,
                      },
                    ],
                  });
                })
              }
            >
              Salvar bases / tributos / despesas
            </Button>
            <Button
              type="button"
              disabled={busy}
              data-testid="numerario-confirm"
              onClick={() =>
                void run(async () => {
                  await confirmFundingRequest(processId, selected.id, {
                    expected_version: selected.version,
                  });
                })
              }
            >
              Confirmar
            </Button>
            <Button
              type="button"
              variant="danger"
              disabled={busy}
              data-testid="numerario-cancel"
              onClick={() =>
                void run(async () => {
                  await cancelFundingRequest(processId, selected.id, {
                    expected_version: selected.version,
                  });
                })
              }
            >
              Cancelar
            </Button>
          </div>
          <p data-testid="numerario-totals">
            Declarado {formatMoney(selected.declared_total, selected.currency)} · Estruturado{" "}
            {formatMoney(selected.structured_total, selected.currency)} · Divergência{" "}
            {formatMoney(selected.divergence, selected.currency)}
          </p>
        </SectionCard>
      ) : null}

      {selected && selected.status !== "DRAFT" ? (
        <SectionCard
          title={`Numerário #${selected.id} (${fundingStatusLabel(selected.status)})`}
        >
          <p data-testid="numerario-confirmed-totals">
            Declarado {formatMoney(selected.declared_total, selected.currency)} · Estruturado{" "}
            {formatMoney(selected.structured_total, selected.currency)} · Divergência{" "}
            {formatMoney(selected.divergence, selected.currency)}
          </p>
          {selected.payable_links && selected.payable_links.length > 0 ? (
            <p data-testid="numerario-payable-links">
              Conta a pagar{" "}
              {selected.payable_links.map((lnk, idx) => (
                <span key={lnk.id}>
                  {idx > 0 ? ", " : null}
                  <Link to="/payables">#{lnk.payable_id}</Link>
                </span>
              ))}{" "}
              · <Link to="/payables">Abrir AP</Link>
            </p>
          ) : null}
          <ul>
            {selected.value_bases.map((l) => (
              <li key={`vb-${l.id}`}>
                Base {l.code || l.label}: {l.amount ?? "(vazio)"}
              </li>
            ))}
            {selected.tax_lines.map((l) => (
              <li key={`tx-${l.id}`}>
                Tributo {l.code || l.label}: {l.amount ?? "(vazio)"}
              </li>
            ))}
            {selected.expense_lines.map((l) => (
              <li key={`ex-${l.id}`}>
                Despesa {l.code || l.label}: {l.amount ?? "(vazio)"}
              </li>
            ))}
          </ul>
          {selected.status === "CONFIRMED" && writable ? (
            <Button
              type="button"
              variant="danger"
              disabled={busy}
              data-testid="numerario-cancel-confirmed"
              onClick={() =>
                void run(async () => {
                  await cancelFundingRequest(processId, selected.id, {
                    expected_version: selected.version,
                  });
                })
              }
            >
              Cancelar (se conta a pagar aberta)
            </Button>
          ) : null}
        </SectionCard>
      ) : null}
    </div>
  );
}
