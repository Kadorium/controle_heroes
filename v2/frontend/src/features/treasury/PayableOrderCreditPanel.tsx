import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import type { Payable } from "../billing/billingApi";
import { getPayable } from "../billing/billingApi";
import {
  Button,
  Notice,
  SectionCard,
  formatDateOnly,
} from "../../ui";
import { listOrderAdvances, type OrderAdvance } from "./advanceApi";
import { allocatePayment, canAllocateTreasury } from "./treasuryApi";

type Props = {
  user: User;
  payable: Payable;
  onApplied: () => void;
};

function minAmount(a: string, b: string): string {
  const na = Number(a);
  const nb = Number(b);
  if (!Number.isFinite(na) || !Number.isFinite(nb)) return "0";
  return (na < nb ? na : nb).toFixed(2);
}

/** Crédito do mesmo pedido — nunca aplica sozinho. */
export function PayableOrderCreditPanel({ user, payable, onApplied }: Props) {
  const orderId = payable.order_id ?? null;
  const canAlloc = canAllocateTreasury(user);
  const [advances, setAdvances] = useState<OrderAdvance[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    if (orderId == null) return;
    let cancelled = false;
    setLoaded(false);
    void listOrderAdvances(orderId)
      .then((data) => {
        if (!cancelled) {
          setAdvances(data.advances ?? []);
          setLoaded(true);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Erro ao carregar créditos");
          setLoaded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [orderId, payable.id, payable.version]);

  if (orderId == null) return null;

  const open = advances.filter((a) => Number(a.amount_unallocated ?? 0) > 0);
  const balance = String(payable.balance ?? "0");

  async function apply(adv: OrderAdvance) {
    if (!canAlloc || busyId != null) return;
    const amount = minAmount(String(adv.amount_unallocated ?? "0"), balance);
    if (Number(amount) <= 0) return;
    setBusyId(adv.payment_id);
    setError(null);
    try {
      const fresh = await getPayable(payable.id);
      await allocatePayment(adv.payment_id, {
        expected_version: adv.version,
        idempotency_key: `fin2-apply-${adv.payment_id}-p${payable.id}-${fresh.version}`,
        allocations: [
          {
            payable_id: payable.id,
            amount,
            expected_version: fresh.version,
          },
        ],
      });
      onApplied();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao aplicar crédito");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <SectionCard title="Crédito do pedido" data-testid="payable-order-credit">
      <p className="muted">
        Adiantamento do pedido #{orderId}. Não é aplicado automaticamente — escolha o crédito e
        confirme.
      </p>
      {error ? (
        <Notice tone="danger">
          {error}
        </Notice>
      ) : null}
      {!loaded ? (
        <p className="muted" data-testid="payable-order-credit-loading">
          Carregando créditos…
        </p>
      ) : open.length === 0 ? (
        <p className="muted" data-testid="payable-order-credit-empty">
          Nenhum crédito em aberto neste pedido.
        </p>
      ) : (
        <ul data-testid="payable-order-credit-list">
          {open.map((a) => (
            <li key={a.payment_id} style={{ marginBottom: "0.5rem" }}>
              Adiantamento {a.currency} {a.amount_unallocated ?? a.amount} pago em{" "}
              {formatDateOnly(a.payment_date)}
              {a.rate ? ` à taxa ${a.rate}` : ""}
              {canAlloc && Number(balance) > 0 ? (
                <Button
                  type="button"
                  data-testid={`apply-advance-${a.payment_id}`}
                  busy={busyId === a.payment_id}
                  onClick={() => void apply(a)}
                  style={{ marginLeft: "0.5rem" }}
                >
                  Aplicar neste vencimento
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {Number(balance) > 0 && payable.supplier_id != null ? (
        <p>
          <Link
            className="ui-button ui-button--secondary"
            data-testid="pay-remainder-link"
            to={`/payments/new?supplier_id=${payable.supplier_id}&payable_id=${payable.id}&amount=${encodeURIComponent(balance)}&currency=${payable.currency}&order_id=${orderId}`}
          >
            Pagar saldo restante
          </Link>
        </p>
      ) : null}
      {Number(balance) > 0 ? (
        <p className="muted">
          Custo BRL desta obrigação = soma dos câmbios rateados (adiantamento + saldo). Não é
          EUR × taxa média.
        </p>
      ) : null}
    </SectionCard>
  );
}
