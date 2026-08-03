import { describe, expect, it } from "vitest";

/** Mirror of PaymentDetailPage allocFingerprint — D3 idempotency intent keying. */
function allocFingerprint(
  lines: { payable_id: number; amount: string; expected_version: number }[],
) {
  return lines
    .map((l) => `${l.payable_id}:${l.amount}:${l.expected_version}`)
    .sort()
    .join("|");
}

describe("allocate idempotency fingerprint", () => {
  it("is stable for same payload regardless of order", () => {
    const a = allocFingerprint([
      { payable_id: 2, amount: "10", expected_version: 1 },
      { payable_id: 1, amount: "5", expected_version: 3 },
    ]);
    const b = allocFingerprint([
      { payable_id: 1, amount: "5", expected_version: 3 },
      { payable_id: 2, amount: "10", expected_version: 1 },
    ]);
    expect(a).toBe(b);
  });

  it("changes when amount changes", () => {
    const a = allocFingerprint([{ payable_id: 1, amount: "5", expected_version: 1 }]);
    const b = allocFingerprint([{ payable_id: 1, amount: "6", expected_version: 1 }]);
    expect(a).not.toBe(b);
  });
});
