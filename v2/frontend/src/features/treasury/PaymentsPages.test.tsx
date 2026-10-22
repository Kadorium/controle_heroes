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
        supplier_name: "Heroes Metalúrgica LTDA",
        payee_display_name: "Heroes Metalúrgica LTDA",
        amount: "1000.00",
        currency: "EUR",
        payment_date: "2026-07-22",
        external_reference: null,
        status: "REGISTERED",
        version: 1,
        amount_allocated: "0.00",
        amount_unallocated: "1000.00",
        allocations: [],
        documents: [],
      },
      {
        id: 8,
        supplier_id: null,
        supplier_name: null,
        payee_display_name: "Bechtrans",
        amount: "100.00",
        currency: "BRL",
        payment_date: "2026-08-20",
        external_reference: null,
        status: "REGISTERED",
        version: 1,
        amount_allocated: "0.00",
        amount_unallocated: "100.00",
        allocations: [],
        documents: [],
      },
    ]),
  };
});

describe("PaymentsListPage", () => {
  it("apresenta primitives V0 (data, money, status, fornecedor)", async () => {
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
    expect(screen.getByText("22/07/2026")).toBeInTheDocument();
    expect(screen.getByText("Heroes Metalúrgica LTDA")).toBeInTheDocument();
    expect(screen.getByText("Bechtrans")).toBeInTheDocument();
    expect(screen.queryByText("null")).toBeNull();
    expect(screen.getAllByText("Registrado").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("REGISTERED")).toBeNull();
    expect(screen.getAllByText("EUR 1.000,00").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/#1/)).toBeNull();
    const openLinks = screen.getAllByRole("link", { name: /abrir/i });
    expect(openLinks[0]).toHaveAttribute("href", "/payments/7");
    expect(openLinks[1]).toHaveAttribute("href", "/payments/8");
    expect(screen.queryByRole("link", { name: /^—$/ })).toBeNull();
    expect(screen.getByRole("link", { name: /novo pagamento/i })).toBeInTheDocument();
  });
});
