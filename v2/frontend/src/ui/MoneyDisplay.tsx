import { formatMoney, formatRate } from "./format";

export function MoneyDisplay({
  amount,
  currency,
}: {
  amount: string | number | null | undefined;
  currency?: string | null;
}) {
  const text = formatMoney(amount, currency);
  return (
    <span className="money" data-testid="money">
      {text}
    </span>
  );
}

export function FxDisplay({
  rate,
  stale,
  fractionDigits = 4,
}: {
  rate: string | null | undefined;
  stale?: boolean;
  fractionDigits?: number;
}) {
  const text = formatRate(rate, fractionDigits);
  if (text === "—") {
    return <span className="fx-display">—</span>;
  }
  return (
    <span className={`fx-display${stale ? " is-stale" : ""}`} data-testid="fx-display">
      {text}
      {stale ? " · desatualizado" : ""}
    </span>
  );
}
