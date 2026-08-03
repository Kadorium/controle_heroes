import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OrdersListPage } from "./OrdersListPage";
import { OrderCreatePage } from "./OrderCreatePage";
import { OrderDetailPage } from "./OrderDetailPage";

vi.mock("../reporting/reportingApi", () => ({
  fetchOrdersList: vi.fn(),
}));

vi.mock("./ordersApi", () => ({
  listOrders: vi.fn(),
  getOrder: vi.fn(),
  createOrder: vi.fn(),
  updateOrder: vi.fn(),
  updateOrderItem: vi.fn(),
  uploadOrderDocument: vi.fn(),
  addOrderItem: vi.fn(),
  confirmOrder: vi.fn(),
  cancelOrder: vi.fn(),
}));

vi.mock("../billing/InvoiceDetailPage", () => ({
  OrderInvoicesPanel: () => null,
}));

vi.mock("../catalog/catalogApi", () => ({
  listSuppliers: vi.fn(async () => []),
  listProducts: vi.fn(async () => [{ id: 1, sku: "SKU-1", description: "Prod", is_active: true }]),
  createSupplier: vi.fn(),
  createProduct: vi.fn(),
}));

import * as reportingApi from "../reporting/reportingApi";
import * as ordersApi from "./ordersApi";
import * as catalogApi from "../catalog/catalogApi";

const writer = {
  id: 1,
  email: "a@b.c",
  name: "Admin",
  role: "admin",
  permissions: ["orders:read", "orders:write", "orders:cancel", "catalog:write"],
};

const reader = {
  id: 2,
  email: "r@b.c",
  name: "Reader",
  role: "comprador",
  permissions: ["orders:read"],
};

describe("OrdersListPage RTL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading then empty state", async () => {
    vi.mocked(reportingApi.fetchOrdersList).mockResolvedValue([]);
    render(
      <MemoryRouter>
        <OrdersListPage user={writer} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/carregando pedidos/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("empty-state")).toBeInTheDocument());
  });

  it("shows error state", async () => {
    vi.mocked(reportingApi.fetchOrdersList).mockRejectedValue(new Error("falha lista"));
    render(
      <MemoryRouter>
        <OrdersListPage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("falha lista"));
  });
});

describe("OrderCreatePage RTL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(catalogApi.listSuppliers).mockResolvedValue([]);
    vi.mocked(catalogApi.listProducts).mockResolvedValue([
      { id: 1, sku: "SKU-1", description: "Prod", is_active: true, created_at: null },
    ]);
  });

  it("blocks users without write permission", () => {
    render(
      <MemoryRouter>
        <OrderCreatePage user={reader} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/sem permissão/i)).toBeInTheDocument();
  });

  it("shows form and commercial_total null when line has no price", async () => {
    render(
      <MemoryRouter>
        <OrderCreatePage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("order-code")).toBeInTheDocument());
    expect(screen.getByTestId("order-date")).toBeInTheDocument();
    expect(screen.getByTestId("order-notes")).toBeInTheDocument();
    expect(screen.getByTestId("line-unit")).toBeInTheDocument();
    const sku = screen.getByTestId("line-sku");
    const qty = screen.getByTestId("line-qty");
    const price = screen.getByTestId("line-price");
    const unit = screen.getByTestId("line-unit");
    // fireEvent via user-like change
    const { fireEvent } = await import("@testing-library/react");
    fireEvent.change(sku, { target: { value: "SKU-1" } });
    fireEvent.change(qty, { target: { value: "2" } });
    fireEvent.change(unit, { target: { value: "CTNS" } });
    fireEvent.change(price, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /adicionar linha/i }));
    expect(screen.getByTestId("commercial-total")).toHaveTextContent(/—/);
    expect(screen.getByTestId("commercial-total").textContent).toMatch(/incompleto|sem preço/i);
    expect(screen.getByText("CTNS")).toBeInTheDocument();
  });
});

describe("OrderDetailPage RTL", () => {
  it("shows readonly banner after confirmation", async () => {
    vi.mocked(ordersApi.getOrder).mockResolvedValue({
      id: 9,
      code: "X",
      external_ref: null,
      source_system: "MANUAL",
      supplier_id: 1,
      status: "CONFIRMED",
      currency: "EUR",
      order_date: "2026-07-22",
      created_by_actor_id: "1",
      notes: null,
      version: 2,
      items: [
        {
          id: 1,
          product_id: 1,
          sku_snapshot: "S",
          description_snapshot: "d",
          quantity: "1",
          unit: "PZ",
          unit_price: "10",
          line_total: "10.0000",
          position: 1,
        },
      ],
      commercial_total: "10.0000",
      priced_subtotal: "10.0000",
      unpriced_item_count: 0,
      documents: [],
    });
    render(
      <MemoryRouter initialEntries={["/orders/9"]}>
        <OrderDetailPage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("readonly-banner")).toBeInTheDocument());
    expect(screen.queryByTestId("confirm-order")).not.toBeInTheDocument();
    expect(screen.getByTestId("order-item-unit-1")).toHaveTextContent("PZ");
    expect(screen.getAllByText(/22\/07\/2026/).length).toBeGreaterThan(0);
  });
});
