import { emptyDash, formatMoney } from "../../i18n/glossario";
import type { AggregateTotals } from "./novaOrdemTotals";
import { eurToBrl } from "./novaOrdemTotals";

interface Props {
  totals: AggregateTotals;
  provisionRate: string;
}

function DualRow({
  label,
  eur,
  rate,
  strong,
}: {
  label: string;
  eur: number | null;
  rate: number | null;
  strong?: boolean;
}) {
  const brl = eurToBrl(eur, rate);
  const Tag = strong ? "strong" : "span";
  return (
    <div className={`nova-ordem-fx__row${strong ? " nova-ordem-fx__row--total" : ""}`}>
      <span className="nova-ordem-fx__label">{label}</span>
      <Tag className="nova-ordem-fx__eur">
        {eur !== null ? formatMoney(eur, "EUR") : emptyDash(null)}
      </Tag>
      <Tag className="nova-ordem-fx__brl">
        {brl !== null ? formatMoney(brl, "BRL") : emptyDash(null)}
      </Tag>
    </div>
  );
}

export function NovaOrdemFxSummary({ totals, provisionRate }: Props) {
  const rate = Number(String(provisionRate).replace(",", "."));
  const appliedRate = Number.isNaN(rate) ? null : rate;

  return (
    <section className="nova-ordem-fx nova-ordem-fx--totals-only" aria-label="Totais EUR e BRL provisionado">
      <div className="nova-ordem-fx__totals">
        <div className="nova-ordem-fx__totals-head">
          <span />
          <span className="nova-ordem-fx__col-h">EUR</span>
          <span className="nova-ordem-fx__col-h">BRL (provisionado)</span>
        </div>
        <DualRow label="Bruto" eur={totals.gross} rate={appliedRate} />
        <DualRow label="Descontos (Σ un. × qtd)" eur={totals.discounts} rate={appliedRate} />
        <DualRow label="Líquido do pedido" eur={totals.net} rate={appliedRate} strong />
        {totals.quantity !== null && (
          <p className="meta nova-ordem-fx__qty">{totals.quantity} unidades no pedido</p>
        )}
      </div>
    </section>
  );
}
