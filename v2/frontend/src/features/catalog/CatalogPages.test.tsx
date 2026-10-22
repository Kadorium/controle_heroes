import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProductListPage } from "./ProductListPage";

vi.mock("../../navigation/useListReturn", () => ({
  useListReturn: () => undefined,
}));

vi.mock("./catalogApi", () => ({
  fetchProductList: vi.fn(async () => ({
    items: [{ id: 9, sku: "SKU-Z", description: "Fora dos 50", commercial_name: "Fora dos 50", is_active: true, ncm: null, ean: null }],
    total: 61,
    limit: 50,
    offset: 0,
    summary: {
      total: 61,
      incomplete: 12,
      missing_ncm: 8,
      needs_review: 3,
      needs_product_review: 3,
      needs_classification_review: 1,
      short_generic: 2,
      missing_image: 61,
      quality_incomplete: 12,
    },
    facets: {},
  })),
  fetchProductAttributeValues: vi.fn(async () => []),
  fetchSupplierList: vi.fn(async () => ({ items: [], total: 0, limit: 1, offset: 0 })),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: ["catalog:read", "catalog:write"],
};

describe("ProductListPage", () => {
  it("mostra identidade humana, KPIs e busca live sem botão Buscar", async () => {
    render(
      <MemoryRouter>
        <ProductListPage user={admin} />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("product-list-page")).toBeInTheDocument();
    expect(screen.getByText("Fora dos 50")).toBeInTheDocument();
    expect(screen.getAllByText(/SKU-Z/).length).toBeGreaterThan(0);
    expect(screen.getByTestId("kpi-inline")).toHaveTextContent("61 produtos");
    expect(screen.getByTestId("products-new-cta")).toHaveAttribute("href", "/catalog/products/new");
    expect(screen.getByTestId("products-next-page")).toBeInTheDocument();
    expect(screen.getByTestId("catalog-overflow")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^buscar$/i })).toBeNull();
    expect(screen.queryByText(/^sim$/i)).toBeNull();
    expect(screen.queryByText(/^não$/i)).toBeNull();
  });
});
