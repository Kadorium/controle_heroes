import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { listPayables, type Payable } from "../billing/billingApi";
import { PayableFxPanel } from "./FxPanels";
import { canReadFx } from "./fxApi";

type Props = { user: User };

export function PayableFxPage({ user }: Props) {
  const { payableId } = useParams();
  const id = Number(payableId);
  const [row, setRow] = useState<Payable | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listPayables()
      .then((rows) => setRow(rows.find((p) => p.id === id) ?? null))
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [id]);

  if (!canReadFx(user)) return <div className="error">Sem permissão FX</div>;

  return (
    <section className="panel" data-testid="payable-fx-page">
      <p>
        <Link to="/payables">← Payables</Link>
      </p>
      <h1>Payable #{id}</h1>
      {error ? <div className="error">{error}</div> : null}
      {row ? (
        <p className="muted">
          Invoice #{row.invoice_id} · {row.currency} · saldo {row.balance} · {row.status}
        </p>
      ) : (
        <p className="muted">Carregando…</p>
      )}
      <PayableFxPanel user={user} payableId={id} />
    </section>
  );
}
