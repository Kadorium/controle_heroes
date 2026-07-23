/** Totais de linha Invoice (DEC-SCONTO-ITEM) — espelha backend HALF_UP 2 casas. */

export type DiscountType = "NONE" | "UNIT_AMOUNT" | "PERCENT" | "";

export function money2(n: number): string {
  return (Math.round(n * 100) / 100).toFixed(2);
}

export function lineAmounts(input: {
  quantity: string;
  unit_price_gross: string | null | undefined;
  discount_type: DiscountType | null | undefined;
  discount_unit_amount?: string | null;
  discount_percent?: string | null;
}): { gross: string | null; discount: string | null; net: string | null } {
  const qty = Number(input.quantity);
  const price = Number(input.unit_price_gross ?? "");
  if (!Number.isFinite(qty) || !Number.isFinite(price) || !input.unit_price_gross) {
    return { gross: null, discount: null, net: null };
  }
  const gross = Math.round(qty * price * 100) / 100;
  const dt = (input.discount_type || "").toUpperCase();
  if (!dt) return { gross: money2(gross), discount: null, net: null };
  let disc = 0;
  if (dt === "NONE") disc = 0;
  else if (dt === "UNIT_AMOUNT") {
    const u = Number(input.discount_unit_amount ?? "");
    if (!Number.isFinite(u)) return { gross: money2(gross), discount: null, net: null };
    disc = Math.round(qty * u * 100) / 100;
  } else if (dt === "PERCENT") {
    const p = Number(input.discount_percent ?? "");
    if (!Number.isFinite(p)) return { gross: money2(gross), discount: null, net: null };
    disc = Math.round(gross * (p / 100) * 100) / 100;
  } else return { gross: money2(gross), discount: null, net: null };
  return { gross: money2(gross), discount: money2(disc), net: money2(gross - disc) };
}

export function previewPercentPayables(net: number, percents: number[]): string[] {
  const amounts: number[] = [];
  let allocated = 0;
  for (let i = 0; i < percents.length; i++) {
    if (i === percents.length - 1) {
      amounts.push(Math.round((net - allocated) * 100) / 100);
    } else {
      const part = Math.round(net * (percents[i] / 100) * 100) / 100;
      amounts.push(part);
      allocated += part;
    }
  }
  return amounts.map(money2);
}

export function canWriteBilling(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("billing:write");
}

export function canIssueBilling(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("billing:issue");
}
