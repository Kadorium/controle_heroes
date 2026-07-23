import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { PaymentsListPage } from "./PaymentsPages";

vi.mock("./treasuryApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./treasuryApi")>();
  return {
    ...actual,
    listPayments: vi.fn(async () => [
      {
        id: 7,
        supplier_id: 1,
        amount: "1000.00",
        currency: "EUR",
        payment_date: "2026-07-22",
        external_reference: null,
        status: "REGISTERED",
        version: 1,
        amount_allocated: "0.00",
        amount_unallocated: "1000.00",
        allocations: [],
      },
    ]),
  };
});

describe("PaymentsListPage", () => {
  it("lists residual and link to allocate", async () => {
    render(
      <MemoryRouter>
        <PaymentsListPage
          user={{
            id: 1,
            email: "a@b.c",
            name: "A",
            role: "admin",
            permissions: ["treasury:write", "treasury:allocate"],
          }}
        />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("payments-list")).toBeInTheDocument();
    expect(screen.getAllByText("1000.00").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /abrir/i })).toHaveAttribute("href", "/payments/7");
    expect(screen.getByRole("link", { name: /novo pagamento/i })).toBeInTheDocument();
  });
});
