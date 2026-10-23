import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CostingWorkspacePage } from "./CostingWorkspacePage";

const version = {
  id: 3,
  case_id: 2,
  kind: "REVISED",
  status: "DRAFT",
  version_number: 2,
  partial_coverage: false,
  included_total_brl: "12100.0000",
  gross_total_brl: "12100.0000",
  title: "Custo desembarcado por produto",
  subtitle: "subtítulo",
  pairs: [],
  products: [
    { sku_snapshot: "MOCK-A", qty: "10", total_brl: "6050.00", unit_brl: "605.00" },
    { sku_snapshot: "MOCK-B", qty: "10", total_brl: "6050.00", unit_brl: "605.00" },
  ],
  components: [
    {
      id: 1,
      component_type: "MERCADORIA",
      source_kind: "INVOICE",
      amount_brl: "12000.0000",
      included: true,
      status: "OK",
      notes: null,
      allocation_method: "VALUE",
    },
    {
      id: 2,
      component_type: "II",
      source_kind: "TAX_LINE",
      amount_brl: "100.0000",
      included: true,
      status: "OK",
      notes: null,
      allocation_method: "VALUE",
    },
  ],
  expenses: [],
  lines: [],
  snapshot: {
    coverage: {
      coverage: "COMPLETE",
      reasons: [],
      invoice_count: 6,
      mentioned_count: 6,
      process_invoice_numbers: ["181", "202", "203", "244", "245", "246"],
      fob_amount: "288195.20",
      fob_currency: "EUR",
      merchandise_foreign: "288195.20",
      merchandise_currency: "EUR",
      freight_conflict: false,
      international_freight_count: 1,
      domestic_freight_count: 2,
      funding_included: true,
    },
    invoices: [{ invoice_number: "181", net_amount: "173217.30", fx: { initial_rate: "5.9205" } }],
    fx: { kind: "documental", documentary_rate: "5.9205", statuses: ["INITIAL"] },
  },
};

const caseRow = {
  id: 2,
  import_process_id: 2,
  process_code: "IMP-MOCK",
  process_reference: "MOCK-J6B",
  process_status: "DRAFT",
  freight_choice: null,
  title: "Custo",
  subtitle: "sub",
  versions: [
    {
      id: 2,
      kind: "REVISED",
      status: "PUBLISHED",
      version_number: 1,
      included_total_brl: "12100.0000",
      published_at: "2026-08-20T12:00:00Z",
    },
    {
      id: 3,
      kind: "REVISED",
      status: "DRAFT",
      version_number: 2,
      included_total_brl: "12100.0000",
      created_at: "2026-08-20T13:00:00Z",
    },
  ],
};

const mocks = vi.hoisted(() => ({
  addCostingExpense: vi.fn(async () => ({ id: 1, status: "ACTIVE", amount: "50.0000" })),
  uploadCostingDocument: vi.fn(async () => ({ id: 9, original_filename: "recibo-ensaio.pdf" })),
}));

vi.mock("./costingApi", () => ({
  getCostingCase: () => Promise.resolve(caseRow),
  getCostingVersion: () => Promise.resolve(version),
  publishCosting: vi.fn(),
  recalculateCosting: vi.fn(),
  reviseCosting: vi.fn(),
  setFreightChoice: vi.fn(),
  resolvePair: vi.fn(),
  addCostingExpense: mocks.addCostingExpense,
  uploadCostingDocument: mocks.uploadCostingDocument,
  compareCostingVersions: vi.fn(),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: [] as string[],
};

const reader = {
  id: 2,
  email: "reader@epic.com.br",
  name: "Reader",
  role: "aduana",
  permissions: ["costing:read"],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CostingWorkspacePage expenses", () => {
  it("mostra formulário, salva despesa e marca prévia desatualizada", async () => {
    render(
      <MemoryRouter initialEntries={["/costing/2"]}>
        <Routes>
          <Route path="/costing/:caseId" element={<CostingWorkspacePage user={admin} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("costing-workspace")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("costing-expense-add"));
    expect(screen.getByTestId("costing-expense-form")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("expense-description"), { target: { value: "ensaio MOCK" } });
    fireEvent.change(screen.getByTestId("expense-amount"), { target: { value: "50.00" } });
    fireEvent.click(screen.getByTestId("expense-save"));
    await waitFor(() => expect(mocks.addCostingExpense).toHaveBeenCalled());
    expect(await screen.findByTestId("costing-preview-stale")).toBeInTheDocument();
  });

  it("somente leitura não mostra adicionar despesa", async () => {
    render(
      <MemoryRouter initialEntries={["/costing/2"]}>
        <Routes>
          <Route path="/costing/:caseId" element={<CostingWorkspacePage user={reader} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("costing-expenses")).toBeInTheDocument();
    expect(screen.getByTestId("costing-components")).toHaveTextContent("12.000,00");
    expect(screen.getByTestId("costing-included-total")).toHaveTextContent("BRL 12.100,00");
    expect(screen.getByTestId("costing-products")).toHaveTextContent("6.050,00");
    expect(screen.queryByTestId("costing-expense-add")).not.toBeInTheDocument();
  });

  it("mostra cobertura 6/6, câmbio documental e copy de publicar revisado", async () => {
    render(
      <MemoryRouter initialEntries={["/costing/2"]}>
        <Routes>
          <Route path="/costing/:caseId" element={<CostingWorkspacePage user={admin} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("costing-coverage-invoices")).toHaveTextContent("6 de 6");
    expect(screen.getByTestId("costing-fx-story")).toHaveTextContent(/documental da importação/i);
    expect(screen.getByTestId("costing-fx-story")).toHaveTextContent("5,920500");
    expect(screen.getByTestId("costing-fx-story")).toHaveTextContent(/não é câmbio bancário realizado/i);
    expect(screen.getByTestId("costing-publish-copy")).toHaveTextContent(/não é custo final/i);
    expect(screen.getByTestId("costing-publish")).toHaveTextContent(/revisado/i);
    expect(screen.queryByTestId("costing-freight-VALUE_BASIS")).not.toBeInTheDocument();
    expect(screen.getByTestId("costing-tolerance-notice")).toHaveTextContent(/tolerância provisória/i);
    expect(screen.getByTestId("costing-pairs-empty")).toHaveTextContent(/Sem divergências/i);
  });
});
