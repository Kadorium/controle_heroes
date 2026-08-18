import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProductListPage } from "./ProductListPage";

vi.mock("../../navigation/useListReturn", () => ({
  useListReturn: () => undefined,
}));

vi.mock("./catalogApi", () => ({
  fetchProductList: vi.fn(async () => ({
    items: [{ id: 9, sku: "SKU-Z", description: "Fora dos 50", is_active: true, ncm: null }],
    total: 61,
    limit: 50,
    offset: 0,
  })),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: ["catalog:read", "catalog:write"],
};

describe("ProductListPage", () => {
  it("mostra envelope de lista e CTA de novo produto", async () => {
    render(
      <MemoryRouter>
        <ProductListPage user={admin} />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("product-list-page")).toBeInTheDocument();
    expect(screen.getByText("SKU-Z")).toBeInTheDocument();
    expect(screen.getByTestId("products-new-cta")).toHaveAttribute("href", "/catalog/products/new");
    expect(screen.getByTestId("products-next-page")).toBeInTheDocument();
  });
});
