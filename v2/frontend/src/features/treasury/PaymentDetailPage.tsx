import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  Button,
  ConfirmationModal,
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  LoadingState,
  MoneyDisplay,
  MoneyInput,
  Notice,
  OperationalTable,
  PageHeader,
  RowLink,
  SectionCard,
  StatusBadge,
  SummaryGrid,
  formatDateOnly,
  formatMoney,
  paymentAllocationStateLabel,
} from "../../ui";
import { buildReturnTo } from "../../navigation/returnState";
import {
  allocatePayment,
  canAllocateTreasury,
  canCancelTreasury,
  cancelPayment,
  eligiblePayables,
  getPayment,
  type EligiblePayable,
  type Payment,
} from "./treasuryApi";
import { PaymentFxPanel } from "./FxPanels";

type Props = { user: User };

type AllocIntent = {
  key: string;
  fingerprint: string;
};

function allocFingerprint(
  lines: { payable_id: number; amount: string; expected_version: number }[],
) {
  return lines
    .map((l) => `${l.payable_id}:${l.amount}:${l.expected_version}`)
    .sort()
    .join("|");
}

export function PaymentDetailPage({ user }: Props) {
  const { paymentId } = useParams();
  const id = Number(paymentId);
  const [pay, setPay] = useState<Payment | null>(null);
  const [elig, setElig] = useState<EligiblePayable[]>([]);
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmAlloc, setConfirmAlloc] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const intentRef = useRef<AllocIntent | null>(null);
  const paymentsReturn = buildReturnTo("/payments");

  async function reload() {
    const p = await getPayment(id);
    setPay(p);
    setElig(await eligiblePayables(id));
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [id]);

  const previewLines = useMemo(
    () =>
      elig
        .map((e) => ({
          payable_id: e.id,
          amount: amounts[e.id] || "",
          expected_version: e.version,
          balance: e.balance,
          currency: e.currency,
          label: e.invoice_number || (e.due_date ? `Venc. ${e.due_date}` : "Obrigação"),
        }))
        .filter((l) => l.amount && Number(l.amount) > 0),
    [elig, amounts],
  );
  const previewTotal = previewLines.reduce((acc, l) => acc + Number(l.amount), 0);
  const canCancel =
    canCancelTreasury(user) &&
    pay?.status === "REGISTERED" &&
    (pay.allocations?.length ?? 0) === 0;

  if (error && !pay) return <ErrorState message={error} />;
  if (!pay) return <LoadingState message="Carregando pagamento…" />;

  function openAllocConfirm() {
    if (!previewLines.length) {
      setError("Informe ao menos um valor a alocar");
      return;
    }
    const fp = allocFingerprint(previewLines);
    if (!intentRef.current || intentRef.current.fingerprint !== fp) {
      intentRef.current = {
        key: `ui-${id}-${crypto.randomUUID()}`,
        fingerprint: fp,
      };
    }
    setConfirmAlloc(true);
  }

  function cancelAllocIntent() {
    setConfirmAlloc(false);
    intentRef.current = null;
  }

  async function onAllocate() {
    if (!pay || busy) return;
    if (!previewLines.length) {
      setError("Informe ao menos um valor a alocar");
      setConfirmAlloc(false);
      return;
    }
    const fp = allocFingerprint(previewLines);
    if (!intentRef.current || intentRef.current.fingerprint !== fp) {
      intentRef.current = { key: `ui-${id}-${crypto.randomUUID()}`, fingerprint: fp };
    }
    const key = intentRef.current.key;
    setBusy(true);
    setError(null);
    try {
      const next = await allocatePayment(pay.id, {
        expected_version: pay.version,
        idempotency_key: key,
        allocations: previewLines.map(({ payable_id, amount, expected_version }) => ({
          payable_id,
          amount,
          expected_version,
        })),
      });
      setPay(next);
      setAmounts({});
      setElig(await eligiblePayables(id));
      setConfirmAlloc(false);
      intentRef.current = null;
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        setError(
          e instanceof Error
            ? `${e.message} — valores de alocação preservados; chave de intenção reutilizada se o payload for o mesmo.`
            : "Conflito",
        );
        try {
          const fresh = await getPayment(id);
          setPay(fresh);
          setElig(await eligiblePayables(id));
        } catch {
          /* keep local */
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onCancelPayment() {
    if (!pay || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await cancelPayment(pay.id, pay.version, "PAYMENT_CANCEL_UI");
      setPay(next);
      setConfirmCancel(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  const titleRef =
    pay.external_reference?.trim() ||
    [pay.supplier_name?.trim(), formatDateOnly(pay.payment_date), formatMoney(pay.amount, pay.currency)]
      .filter(Boolean)
      .join(" · ") ||
    "Pagamento";

  return (
    <section className="panel dense page-detail detail-shell" data-testid="payment-detail">
      <ContextBreadcrumb
        items={[
          { label: "Financeiro", to: paymentsReturn },
          { label: "Pagamentos realizados", to: paymentsReturn },
          { label: titleRef },
        ]}
      />
      <PageHeader
        title={titleRef}
        subtitle={
          pay.supplier_name?.trim()
            ? `${pay.supplier_name} · ${pay.currency}`
            : `Fornecedor não identificado · ${pay.currency}`
        }
        actions={
          <div className="stack-row page-header-actions">
            <Link className="ui-button ui-button--secondary" to={paymentsReturn}>
              Voltar à fila
            </Link>
            {canCancel ? (
              <Button
                type="button"
                variant="secondary"
                data-testid="cancel-payment"
                busy={busy}
                onClick={() => setConfirmCancel(true)}
              >
                Cancelar pagamento
              </Button>
            ) : null}
          </div>
        }
      />
      <div data-testid="payment-residual">
        <SummaryGrid
          items={[
            {
              label: "Valor",
              value: <MoneyDisplay amount={pay.amount} currency={pay.currency} />,
            },
            {
              label: "Alocado",
              value: <MoneyDisplay amount={pay.amount_allocated} currency={pay.currency} />,
            },
            {
              label: "Aberto",
              value: <MoneyDisplay amount={pay.amount_unallocated} currency={pay.currency} />,
            },
            {
              label: "Estado",
              value: (
                <span data-testid="payment-allocation-state">
                  {paymentAllocationStateLabel(pay)}
                </span>
              ),
            },
            { label: "Data", value: formatDateOnly(pay.payment_date) },
            {
              label: "Registro",
              value: <StatusBadge status={pay.status} entity="payment" />,
            },
          ]}
        />
      </div>
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Comprovantes">
        {pay.documents.length === 0 ? (
          <p className="muted">Nenhum comprovante</p>
        ) : (
          <OperationalTable density="standard" data-testid="payment-docs">
            <thead>
              <tr>
                <th>Arquivo</th>
              </tr>
            </thead>
            <tbody>
              {pay.documents.map((d) => (
                <tr key={d.id}>
                  <td>{d.original_filename}</td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        )}
      </SectionCard>

      <SectionCard title="Alocações">
        <div data-testid="alloc-list">
          {pay.allocations.length === 0 ? (
            <p className="muted">Nenhuma alocação ainda</p>
          ) : (
            <OperationalTable density="standard">
              <thead>
                <tr>
                  <th>Obrigação</th>
                  <th className="num">Valor</th>
                </tr>
              </thead>
              <tbody>
                {pay.allocations.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <RowLink to={`/payables/${a.payable_id}/fx`}>Ver obrigação</RowLink>
                    </td>
                    <td className="num">
                      <MoneyDisplay amount={a.amount} currency={pay.currency} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </OperationalTable>
          )}
        </div>
      </SectionCard>

      {canAllocateTreasury(user) && pay.status === "REGISTERED" && Number(pay.amount_unallocated) > 0 ? (
        <SectionCard title="Obrigações elegíveis">
          <Notice tone="info">
            A prévia abaixo ainda não foi confirmada. O saldo da obrigação só muda após alocar.
          </Notice>
          {elig.length === 0 ? (
            <EmptyState
              message="Sem Fattura emitida, não há Conta a pagar (obrigação) para alocar este crédito."
              orientation="A alocação existe no sistema; falta a fatura gerar a obrigação."
            />
          ) : null}
          <OperationalTable density="finance" data-testid="eligible-table">
            <thead>
              <tr>
                <th>Fatura</th>
                <th>Pedido</th>
                <th>Vencimento</th>
                <th className="num">Saldo</th>
                <th className="num">Alocar</th>
              </tr>
            </thead>
            <tbody>
              {elig.map((e) => (
                <tr key={e.id}>
                  <td>{e.invoice_number?.trim() || "—"}</td>
                  <td>{e.order_code?.trim() || "—"}</td>
                  <td>{formatDateOnly(e.due_date)}</td>
                  <td className="num">
                    <MoneyDisplay amount={e.balance} currency={e.currency} />
                  </td>
                  <td className="num">
                    <MoneyInput
                      data-testid={`alloc-amt-${e.id}`}
                      value={amounts[e.id] ?? ""}
                      onValueChange={(v) => setAmounts({ ...amounts, [e.id]: v })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
          {previewLines.length > 0 ? (
            <p data-testid="alloc-preview">
              Prévia: {previewLines.length} linha(s) · total {formatMoney(previewTotal, pay.currency)} ·
              residual após ≈ {formatMoney(Number(pay.amount_unallocated) - previewTotal, pay.currency)}
            </p>
          ) : null}
          <Button type="button" data-testid="allocate-btn" busy={busy} onClick={openAllocConfirm}>
            Alocar
          </Button>
          <ConfirmationModal
            open={confirmAlloc}
            title="Confirmar alocação"
            confirmLabel="Alocar"
            busy={busy}
            onCancel={cancelAllocIntent}
            onConfirm={() => void onAllocate()}
          >
            <p>
              A alocação é atômica. Isto reduz o saldo da obrigação e atualiza o residual do
              pagamento.
            </p>
            <OperationalTable density="standard" data-testid="alloc-preview-list">
              <tbody>
                {previewLines.map((l) => (
                  <tr key={l.payable_id}>
                    <td>{l.label}</td>
                    <td className="num">{formatMoney(l.amount, pay.currency)}</td>
                    <td className="muted">saldo {formatMoney(l.balance, l.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </OperationalTable>
          </ConfirmationModal>
        </SectionCard>
      ) : null}

      <ConfirmationModal
        open={confirmCancel}
        title="Cancelar pagamento"
        confirmLabel="Cancelar pagamento"
        busy={busy}
        onCancel={() => setConfirmCancel(false)}
        onConfirm={() => void onCancelPayment()}
      >
        <p>
          Só é possível cancelar pagamentos REGISTERED sem alocações. Esta ação não reduz saldo de
          obrigações (não há alocações).
        </p>
      </ConfirmationModal>

      {pay.allocations.length > 0 || pay.currency !== "BRL" ? (
        <PaymentFxPanel key={`${pay.id}-${pay.version}`} user={user} paymentId={pay.id} />
      ) : null}
    </section>
  );
}
