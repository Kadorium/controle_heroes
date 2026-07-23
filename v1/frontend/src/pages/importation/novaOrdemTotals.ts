/**
 * Totais do modal Nova Ordem — mesma regra do backend: vazio = null, nunca 0 implícito.
 * Desconto na linha é **por unidade** (€/un), não desconto bruto no total.
 */

export interface ItemTotalsInput {
  quantity_ordered: string;
  unit_price_foreign: string;
  discount_amount_foreign: string;
}

export interface LineTotals {
  /** qtd × preço unitário (antes do desconto). */
  gross: number | null;
  /** qtd × desconto unitário. */
  discount: number | null;
  /** gross − discount. */
  net: number | null;
}

export interface AggregateTotals {
  gross: number | null;
  discounts: number | null;
  net: number | null;
  quantity: number | null;
}

/** Campo vazio ou inválido → null (não zero). */
export function parseDecimalInput(raw: string): number | null {
  const t = raw.trim();
  if (!t) return null;
  const n = Number(t.replace(",", "."));
  if (Number.isNaN(n)) return null;
  return n;
}

export function lineTotals(item: ItemTotalsInput): LineTotals {
  const qty = parseDecimalInput(item.quantity_ordered);
  const price = parseDecimalInput(item.unit_price_foreign);
  const discountPerUnit = parseDecimalInput(item.discount_amount_foreign);

  const gross = qty !== null && price !== null ? qty * price : null;
  const discount =
    qty !== null && discountPerUnit !== null ? qty * discountPerUnit : null;
  const net =
    gross !== null ? gross - (discount !== null ? discount : 0) : null;

  return { gross, discount, net };
}

export function aggregateTotals(items: ItemTotalsInput[]): AggregateTotals {
  let gross = 0;
  let discounts = 0;
  let net = 0;
  let quantity = 0;
  let hasGross = false;
  let hasDiscount = false;
  let hasNet = false;
  let hasQty = false;

  for (const item of items) {
    const line = lineTotals(item);
    if (line.gross !== null) {
      gross += line.gross;
      hasGross = true;
    }
    if (line.discount !== null) {
      discounts += line.discount;
      hasDiscount = true;
    }
    if (line.net !== null) {
      net += line.net;
      hasNet = true;
    }
    const qty = parseDecimalInput(item.quantity_ordered);
    if (qty !== null) {
      quantity += qty;
      hasQty = true;
    }
  }

  return {
    gross: hasGross ? gross : null,
    discounts: hasDiscount ? discounts : null,
    net: hasNet ? net : null,
    quantity: hasQty ? quantity : null,
  };
}

export function itemHasContent(
  item: ItemTotalsInput & { sku_code?: string; description?: string; product_id?: number | null },
): boolean {
  return Boolean(
    item.product_id ||
      (item.sku_code ?? "").trim() ||
      (item.description ?? "").trim() ||
      parseDecimalInput(item.quantity_ordered) !== null ||
      parseDecimalInput(item.unit_price_foreign) !== null ||
      parseDecimalInput(item.discount_amount_foreign) !== null,
  );
}

/** Converte EUR → BRL com taxa; null se faltar dado. */
export function eurToBrl(eur: number | null, rate: number | null): number | null {
  if (eur === null || rate === null) return null;
  return eur * rate;
}

/** Aplica mark-up % sobre taxa base. */
export function rateWithMarkup(baseRate: number | null, markupPct: number | null): number | null {
  if (baseRate === null) return null;
  const m = markupPct ?? 0;
  return baseRate * (1 + m / 100);
}
