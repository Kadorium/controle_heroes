import { describe, expect, it } from "vitest";
import { canReadFx, canRefreshFxQuote, canWriteFx, fmtFx } from "./fxApi";

describe("fx permissions and null display", () => {
  it("gates fx perms", () => {
    expect(canReadFx({ role: "admin", permissions: [] })).toBe(true);
    expect(canWriteFx({ role: "x", permissions: ["treasury:fx_write"] })).toBe(true);
    expect(canRefreshFxQuote({ role: "x", permissions: ["treasury:fx_quote_refresh"] })).toBe(true);
    expect(canReadFx({ role: "x", permissions: ["treasury:read"] })).toBe(false);
  });

  it("never shows 0 for missing", () => {
    expect(fmtFx(null)).toBe("—");
    expect(fmtFx(undefined)).toBe("—");
    expect(fmtFx("")).toBe("—");
    expect(fmtFx("-40.00")).toBe("-40.00");
  });
});
