import { describe, expect, it } from "vitest";
import {
  canAdjustInventory,
  canReadInventory,
  canWriteInventory,
} from "./inventoryPermissions";
import {
  fundingStatusLabel,
  locationTypeLabel,
  movementTypeLabel,
  nationalizationStatusLabel,
  receiptStatusLabel,
  receiptTypeLabel,
  skuBucketLabel,
} from "./inventoryLabels";
import type { User } from "../auth/types";

const base: User = {
  id: 1,
  email: "a@b.c",
  name: "A",
  role: "estoque",
  permissions: ["inventory:read"],
};

describe("inventoryPermissions", () => {
  it("read/write/adjust gates", () => {
    expect(canReadInventory(base)).toBe(true);
    expect(canWriteInventory(base)).toBe(false);
    expect(canAdjustInventory(base)).toBe(false);
    expect(
      canWriteInventory({
        ...base,
        permissions: ["inventory:read", "inventory:write"],
      }),
    ).toBe(true);
    expect(canAdjustInventory({ ...base, role: "admin", permissions: [] })).toBe(true);
  });
});

describe("inventoryLabels", () => {
  it("sku buckets pt-BR", () => {
    expect(skuBucketLabel("available_qty")).toBe("Disponível");
    expect(skuBucketLabel("bonded_qty")).toBe("Entreposto");
    expect(skuBucketLabel("cleared_not_received_qty")).toBe("Liberado não recebido");
    expect(skuBucketLabel("future_order_qty")).toBe("Pedido futuro");
  });

  it("movement / receipt / location labels", () => {
    expect(movementTypeLabel("BONDED_IN")).toBe("Entrada entreposto");
    expect(movementTypeLabel("REVERSAL")).toBe("Estorno");
    expect(receiptTypeLabel("DOMESTIC_IN")).toBe("Entrada doméstica");
    expect(locationTypeLabel("BONDED")).toBe("Entreposto");
    expect(receiptStatusLabel("CONFIRMED")).toBe("Confirmado");
    expect(nationalizationStatusLabel("REVERSED")).toBe("Estornada");
    expect(fundingStatusLabel("DRAFT")).toBe("Rascunho");
  });
});
