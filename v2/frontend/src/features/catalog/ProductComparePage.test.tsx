import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProductComparePage } from "./ProductComparePage";
import type { Product } from "./catalogApi";

vi.mock("./catalogApi", () => ({
  getProduct: vi.fn(async (id: number) => {
    const base = {
      is_active: true,
      sku: id === 1 ? "HEROES-BT-HARLEY-2024" : "HEROES-BT-HARLEY-2025",
      description: id === 1 ? "#HARLEY 2024" : "#HARLEY 2025",
      commercial_name: id === 1 ? "#HARLEY 2024" : "#HARLEY 2025",
      category_name: "Raquetes",
      subcategory: "Beach Tennis",
      product_type_name: "Raquete",
      sport: "BEACH TENNIS",
      model: "HARLEY",
      collection_year: id === 1 ? "2024" : "2025",
      color: null,
      gender: null,
      line: null,
    };
    return { id, ...base } as Product;
  }),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: ["catalog:read"],
};

describe("ProductComparePage", () => {
  it("destaca coleção diferente e modelo igual", async () => {
    render(
      <MemoryRouter initialEntries={["/catalog/products/compare?ids=1,2"]}>
        <Routes>
          <Route path="/catalog/products/compare" element={<ProductComparePage user={admin} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("product-compare-page")).toBeInTheDocument();
    const table = screen.getByTestId("compare-table");
    expect(table).toHaveTextContent("HARLEY");
    expect(table).toHaveTextContent("2024");
    expect(table).toHaveTextContent("2025");
    const diffRows = [...table.querySelectorAll("tr.compare-diff")].map((row) => row.textContent || "");
    expect(diffRows.some((text) => text.includes("Coleção"))).toBe(true);
    expect(table.textContent).toContain("HARLEY");
    fireEvent.click(screen.getByTestId("compare-diffs-only"));
    expect(screen.queryByText("Modelo")).toBeNull();
    expect(screen.getByText("Coleção")).toBeInTheDocument();
  });
});
