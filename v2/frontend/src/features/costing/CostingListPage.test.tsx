import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CostingListPage } from "./CostingListPage";

vi.mock("./costingApi", () => ({
  listCostingQueue: () =>
    Promise.resolve([
      {
        id: null,
        import_process_id: 9,
        process_code: "IMP-1",
        process_reference: "DUIMP-X",
        process_status: "DRAFT",
        current_kind: null,
        current_status: null,
        included_total_brl: null,
        partial_coverage: null,
        updated_at: null,
      },
    ]),
  ensureCostingCase: vi.fn(),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: [] as string[],
};

afterEach(() => cleanup());

describe("CostingListPage", () => {
  it("mostra fila e subtítulo bruto", async () => {
    render(
      <MemoryRouter>
        <CostingListPage user={admin} />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("costing-queue")).toBeInTheDocument();
    expect(
      screen.getByText(/Não representa tratamento contábil ou fiscal de recuperabilidade/i),
    ).toBeInTheDocument();
    expect(screen.getByText("IMP-1")).toBeInTheDocument();
  });
});
