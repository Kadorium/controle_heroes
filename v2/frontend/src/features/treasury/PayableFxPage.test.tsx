import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PayableFxPage } from "./PayableFxPage";

const getPayable = vi.fn();
const getPayableFxView = vi.fn();
const listOrderAdvances = vi.fn();
const allocatePayment = vi.fn();

vi.mock("../../navigation/returnState", () => ({
  buildReturnTo: () => "/payables",
}));

vi.mock("../billing/billingApi", () => ({
  getPayable: (...args: unknown[]) => getPayable(...args),
}));

vi.mock("./advanceApi", () => ({
  listOrderAdvances: (...args: unknown[]) => listOrderAdvances(...args),
}));

vi.mock("./treasuryApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./treasuryApi")>();
  return {
    ...actual,
    allocatePayment: (...args: unknown[]) => allocatePayment(...args),
    canAllocateTreasury: () => true,
  };
});

vi.mock("./fxApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./fxApi")>();
  return {
    ...actual,
    getPayableFxView: (...args: unknown[]) => getPayableFxView(...args),
    canReadFx: () => true,
    canWriteFx: () => false,
    canRefreshFxQuote: () => false,
  };
});

const payable = {
  id: 22,
  sequence: 1,
  due_date: "2026-03-20",
  currency: "EUR",
  balance: "36000.00",
  amount: "36000.00",
  status: "OPEN",
  destination_bank: null,
  destination_iban: null,
  order_id: 34,
  version: 1,
  supplier_id: 27,
};

function fxView(costBrl: string) {
  return {
    payable_id: 22,
    currency: "EUR",
    open_foreign: "36000.00",
    initial_planned_rate: null,
    current_forecast_rate: null,
    market: { rate: null, status: "missing", stale: false, source: null },
    projected_open_brl: null,
    market_open_brl: null,
    online_result_vs_current: null,
    online_result_vs_initial: null,
    settled_foreign: "0.00",
    cost_brl: costBrl,
    realized_brl: null,
    realized_result_vs_reference: null,
    realized_result_vs_initial: null,
    total_vs_current: null,
    total_vs_initial: null,
    benchmarks: {},
    plan_history: [],
  };
}

describe("PayableFxPage", () => {
  beforeEach(() => {
    getPayable.mockReset();
    getPayableFxView.mockReset();
    listOrderAdvances.mockReset();
    allocatePayment.mockReset();
    getPayable.mockResolvedValue(payable);
    listOrderAdvances.mockResolvedValue({
      order_id: 34,
      order_code: "TESTE-CICLO-001",
      currency: "EUR",
      advances: [
        {
          payment_id: 25,
          amount: "120000.00",
          currency: "EUR",
          payment_date: "2026-01-15",
          external_reference: null,
          status: "REGISTERED",
          version: 1,
          fx_execution_id: 1,
          foreign_amount: "120000.00",
          brl_amount: "696000.00",
          rate: "5.800000",
          execution_date: "2026-01-14",
          amount_unallocated: "36000.00",
          fx_documents: [],
        },
      ],
      settlements: [],
      consolidated: {
        total_eur: "120000.00",
        total_brl: "696000.00",
        weighted_avg_rate: "5.800000",
        count: 1,
      },
    });
    allocatePayment.mockResolvedValue({ id: 25, version: 2 });
    getPayableFxView
      .mockResolvedValueOnce(fxView("0.00"))
      .mockResolvedValueOnce(fxView("208800.00"));
  });

  it("atualiza Custo BRL após aplicar crédito, sem recarregar a página", async () => {
    render(
      <MemoryRouter initialEntries={["/payables/22/fx"]}>
        <Routes>
          <Route
            path="/payables/:payableId/fx"
            element={
              <PayableFxPage
                user={{
                  id: 1,
                  email: "a@b.c",
                  name: "A",
                  role: "admin",
                  permissions: ["treasury:allocate", "treasury:fx_read"],
                }}
              />
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("payable-fx-page")).toBeInTheDocument();
    expect(await screen.findByText("BRL 0,00")).toBeInTheDocument();

    fireEvent.click(await screen.findByTestId("apply-advance-25"));

    await waitFor(() => {
      expect(allocatePayment).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText("BRL 208.800,00")).toBeInTheDocument();
    });
    expect(getPayableFxView).toHaveBeenCalledTimes(2);
  });
});
