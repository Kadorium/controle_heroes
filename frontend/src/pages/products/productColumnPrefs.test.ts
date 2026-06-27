import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  defaultVisibleColumns,
  loadVisibleColumns,
  saveVisibleColumns,
  toggleColumn,
} from "./productColumnPrefs";

describe("productColumnPrefs", () => {
  beforeEach(() => {
    const store: Record<string, string> = {};
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
    });
  });

  it("defaultVisibleColumns inclui colunas essenciais", () => {
    const cols = defaultVisibleColumns();
    expect(cols).toContain("sku");
    expect(cols).toContain("name");
    expect(cols).not.toContain("pending");
  });

  it("persiste preferência por usuário", () => {
    saveVisibleColumns(99, ["sku", "name", "qty_stock"]);
    expect(loadVisibleColumns(99)).toEqual(["sku", "name", "qty_stock"]);
    expect(loadVisibleColumns(100)).not.toEqual(["sku", "name", "qty_stock"]);
  });

  it("toggleColumn não deixa lista vazia", () => {
    const next = toggleColumn(["sku"], "sku");
    expect(next).toEqual(["sku"]);
  });
});
