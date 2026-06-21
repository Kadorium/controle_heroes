import { DEFAULT_IMPORT_CURRENCY } from "../../constants/currency";

export function compactMoney(value: number, currency = DEFAULT_IMPORT_CURRENCY): string {
  const abs = Math.abs(value);
  let formatted: string;
  let unit = "";
  if (abs >= 1_000_000) {
    formatted = (value / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
    unit = " mi";
  } else if (abs >= 1_000) {
    formatted = (value / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
    unit = " mil";
  } else {
    formatted = value.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  }
  return `${currency} ${formatted}${unit}`;
}

export function fullMoney(value: number, currency = DEFAULT_IMPORT_CURRENCY): string {
  return `${currency} ${value.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

export function dominantCurrency(currencies: string[]): string {
  if (currencies.length === 0) return DEFAULT_IMPORT_CURRENCY;
  const counts = new Map<string, number>();
  currencies.forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1));
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
}
