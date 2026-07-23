/** Totais comerciais derivados (espelha regra backend). */
export function deriveLineTotal(quantity: string, unitPrice: string | null | undefined): string | null {
  const q = quantity.trim();
  const p = (unitPrice ?? "").trim();
  if (!q || !p) return null;
  const qn = Number(q);
  const pn = Number(p);
  if (!Number.isFinite(qn) || !Number.isFinite(pn)) return null;
  return (qn * pn).toFixed(4);
}

export function summarizeLines(
  lines: { quantity: string; unit_price: string | null | undefined }[],
): { priced_subtotal: string | null; unpriced_item_count: number; commercial_total: string | null } {
  if (lines.length === 0) {
    return { priced_subtotal: null, unpriced_item_count: 0, commercial_total: null };
  }
  let priced = 0;
  let anyPriced = false;
  let unpriced = 0;
  for (const line of lines) {
    const lt = deriveLineTotal(line.quantity, line.unit_price);
    if (lt === null) unpriced += 1;
    else {
      anyPriced = true;
      priced += Number(lt);
    }
  }
  const priced_subtotal = anyPriced ? priced.toFixed(4) : null;
  const commercial_total = unpriced === 0 && anyPriced ? priced_subtotal : null;
  return { priced_subtotal, unpriced_item_count: unpriced, commercial_total };
}

export function canWriteOrders(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("orders:write");
}

export function canCancelOrders(user: { role: string; permissions: string[] }) {
  return user.role === "admin" || user.permissions.includes("orders:cancel");
}
