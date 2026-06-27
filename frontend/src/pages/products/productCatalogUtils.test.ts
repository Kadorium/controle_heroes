import { describe, expect, it } from "vitest";
import type { Product } from "../../api";
import {
  bulkEligible,
  canArchive,
  canCancel,
  formatBulkResult,
  PENDING_LABELS,
  sortProducts,
  STATUS_LABELS,
} from "./productCatalogUtils";

const sample: Product[] = [
  { id: 2, sku_code: "B", description: "Beta", is_active: true, product_group: "G2", lifecycle_status: "ACTIVE" },
  { id: 1, sku_code: "A", description: "Alpha", is_active: true, product_group: "G1", lifecycle_status: "DISCONTINUED" },
];

describe("productCatalogUtils", () => {
  it("sortProducts by sku asc", () => {
    const out = sortProducts(sample, "sku_code", true);
    expect(out[0].sku_code).toBe("A");
  });

  it("sortProducts by sku desc", () => {
    const out = sortProducts(sample, "sku_code", false);
    expect(out[0].sku_code).toBe("B");
  });

  it("bulkEligible archive skips archived", () => {
    const archived: Product = { ...sample[0], id: 3, lifecycle_status: "ARCHIVED" };
    const r = bulkEligible([sample[0], archived], "archive");
    expect(r.eligible).toHaveLength(1);
    expect(r.ineligible).toHaveLength(1);
  });

  it("bulkEligible discontinue only active", () => {
    const r = bulkEligible(sample, "discontinue");
    expect(r.eligible.map((p) => p.id)).toEqual([2]);
    expect(r.ineligible.map((p) => p.id)).toEqual([1]);
  });

  it("canCancel requires active", () => {
    expect(canCancel({ ...sample[0], is_active: false })).toBe(false);
    expect(canArchive({ ...sample[0], lifecycle_status: "ARCHIVED" })).toBe(false);
  });

  it("formatBulkResult summarizes", () => {
    expect(formatBulkResult({ succeeded: [1, 2], skipped: [{ id: 3, reason: "x" }], failed: [] })).toContain("2 ok");
  });

  it("labels exist for pending flags", () => {
    expect(PENDING_LABELS.ncm_pending).toBeTruthy();
    expect(STATUS_LABELS.DISCONTINUED).toBeTruthy();
  });
});
