import { describe, expect, it } from "vitest";
import { formatDateOnly, formatDateTime, formatMoney, formatRate, compactQuantityWire, formatQuantity } from "./format";
import { resolveStatus, statusLabel, statusSemantics } from "./statusLabels";

describe("formatMoney", () => {
  it("formata EUR/BRL com código e pt-BR", () => {
    expect(formatMoney("400.0000", "EUR")).toBe("EUR 400,00");
    expect(formatMoney("1250.5", "BRL")).toBe("BRL 1.250,50");
    expect(formatMoney(1000, "EUR")).toBe("EUR 1.000,00");
  });

  it("preserva zero real e ausência", () => {
    expect(formatMoney("0", "EUR")).toBe("EUR 0,00");
    expect(formatMoney(0, "EUR")).toBe("EUR 0,00");
    expect(formatMoney(null, "EUR")).toBe("—");
    expect(formatMoney(undefined)).toBe("—");
    expect(formatMoney("")).toBe("—");
  });

  it("não usa símbolo de moeda nem prefixo duplicado", () => {
    const text = formatMoney("400", "EUR");
    expect(text).not.toMatch(/€|\$/);
    expect(text).toBe("EUR 400,00");
  });
});

describe("formatRate", () => {
  it("usa precisão própria (4 casas)", () => {
    expect(formatRate("6.2180")).toBe("6,2180");
    expect(formatRate(5.8268)).toBe("5,8268");
  });

  it("ausência = —", () => {
    expect(formatRate(null)).toBe("—");
    expect(formatRate("")).toBe("—");
  });
});

describe("formatDateOnly", () => {
  it("converte YYYY-MM-DD sem shift UTC", () => {
    expect(formatDateOnly("2026-07-23")).toBe("23/07/2026");
    expect(formatDateOnly("2026-07-23T00:00:00Z")).toBe("23/07/2026");
  });

  it("ausência = —", () => {
    expect(formatDateOnly(null)).toBe("—");
    expect(formatDateOnly("")).toBe("—");
  });
});

describe("formatDateTime", () => {
  it("exibe data/hora e timezone quando presente", () => {
    expect(formatDateTime("2026-07-29T16:46:40.332581-03:00")).toBe(
      "29/07/2026 16:46:40 -03:00",
    );
    expect(formatDateTime("2026-07-29T16:46:40Z")).toBe("29/07/2026 16:46:40 UTC");
  });
});

describe("compactQuantityWire", () => {
  it("remove zeros à direita do wire decimal", () => {
    expect(compactQuantityWire("10.0000")).toBe("10");
    expect(compactQuantityWire("2.0000")).toBe("2");
    expect(compactQuantityWire("10.5000")).toBe("10.5");
    expect(compactQuantityWire("10")).toBe("10");
    expect(compactQuantityWire(null)).toBe("");
    expect(formatQuantity("10.0000")).toBe("10");
    expect(formatQuantity("10.5")).toBe("10,5");
  });
});

describe("statusLabels por entidade", () => {
  it("mapeia Order / Invoice / Payment / Payable", () => {
    expect(statusLabel("CONFIRMED", "order")).toBe("Confirmado");
    expect(statusLabel("ISSUED", "invoice")).toBe("Emitida");
    expect(statusLabel("CANCELLED", "invoice")).toBe("Cancelada");
    expect(statusLabel("REGISTERED", "payment")).toBe("Registrado");
    expect(statusLabel("PARTIALLY_PAID", "payable")).toBe("Parcialmente pago");
  });

  it("semântica DS aprovada", () => {
    expect(statusSemantics("REGISTERED", "payment")).toBe("information");
    expect(statusSemantics("CONFIRMED", "order")).toBe("success");
    expect(statusSemantics("OVERDUE", "payable")).toBe("danger");
    expect(statusSemantics("DRAFT", "order")).toBe("neutral");
    expect(statusSemantics("PARTIALLY_PAID", "payable")).toBe("warning");
  });

  it("INITIAL permanece técnico em FX", () => {
    expect(resolveStatus("INITIAL", "fx")).toEqual({
      label: "INITIAL",
      semantics: "neutral",
    });
  });
});
