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
import { numerarioDisplayTotals } from "./numerarioDisplay";
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
            {fundings.map((f) => {
              const t = numerarioDisplayTotals(f);
              return (
                <li key={f.id} data-testid={`numerario-item-${f.id}`}>
                  #{f.id} · {fundingStatusLabel(f.status)} · declarado{" "}
                  {formatMoney(t.declaredWire, f.currency)} · tributos+despesas{" "}
                  {formatMoney(t.obligationWire, f.currency)}
                  {f.payee ? ` · ${f.payee.name}` : ""}
                </li>
              );
            })}
          </ul>
        )}
      </SectionCard>

      {writable ? (
        <SectionCard title="Novo favorecido / Numerário (ensaio — não substitui o PDF)">
          <p className="muted">
            Use só quando não houver Solicitação de Numerário no ingest. Valores digitados aqui não
            são fato documental.
          </p>
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
        <SectionCard title={`Numerário #${selected.id} (rascunho) — confirmar obrigação`}>
          <Notice tone="warning" data-testid="numerario-pdf-lines-notice">
            Confirmar registra a obrigação (payable CUSTOMS_FUNDING em aberto). Não paga. Não
            substitua linhas extraídas do PDF por valores digitados.
          </Notice>
          <NumerarioLineGroups fr={selected} />
          <NumerarioComparableTotals fr={selected} />
          <div className="form-actions">
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
              Confirmar (nasce a obrigação, sem pagar)
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
          <p className="muted">Ajuste excepcional de linhas (não usar em documento real):</p>
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
          </div>
        </SectionCard>
      ) : null}

      {selected && selected.status !== "DRAFT" ? (
        <SectionCard
          title={`Numerário #${selected.id} (${fundingStatusLabel(selected.status)})`}
        >
          <NumerarioComparableTotals fr={selected} testId="numerario-confirmed-totals" />
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
          <NumerarioLineGroups fr={selected} />
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

function lineLabel(l: { code?: string | null; label?: string | null; amount?: string | null; currency?: string | null }) {
  const name = l.code || l.label || "linha";
  const amt = l.amount ?? "(vazio)";
  const cur = l.currency?.trim();
  return `${name}: ${amt}${cur ? ` ${cur}` : ""}`;
}

function NumerarioLineGroups({ fr }: { fr: FundingRequest }) {
  return (
    <div data-testid="numerario-draft-lines">
      <p className="muted">Bases aduaneiras (FOB/CIF) — referência, não entram no total a pagar</p>
      <ul data-testid="numerario-bases">
        {fr.value_bases.map((l) => (
          <li key={`vb-${l.id}`}>Base {lineLabel(l)}</li>
        ))}
      </ul>
      <p className="muted">Tributos</p>
      <ul data-testid="numerario-taxes">
        {fr.tax_lines.map((l) => (
          <li key={`tx-${l.id}`}>Tributo {lineLabel(l)}</li>
        ))}
      </ul>
      <p className="muted">Despesas</p>
      <ul data-testid="numerario-expenses">
        {fr.expense_lines.map((l) => (
          <li key={`ex-${l.id}`}>Despesa {lineLabel(l)}</li>
        ))}
      </ul>
    </div>
  );
}

function NumerarioComparableTotals({
  fr,
  testId = "numerario-totals",
}: {
  fr: FundingRequest;
  testId?: string;
}) {
  const t = numerarioDisplayTotals(fr);
  return (
    <div data-testid={testId}>
      <Notice tone="info" data-testid="numerario-bases-notice">
        Bases FOB/CIF não são o total do Numerário. O total documental declarado compara-se a
        tributos + despesas, não à soma que inclui bases.
      </Notice>
      {t.basesMixedCurrency ? (
        <p className="muted">As bases estão em moedas distintas — não somar com o total em reais.</p>
      ) : null}
      <p data-testid="numerario-declared">
        Total documental declarado {formatMoney(t.declaredWire, fr.currency)}
      </p>
      <p data-testid="numerario-obligation">
        Tributos {formatMoney(t.taxesWire, fr.currency)} + despesas{" "}
        {formatMoney(t.expensesWire, fr.currency)} = obrigação{" "}
        {formatMoney(t.obligationWire, fr.currency)}
      </p>
      <p data-testid="numerario-obligation-gap">
        Diferença obrigação vs declarado {formatMoney(t.obligationVsDeclaredWire, fr.currency)}
      </p>
    </div>
  );
}
