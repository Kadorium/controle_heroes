import { describe, expect, it } from "vitest";
import { displayTitle, matchCatalogProduct, productIdentity, productIncomplete, skuLooksLikeGtin } from "./productIdentity";
import type { Product } from "./catalogApi";

function product(partial: Partial<Product> & Pick<Product, "sku" | "description">): Product {
  return {
    id: 1,
    is_active: true,
    ncm: null,
    ean: null,
    size: null,
    color: null,
    country_of_origin: null,
    unit: null,
    net_weight_kg: null,
    ...partial,
  } as Product;
}

describe("productIdentity", () => {
  it("usa o nome comercial como título e o SKU como subtítulo", () => {
    const idn = productIdentity(
      product({ sku: "SKU-1", description: "legado", commercial_name: "Bolsa vermelha", category_name: "Acessórios" }),
    );
    expect(idn.title).toBe("Bolsa vermelha");
    expect(idn.sub).toContain("SKU-1");
    expect(idn.sub).toContain("Acessórios");
    expect(idn.fallback).toBe(false);
    expect(displayTitle(product({ sku: "SKU-1", description: "Bolsa vermelha" }))).toBe("Bolsa vermelha");
  });

  it("cai no fallback quando a descrição é inútil", () => {
    expect(productIdentity(product({ sku: "SKU-9", description: "SKU-9" })).title).toBe("SKU-9");
    expect(productIdentity(product({ sku: "SKU-9", description: "Item" })).sub).toBe("Sem descrição comercial");
    expect(productIdentity(product({ sku: "SKU-9", description: "produto" })).fallback).toBe(true);
  });

  it("marca incompleto sem NCM ou EAN quando não há quality", () => {
    expect(productIncomplete(product({ sku: "A", description: "A", ncm: "61091000", ean: "1" }))).toBe(false);
    expect(productIncomplete(product({ sku: "A", description: "A", ncm: "61091000", ean: null }))).toBe(true);
  });

  it("usa quality.quality_incomplete quando o contrato PIM está presente", () => {
    expect(
      productIncomplete(
        product({
          sku: "A",
          description: "A",
          ncm: null,
          ean: null,
          quality: { quality_incomplete: false } as Product["quality"],
        }),
      ),
    ).toBe(false);
  });

  it("casa picker por SKU, EAN, nome ou resultado único", () => {
    const rows = [
      product({
        id: 1,
        sku: "HEROES-BT-ARION-2026",
        description: "#ARION 2026",
        commercial_name: "#ARION 2026",
        ean: "8052080572263",
      }),
      product({ id: 2, sku: "MDM-R-001", description: "Massa visual MDM 1", commercial_name: "Massa visual MDM 1" }),
    ];
    expect(matchCatalogProduct(rows, "HEROES-BT-ARION-2026")?.id).toBe(1);
    expect(matchCatalogProduct(rows, "8052080572263")?.id).toBe(1);
    expect(matchCatalogProduct(rows, "#ARION 2026")?.id).toBe(1);
    expect(matchCatalogProduct(rows, "ARION")?.id).toBe(1);
  });

  it("recusa SKU que é só o código de barras", () => {
    expect(skuLooksLikeGtin("8057628953586")).toBe(true);
    expect(skuLooksLikeGtin("ENSAIO-E9-SHOW")).toBe(false);
    expect(skuLooksLikeGtin("HEROES-BT-SHOW")).toBe(false);
  });
});
