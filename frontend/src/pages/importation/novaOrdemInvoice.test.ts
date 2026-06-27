import { describe, expect, it } from "vitest";
import {
  canSubmitInvoiceAmount,
  extractInvoiceSuffix,
  nextInvoiceSuffix,
  orderRemainingToInvoice,
  resolveInvoiceAmount,
  suggestInvoiceNumber,
} from "./novaOrdemInvoice";

describe("suggestInvoiceNumber", () => {
  it("concatena PO e letra", () => {
    expect(suggestInvoiceNumber("760", "a")).toBe("760A");
  });
});

describe("nextInvoiceSuffix", () => {
  it("retorna A sem faturas", () => {
    expect(nextInvoiceSuffix([], "760")).toBe("A");
  });

  it("pula letras já usadas", () => {
    expect(
      nextInvoiceSuffix(
        [{ invoice_number: "760A" }, { invoice_number: "760B" }],
        "760",
      ),
    ).toBe("C");
  });
});

describe("extractInvoiceSuffix", () => {
  it("extrai letra do padrão PO+sufixo", () => {
    expect(extractInvoiceSuffix("760B", "760")).toBe("B");
    expect(extractInvoiceSuffix("PRO-760", "760")).toBeNull();
  });
});

describe("orderRemainingToInvoice", () => {
  it("calcula saldo a faturar", () => {
    expect(orderRemainingToInvoice(1000, 300)).toBe(700);
    expect(orderRemainingToInvoice(1000, null)).toBe(1000);
    expect(orderRemainingToInvoice(1000, 1200)).toBe(0);
    expect(orderRemainingToInvoice(null, 100)).toBeNull();
  });
});

describe("resolveInvoiceAmount", () => {
  it("EUR absoluto — fatura EUR e pagamento BRL", () => {
    const r = resolveInvoiceAmount("EUR", "100", 500, 6);
    expect(r.invoiceAmountOrderCurrency).toBe(100);
    expect(r.paymentAmountBrl).toBe(600);
    expect(r.previewBrl).toBe(600);
  });

  it("BRL absoluto — fatura EUR e pagamento BRL", () => {
    const r = resolveInvoiceAmount("BRL", "600", 500, 6);
    expect(r.invoiceAmountOrderCurrency).toBe(100);
    expect(r.paymentAmountBrl).toBe(600);
  });

  it("% EUR sobre saldo a faturar", () => {
    const r = resolveInvoiceAmount("PCT_EUR", "50", 700, 6);
    expect(r.invoiceAmountOrderCurrency).toBe(350);
    expect(r.paymentAmountBrl).toBe(2100);
  });

  it("% BRL sobre saldo a faturar", () => {
    const r = resolveInvoiceAmount("PCT_BRL", "10", 1000, 5);
    expect(r.paymentAmountBrl).toBe(500);
    expect(r.invoiceAmountOrderCurrency).toBe(100);
  });
});

describe("canSubmitInvoiceAmount", () => {
  it("bloqueia sem taxa ou valor", () => {
    expect(canSubmitInvoiceAmount("EUR", "", 500, 6)).toBe(false);
    expect(canSubmitInvoiceAmount("EUR", "100", 500, null)).toBe(false);
    expect(canSubmitInvoiceAmount("PCT_EUR", "50", null, 6)).toBe(false);
    expect(canSubmitInvoiceAmount("EUR", "100", 500, 6)).toBe(true);
  });
});
