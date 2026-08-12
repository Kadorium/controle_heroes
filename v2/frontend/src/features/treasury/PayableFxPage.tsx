import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { User } from "../auth/types";
import { getPayable, type Payable } from "../billing/billingApi";
import {
  ContextBreadcrumb,
  ErrorState,
  LoadingState,
  MoneyDisplay,
  PageHeader,
  StatusBadge,
  SummaryGrid,
  formatDateOnly,
} from "../../ui";
import { buildReturnTo } from "../../navigation/returnState";
import { PayableFxPanel } from "./FxPanels";
import { PayableOrderCreditPanel } from "./PayableOrderCreditPanel";
import { canReadFx } from "./fxApi";

type Props = { user: User };

/** SCR-009 — Câmbio da obrigação (sem hub /fx). FX ≠ liquidação. */
export function PayableFxPage({ user }: Props) {
  const { payableId } = useParams();
  const id = Number(payableId);
  const [row, setRow] = useState<Payable | null>(null);
  const [error, setError] = useState<string | null>(null);
  const payablesReturn = buildReturnTo("/payables");

  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) {
      setError("Obrigação inválida");
      return;
    }
    let cancelled = false;
    void getPayable(id)
      .then((p) => {
        if (!cancelled) setRow(p);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!canReadFx(user)) return <ErrorState message="Sem permissão de câmbio" />;

  const titleLabel = row
    ? `Parcela ${row.sequence} · venc. ${formatDateOnly(String(row.due_date))}`
    : "Câmbio da obrigação";

  return (
    <section className="panel dense page-detail detail-shell" data-testid="payable-fx-page">
      <ContextBreadcrumb
        items={[
          { label: "Financeiro", to: payablesReturn },
          { label: "Contas a pagar", to: payablesReturn },
          { label: titleLabel },
        ]}
      />
      <PageHeader
        title={row ? `Câmbio · ${titleLabel}` : "Câmbio da obrigação"}
        subtitle="Planejado · mercado · realizado"
        actions={
          <Link className="ui-button ui-button--secondary" to={payablesReturn}>
            Voltar à fila
          </Link>
        }
      />
      {error ? <ErrorState message={error} /> : null}
      {!row && !error ? <LoadingState message="Carregando obrigação…" /> : null}
      {row ? (
        <div data-testid="fx-payable-context">
          <SummaryGrid
            items={[
              { label: "Parcela", value: String(row.sequence) },
              { label: "Vencimento", value: formatDateOnly(String(row.due_date)) },
              { label: "Moeda", value: row.currency },
              {
                label: "Saldo",
                value: <MoneyDisplay amount={row.balance} currency={row.currency} />,
              },
              {
                label: "Status",
                value: <StatusBadge status={row.status} entity="payable" />,
              },
              {
                label: "Banco",
                value: row.destination_bank || "—",
              },
              {
                label: "IBAN",
                value: (
                  <span data-testid="payable-destination-iban">
                    {row.destination_iban || "—"}
                  </span>
                ),
              },
            ]}
          />
        </div>
      ) : null}
      {row ? (
        <PayableOrderCreditPanel
          user={user}
          payable={row}
          onApplied={() => {
            void getPayable(id).then(setRow);
          }}
        />
      ) : null}
      <div className="fx-shell">
        <PayableFxPanel user={user} payableId={id} />
      </div>
    </section>
  );
}
