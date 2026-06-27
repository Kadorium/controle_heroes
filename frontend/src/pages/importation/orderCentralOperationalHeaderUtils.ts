import type { ImportationItem, OperationalHeader, OrderCentralInvoice, OrderCentralModel } from "../../api";

export interface ItemPreviewRow {
  key: string;
  label: string;
  qty: number | null;
  unitPrice: string | null;
  paid: string | null;
}

export function normalizeItemLabel(label: string): string {
  return label.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function pick(...vals: (string | null | undefined)[]): string | null {
  for (const v of vals) {
    if (v != null && v !== "") return v;
  }
  return null;
}

function lineValue(row: Pick<ItemPreviewRow, "qty" | "unitPrice" | "paid">): string | null {
  if (row.paid != null && row.paid !== "") return row.paid;
  if (row.qty != null && row.unitPrice != null) {
    return String(Number(row.qty) * Number(row.unitPrice));
  }
  return null;
}

function mergePreviewRows(existing: ItemPreviewRow, incoming: ItemPreviewRow): ItemPreviewRow {
  const qtyA = existing.qty ?? 0;
  const qtyB = incoming.qty ?? 0;
  const totalQty = qtyA + qtyB;

  let unitPrice = existing.unitPrice;
  if (existing.unitPrice && incoming.unitPrice && totalQty > 0) {
    unitPrice = String(
      (Number(existing.unitPrice) * qtyA + Number(incoming.unitPrice) * qtyB) / totalQty,
    );
  } else {
    unitPrice = existing.unitPrice ?? incoming.unitPrice;
  }

  const valA = lineValue(existing);
  const valB = lineValue(incoming);
  let paid: string | null = null;
  if (valA != null && valB != null) {
    paid = String(Number(valA) + Number(valB));
  } else {
    paid = valA ?? valB;
  }

  return {
    key: existing.key,
    label: existing.label.length >= incoming.label.length ? existing.label : incoming.label,
    qty: totalQty > 0 ? totalQty : existing.qty ?? incoming.qty,
    unitPrice,
    paid,
  };
}

export function aggregateItemPreviewRows(rows: ItemPreviewRow[]): ItemPreviewRow[] {
  const byLabel = new Map<string, ItemPreviewRow>();
  for (const row of rows) {
    const key = normalizeItemLabel(row.label) || row.key;
    const existing = byLabel.get(key);
    byLabel.set(key, existing ? mergePreviewRows(existing, row) : { ...row, key });
  }
  return Array.from(byLabel.values());
}

export function buildItemPreviewRows(
  models: OrderCentralModel[] | undefined,
  items: ImportationItem[] | undefined,
  invoices: OrderCentralInvoice[] | undefined,
): ItemPreviewRow[] {
  const itemById = new Map((items ?? []).map((i) => [i.id, i]));
  const seen = new Set<number>();
  const rows: ItemPreviewRow[] = [];

  const pushRow = (row: Omit<ItemPreviewRow, "key"> & { key: number }) => {
    if (seen.has(row.key)) return;
    seen.add(row.key);
    rows.push({
      key: String(row.key),
      label: row.label,
      qty: row.qty,
      unitPrice: row.unitPrice,
      paid: row.paid,
    });
  };

  if (models && models.length > 0) {
    for (const m of models) {
      pushRow({
        key: m.importation_item_id,
        label: m.model_label ?? m.description ?? m.supplier_sku ?? m.product_sku ?? "—",
        qty: m.quantity_ordered,
        unitPrice: m.price_fattura ?? itemById.get(m.importation_item_id)?.unit_price_foreign ?? null,
        paid: m.acconto_amount ?? null,
      });
    }
  }

  for (const it of items ?? []) {
    pushRow({
      key: it.id,
      label: it.description ?? it.supplier_sku ?? "—",
      qty: it.quantity_ordered,
      unitPrice: it.unit_price_foreign ?? null,
      paid: null,
    });
  }

  for (const inv of invoices ?? []) {
    for (const ii of inv.items ?? []) {
      const key = ii.importation_item_id ?? ii.id;
      pushRow({
        key,
        label: ii.description ?? ii.product_sku ?? inv.invoice_number,
        qty: ii.quantity,
        unitPrice: ii.unit_price != null ? String(ii.unit_price) : null,
        paid: ii.amount != null ? String(ii.amount) : inv.paid_total != null ? String(inv.paid_total) : null,
      });
    }
  }

  return aggregateItemPreviewRows(rows);
}

function brlFromEur(eur: string | null, rate: number | null): string | null {
  if (eur == null || rate == null || Number.isNaN(rate)) return null;
  return String(Number(eur) * rate);
}

export interface ResolvedFinance {
  opening: string | null;
  currentRate: number | null;
  orderTotalEur: string | null;
  orderTotalBrl: string | null;
  invoicedEur: string | null;
  invoicedBrl: string | null;
  settledEur: string | null;
  settledBrl: string | null;
  remainingEur: string | null;
  remainingBrl: string | null;
  balanceEur: string | null;
  balanceBrl: string | null;
  brlHint: string;
}

export function resolveFinance(
  header: OperationalHeader,
  estimatedTotal?: string | null,
  versatoTotal?: string | null,
): ResolvedFinance {
  const eur = header.totals_by_currency?.EUR;
  const opening = header.opening_exchange_rate ?? null;
  const markRateRaw = header.fx_pnl?.mark_rate ?? null;
  const currentRateNum = (() => {
    const candidates = [markRateRaw, opening];
    for (const raw of candidates) {
      if (raw == null || raw === "") continue;
      const n = Number(String(raw).replace(",", "."));
      if (!Number.isNaN(n) && n > 0) return n;
    }
    return null;
  })();

  const settledEur = pick(header.settled_eur, header.total_paid, eur?.total_paid);
  const balanceEur = pick(header.balance_to_settle_eur, header.open_balance, eur?.consolidated_balance);
  const invoicedEur = pick(header.invoiced_eur, header.total_invoiced, eur?.total_invoiced);

  const orderTotalEur = pick(
    header.order_total_eur,
    estimatedTotal,
    versatoTotal,
    invoicedEur && balanceEur != null
      ? String(Number(invoicedEur) + Number(balanceEur))
      : null,
    settledEur && balanceEur != null
      ? String(Number(settledEur) + Number(balanceEur))
      : null,
    settledEur,
  );

  const orderTotalBrl = pick(
    header.order_total_brl,
    brlFromEur(orderTotalEur, currentRateNum),
  );

  const invoicedBrl = pick(
    header.invoiced_brl,
    brlFromEur(invoicedEur, currentRateNum),
  );

  const settledBrl = pick(header.settled_brl, brlFromEur(settledEur, currentRateNum));

  const remainingEur = pick(
    header.remaining_to_invoice_eur,
    orderTotalEur && invoicedEur
      ? String(Math.max(0, Number(orderTotalEur) - Number(invoicedEur)))
      : null,
  );
  const remainingBrl = pick(
    header.remaining_to_invoice_brl,
    brlFromEur(remainingEur, currentRateNum),
  );

  const avgInvRate =
    invoicedEur && invoicedBrl && Number(invoicedEur) > 0
      ? Number(invoicedBrl) / Number(invoicedEur)
      : currentRateNum;
  const balanceBrl = pick(
    header.balance_to_settle_brl,
    header.open_balance_brl_equivalent,
    balanceEur && avgInvRate != null ? String(Number(balanceEur) * avgInvRate) : null,
    brlFromEur(balanceEur, currentRateNum),
  );

  const brlHint =
    markRateRaw != null
      ? `estimativa pelo câmbio atual ${markRateRaw}`
      : opening
        ? `estimativa pelo câmbio abertura ${opening}`
        : "estimativa cambial";

  return {
    opening,
    currentRate: currentRateNum,
    orderTotalEur,
    orderTotalBrl,
    invoicedEur,
    invoicedBrl,
    settledEur,
    settledBrl,
    remainingEur,
    remainingBrl,
    balanceEur,
    balanceBrl,
    brlHint,
  };
}

export function estimateItemPreviewRowCount(
  columnHeightPx: number,
  paddingVerticalPx: number,
  footerHeightPx: number,
  theadHeightPx: number,
  rowHeightPx: number,
): number {
  const available = columnHeightPx - paddingVerticalPx - footerHeightPx - theadHeightPx - 4;
  if (available <= 0 || rowHeightPx <= 0) return 1;
  return Math.max(1, Math.floor(available / rowHeightPx));
}
