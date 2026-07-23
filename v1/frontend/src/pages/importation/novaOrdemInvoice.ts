import { eurToBrl, parseDecimalInput } from "./novaOrdemTotals";

export type InvoiceAmountMode = "EUR" | "BRL" | "PCT_EUR" | "PCT_BRL";

export interface InvoiceListItem {
  invoice_number: string;
}

export interface ResolvedInvoiceAmount {
  previewEur: number | null;
  previewBrl: number | null;
  /** Valor da fatura na moeda da ordem (EUR). */
  invoiceAmountOrderCurrency: number | null;
  /** Pagamento planejado operacional — sempre BRL. */
  paymentAmountBrl: number | null;
}

/** Saldo a faturar em EUR: total da ordem − já faturado. */
export function orderRemainingToInvoice(
  orderNetEur: number | null,
  totalInvoicedEur: number | null,
): number | null {
  if (orderNetEur === null) return null;
  const invoiced = totalInvoicedEur ?? 0;
  return Math.max(0, orderNetEur - invoiced);
}

export function suggestInvoiceNumber(po: string, suffix: string): string {
  const base = po.trim();
  if (!base) return "";
  return `${base}${suffix.toUpperCase()}`;
}

export function extractInvoiceSuffix(invoiceNumber: string, po: string): string | null {
  const base = po.trim();
  const num = invoiceNumber.trim();
  if (!base || num.length !== base.length + 1) return null;
  if (!num.startsWith(base)) return null;
  const ch = num[base.length]?.toUpperCase();
  return ch && /^[A-Z]$/.test(ch) ? ch : null;
}

export function nextInvoiceSuffix(existingInvoices: InvoiceListItem[], po: string): string {
  const used = new Set<string>();
  for (const inv of existingInvoices) {
    const suffix = extractInvoiceSuffix(inv.invoice_number, po);
    if (suffix) used.add(suffix);
  }
  for (let code = 65; code <= 90; code++) {
    const letter = String.fromCharCode(code);
    if (!used.has(letter)) return letter;
  }
  return "Z";
}

function emptyResolved(): ResolvedInvoiceAmount {
  return {
    previewEur: null,
    previewBrl: null,
    invoiceAmountOrderCurrency: null,
    paymentAmountBrl: null,
  };
}

/**
 * Resolve fatura (EUR) e pagamento planejado (BRL).
 * @param baseEur — base para %: total líquido (Nova Ordem) ou saldo a faturar (Central).
 */
export function resolveInvoiceAmount(
  mode: InvoiceAmountMode,
  raw: string,
  baseEur: number | null,
  provisionRate: number | null,
): ResolvedInvoiceAmount {
  const val = parseDecimalInput(raw);
  if (val === null) return emptyResolved();

  const brlBase = eurToBrl(baseEur, provisionRate);

  switch (mode) {
    case "EUR": {
      if (provisionRate === null) {
        return {
          previewEur: val,
          previewBrl: null,
          invoiceAmountOrderCurrency: val,
          paymentAmountBrl: null,
        };
      }
      const brl = val * provisionRate;
      return {
        previewEur: val,
        previewBrl: brl,
        invoiceAmountOrderCurrency: val,
        paymentAmountBrl: brl,
      };
    }
    case "BRL": {
      if (provisionRate === null) {
        return {
          previewEur: null,
          previewBrl: val,
          invoiceAmountOrderCurrency: null,
          paymentAmountBrl: val,
        };
      }
      const eur = val / provisionRate;
      return {
        previewEur: eur,
        previewBrl: val,
        invoiceAmountOrderCurrency: eur,
        paymentAmountBrl: val,
      };
    }
    case "PCT_EUR": {
      if (baseEur === null) return emptyResolved();
      const eur = (baseEur * val) / 100;
      if (provisionRate === null) {
        return {
          previewEur: eur,
          previewBrl: null,
          invoiceAmountOrderCurrency: eur,
          paymentAmountBrl: null,
        };
      }
      const brl = eur * provisionRate;
      return {
        previewEur: eur,
        previewBrl: brl,
        invoiceAmountOrderCurrency: eur,
        paymentAmountBrl: brl,
      };
    }
    case "PCT_BRL": {
      if (brlBase === null) return emptyResolved();
      const brl = (brlBase * val) / 100;
      if (provisionRate === null) {
        return {
          previewEur: null,
          previewBrl: brl,
          invoiceAmountOrderCurrency: null,
          paymentAmountBrl: brl,
        };
      }
      const eur = brl / provisionRate;
      return {
        previewEur: eur,
        previewBrl: brl,
        invoiceAmountOrderCurrency: eur,
        paymentAmountBrl: brl,
      };
    }
    default:
      return emptyResolved();
  }
}

/** Bloqueia submit se faltar taxa ou valor resolvido (nunca zero implícito). */
export function canSubmitInvoiceAmount(
  mode: InvoiceAmountMode,
  raw: string,
  baseEur: number | null,
  provisionRate: number | null,
): boolean {
  if (!raw.trim()) return false;
  if (provisionRate === null) return false;
  if ((mode === "PCT_EUR" || mode === "PCT_BRL") && baseEur === null) return false;
  const r = resolveInvoiceAmount(mode, raw, baseEur, provisionRate);
  return r.invoiceAmountOrderCurrency !== null && r.paymentAmountBrl !== null;
}

export const INVOICE_AMOUNT_MODES: {
  id: InvoiceAmountMode;
  label: string;
  short: string;
  inputSuffix?: string;
}[] = [
  { id: "EUR", label: "Valor em EUR", short: "EUR" },
  { id: "BRL", label: "Valor em BRL", short: "BRL" },
  { id: "PCT_EUR", label: "% do saldo a faturar (EUR)", short: "% EUR", inputSuffix: "%" },
  { id: "PCT_BRL", label: "% do saldo a faturar (BRL)", short: "% BRL", inputSuffix: "%" },
];
