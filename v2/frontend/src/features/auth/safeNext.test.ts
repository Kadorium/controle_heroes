import { describe, expect, it } from "vitest";
import { loginUrlWithNext, sanitizeNextPath } from "./safeNext";

describe("sanitizeNextPath", () => {
  it("fallback para ausente ou vazio", () => {
    expect(sanitizeNextPath(null)).toBe("/orders");
    expect(sanitizeNextPath("")).toBe("/orders");
    expect(sanitizeNextPath("   ")).toBe("/orders");
  });

  it("aceita paths internos com query", () => {
    expect(sanitizeNextPath("/payables")).toBe("/payables");
    expect(sanitizeNextPath("/payments/new?supplier_id=1")).toBe("/payments/new?supplier_id=1");
    expect(sanitizeNextPath("%2Forders%2F12")).toBe("/orders/12");
  });

  it("rejeita externos e protocol-relative", () => {
    expect(sanitizeNextPath("https://evil.example/phish")).toBe("/orders");
    expect(sanitizeNextPath("//evil.example")).toBe("/orders");
    expect(sanitizeNextPath("/\\evil")).toBe("/orders");
    expect(sanitizeNextPath("javascript:alert(1)")).toBe("/orders");
  });

  it("evita loop em /login", () => {
    expect(sanitizeNextPath("/login")).toBe("/orders");
    expect(sanitizeNextPath("/login?next=/orders")).toBe("/orders");
  });
});

describe("loginUrlWithNext", () => {
  it("codifica destino", () => {
    expect(loginUrlWithNext("/payables", "?status=OPEN")).toBe(
      "/login?next=%2Fpayables%3Fstatus%3DOPEN",
    );
  });

  it("não aninha login", () => {
    expect(loginUrlWithNext("/login")).toBe("/login");
  });
});
