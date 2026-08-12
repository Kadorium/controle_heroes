import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { InvoiceDetailPage } from "./InvoiceDetailPage";

vi.mock("./billingApi", () => ({
  getInvoice: vi.fn(async () => ({
    id: 1,
    order_id: 9,
    supplier_id: 1,
    invoice_number: "F-TEST",
    invoice_type: "FINAL",
    status: "DRAFT",
    invoice_date: "2026-07-22",
    currency: "EUR",
    terms_mode: null,
    created_by_actor_id: "1",
    notes: "Divergência de preço (Fattura ≠ pedido; a fatura segue o documento):\nSKU X pedido 50.00 · Fattura 55.00",
    version: 1,
    incomplete_line_count: 1,
    blockers: ["Há linhas com preço ou desconto incompletos", "Defina scadenze (PERCENT ou AMOUNT)"],
    items: [
      {
        id: 1,
        order_item_id: 1,
        product_id: 1,
        sku_snapshot: "SKU",
        description_snapshot: "Item",
        quantity: "10.0000",
        unit_price_gross: "100.0000",
        discount_type: null,
        discount_unit_amount: null,
        discount_percent: null,
        line_gross_amount: "1000.00",
        line_discount_amount: null,
        line_net_amount: null,
        position: 1,
      },
    ],
    terms: [],
    payables: [],
    payables_preview: [],
    documents: [],
  })),
  replaceItems: vi.fn(),
  setTerms: vi.fn(),
  issueInvoice: vi.fn(),
  uploadInvoiceDocument: vi.fn(),
}));

describe("InvoiceDetailPage", () => {
  it("blocks issue while incomplete and shows blockers", async () => {
    render(
      <MemoryRouter initialEntries={["/invoices/1"]}>
        <Routes>
          <Route
            path="/invoices/:invoiceId"
            element={
              <InvoiceDetailPage
                user={{
                  id: 1,
                  email: "a@b.c",
                  name: "A",
                  role: "admin",
                  permissions: ["billing:issue", "billing:write"],
                }}
              />
            }
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("invoice-detail")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-blockers")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-price-divergence")).toBeInTheDocument();
    expect(screen.getByTestId("issue-invoice")).toBeDisabled();
    expect(screen.getByTestId("issue-blocked-reason")).toHaveTextContent(/bloqueado/i);
  });
});
