import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OrderInvoicesPanel } from "./InvoiceDetailPage";

vi.mock("./billingApi", () => ({
  listOrderInvoices: vi.fn(),
  invoicedQuantities: vi.fn(),
  createInvoice: vi.fn(),
}));

import * as billingApi from "./billingApi";

const writer = {
  id: 1,
  email: "a@b.c",
  name: "Admin",
  role: "admin",
  permissions: ["billing:write"],
};

afterEach(() => {
  cleanup();
});

describe("OrderInvoicesPanel RUX-3F I1", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(billingApi.listOrderInvoices).mockResolvedValue([]);
  });

  it("commitment-only CONFIRMED: Notice + no create + Disponível —", async () => {
    vi.mocked(billingApi.invoicedQuantities).mockResolvedValue([
      {
        order_item_id: 42,
        ordered_qty: "14600.0000",
        issued_qty: "0.0000",
        available_qty: "0",
        line_kind: "COMMITMENT",
        description: "racchette 2027 GRAFICATE",
        billable: false,
      },
      {
        order_item_id: 43,
        ordered_qty: "2000.0000",
        issued_qty: "0.0000",
        available_qty: "0",
        line_kind: "COMMITMENT",
        description: "racchette 2027 NON GRAFICATE",
        billable: false,
      },
    ]);

    render(
      <MemoryRouter>
        <OrderInvoicesPanel user={writer} orderId={31} orderStatus="CONFIRMED" />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("order-invoices-commitment-notice")).toHaveTextContent(
      /só tem linhas de compromisso/i,
    );
    expect(screen.getByTestId("order-invoices-commitment-notice")).toHaveTextContent(
      /importação da Fattura/i,
    );
    expect(screen.queryByText(/fantasma|inválido/i)).not.toBeInTheDocument();
    expect(screen.getByText(/racchette 2027 GRAFICATE/i)).toBeInTheDocument();
    expect(screen.getAllByText(/· compromisso/i).length).toBe(2);
    expect(screen.getByTestId("qty-available-42")).toHaveTextContent("—");
    expect(screen.getByTestId("qty-available-43")).toHaveTextContent("—");
    expect(screen.queryByTestId("create-invoice")).not.toBeInTheDocument();
    expect(screen.queryByTestId("new-invoice-number")).not.toBeInTheDocument();
  });

  it("mixed PRODUCT+COMMITMENT: create only when billable exists; commitment shows —", async () => {
    vi.mocked(billingApi.invoicedQuantities).mockResolvedValue([
      {
        order_item_id: 10,
        ordered_qty: "5.0000",
        issued_qty: "0.0000",
        available_qty: "5.0000",
        line_kind: "PRODUCT",
        description: "SKU final",
        billable: true,
      },
      {
        order_item_id: 11,
        ordered_qty: "50.0000",
        issued_qty: "0.0000",
        available_qty: "0",
        line_kind: "COMMITMENT",
        description: "só compromisso",
        billable: false,
      },
    ]);

    render(
      <MemoryRouter>
        <OrderInvoicesPanel user={writer} orderId={99} orderStatus="CONFIRMED" />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("create-invoice")).toBeInTheDocument());
    expect(screen.queryByTestId("order-invoices-commitment-notice")).not.toBeInTheDocument();
    expect(screen.getByTestId("qty-available-10")).not.toHaveTextContent("—");
    expect(screen.getByTestId("qty-available-11")).toHaveTextContent("—");
    expect(screen.getByText(/só compromisso/i)).toBeInTheDocument();
  });

  it("CONFIRMED but empty qtys: no create form", async () => {
    vi.mocked(billingApi.invoicedQuantities).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <OrderInvoicesPanel user={writer} orderId={1} orderStatus="CONFIRMED" />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("order-invoices")).toBeInTheDocument());
    expect(screen.queryByTestId("create-invoice")).not.toBeInTheDocument();
    expect(screen.queryByTestId("order-invoices-commitment-notice")).not.toBeInTheDocument();
  });
});
