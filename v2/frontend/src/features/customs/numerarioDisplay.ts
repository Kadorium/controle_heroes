/** Totais de apresentação do Numerário — não altera o domínio.

O campo de API `structured_total` soma bases (FOB/CIF) + tributos + despesas.
Isso não é um total financeiro comparável ao total documental declarado.
*/

export type AmountLine = {
  amount?: string | number | null;
  currency?: string | null;
};

function toCents(amount: string | number | null | undefined): number | null {
  if (amount === null || amount === undefined || amount === "") return null;
  const n = typeof amount === "number" ? amount : Number(String(amount).trim());
  if (!Number.isFinite(n)) return null;
  return Math.round(n * 100);
}

function centsToWire(cents: number): string {
  return (cents / 100).toFixed(2);
}

export function sumAmountsWire(lines: AmountLine[]): string {
  let cents = 0;
  for (const line of lines) {
    const c = toCents(line.amount);
    if (c !== null) cents += c;
  }
  return centsToWire(cents);
}

export function lineCurrencies(lines: AmountLine[]): string[] {
  const set = new Set<string>();
  for (const line of lines) {
    const c = line.currency?.trim();
    if (c) set.add(c);
  }
  return [...set];
}

export type NumerarioDisplayTotals = {
  taxesWire: string;
  expensesWire: string;
  /** Tributos + despesas — comparável ao total declarado do PDF. */
  obligationWire: string;
  declaredWire: string;
  obligationVsDeclaredWire: string;
  basesMixedCurrency: boolean;
};

export function numerarioDisplayTotals(fr: {
  declared_total: string;
  value_bases: AmountLine[];
  tax_lines: AmountLine[];
  expense_lines: AmountLine[];
}): NumerarioDisplayTotals {
  const taxesWire = sumAmountsWire(fr.tax_lines);
  const expensesWire = sumAmountsWire(fr.expense_lines);
  const obligationWire = sumAmountsWire([...fr.tax_lines, ...fr.expense_lines]);
  const declaredWire = fr.declared_total;
  const gap = (toCents(obligationWire) ?? 0) - (toCents(declaredWire) ?? 0);
  return {
    taxesWire,
    expensesWire,
    obligationWire,
    declaredWire,
    obligationVsDeclaredWire: centsToWire(gap),
    basesMixedCurrency: lineCurrencies(fr.value_bases).length > 1,
  };
}
