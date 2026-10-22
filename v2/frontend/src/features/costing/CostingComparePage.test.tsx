import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CostingComparePage } from "./CostingComparePage";

vi.mock("./costingApi", () => ({
  compareCostingVersions: () =>
    Promise.resolve({
      left: {
        id: 2,
        case_id: 2,
        version_number: 1,
        kind: "REVISED",
        status: "SUPERSEDED",
        included_total_brl: "12100.0000",
        published_at: "2026-08-20T12:00:00Z",
      },
      right: {
        id: 4,
        case_id: 2,
        version_number: 2,
        kind: "REVISED",
        status: "PUBLISHED",
        included_total_brl: "12150.0000",
        published_at: "2026-08-20T14:00:00Z",
      },
      components: [
        {
          component_type: "MERCADORIA",
          source_kind: "INVOICE",
          left_amount_brl: "12000.0000",
          right_amount_brl: "12000.0000",
          left_included: true,
          right_included: true,
        },
        {
          component_type: "EXPENSE_COSTING_OUTRAS",
          source_kind: "COSTING_EXPENSE",
          left_amount_brl: null,
          right_amount_brl: "50.0000",
          left_included: null,
          right_included: true,
        },
      ],
      products: [
        {
          sku_snapshot: "MOCK-A",
          product_id: 1,
          description_snapshot: "Mock A",
          left_qty: "10",
          right_qty: "10",
          left_total_brl: "6050.00",
          right_total_brl: "6075.00",
          left_unit_brl: "605.00",
          right_unit_brl: "607.50",
        },
      ],
    }),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: [] as string[],
};

afterEach(() => cleanup());

describe("CostingComparePage", () => {
  it("mostra delta e filtra apenas diferenças", async () => {
    render(
      <MemoryRouter initialEntries={["/costing/2/compare?left=2&right=4"]}>
        <Routes>
          <Route path="/costing/:caseId/compare" element={<CostingComparePage user={admin} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("costing-compare-page")).toBeInTheDocument();
    expect(screen.getByTestId("costing-compare-total-delta")).toHaveTextContent(/50,00/);
    const comps = screen.getByTestId("costing-compare-components");
    expect(comps.textContent).toMatch(/Mercadoria/);
    expect(comps.textContent).toMatch(/Despesa/);
    fireEvent.click(screen.getByTestId("costing-compare-diffs-only"));
    expect(screen.getByTestId("costing-compare-components").textContent).not.toMatch(/Mercadoria/);
    expect(screen.getByTestId("costing-compare-components").textContent).toMatch(/Despesa/);
  });
});
