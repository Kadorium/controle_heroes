import { describe, expect, it } from "vitest";
import { canAllocateTreasury, canWriteTreasury } from "./treasuryApi";

describe("treasury permissions", () => {
  it("gates write/allocate", () => {
    expect(canWriteTreasury({ role: "admin", permissions: [] })).toBe(true);
    expect(canAllocateTreasury({ role: "x", permissions: ["treasury:allocate"] })).toBe(true);
    expect(canWriteTreasury({ role: "x", permissions: ["treasury:read"] })).toBe(false);
  });
});
