import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  bindCommitmentProduct: vi.fn(),
  getPaymentSchedule: vi.fn(),
  setPaymentSchedule: vi.fn(),
}));

vi.mock("../billing/InvoiceDetailPage", () => ({
  OrderInvoicesPanel: ({ orderId }: { orderId: number }) => (
    <div data-testid="order-invoices-stub">invoices-{orderId}</div>
  ),
}));

vi.mock("../billing/billingApi", () => ({
  invoicedQuantities: vi.fn(async () => []),
}));

vi.mock("../catalog/catalogApi", () => ({
  listSuppliers: vi.fn(async () => []),
  listProducts: vi.fn(async () => [{ id: 1, sku: "SKU-1", description: "Prod", is_active: true }]),
  createSupplier: vi.fn(),
  createProduct: vi.fn(),
}));

vi.mock("../treasury/OrderAdvancesPanel", () => ({
  OrderAdvancesPanel: () => null,
}));

import * as reportingApi from "../reporting/reportingApi";
import * as ordersApi from "./ordersApi";
import * as catalogApi from "../catalog/catalogApi";
import * as billingApi from "../billing/billingApi";
import { fireEvent } from "@testing-library/react";
import { BindProductModal, bindProductErrorMessage } from "./BindProductModal";

afterEach(() => {
  cleanup();
});

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
    await waitFor(() => expect(screen.getByTestId("commercial-total")).toHaveTextContent(/—/));
    expect(screen.getByTestId("commercial-total").textContent).toMatch(/incompleto|sem preço/i);
    expect(screen.getByText("CTNS")).toBeInTheDocument();
  });
});

describe("OrderDetailPage RTL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(billingApi.invoicedQuantities).mockResolvedValue([]);
    vi.mocked(ordersApi.getPaymentSchedule).mockResolvedValue({
      order_id: 9,
      order_version: 2,
      order_status: "CONFIRMED",
      currency: "EUR",
      mode: null,
      commercial_total: "10.0000",
      amount_sum: null,
      delta: null,
      coherence: null,
      lines: [],
    });
  });

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
          line_kind: "PRODUCT",
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
    expect(screen.queryByTestId("bind-product-1")).not.toBeInTheDocument();
  });

  it("mixed PRODUCT+COMMITMENT: bind só no compromisso; Disponível numérico vs —", async () => {
    vi.mocked(ordersApi.getOrder).mockResolvedValue({
      id: 31,
      code: "589",
      external_ref: null,
      source_system: "MANUAL",
      supplier_id: 1,
      status: "CONFIRMED",
      currency: "EUR",
      order_date: "2026-07-22",
      created_by_actor_id: "1",
      notes: null,
      version: 3,
      items: [
        {
          id: 10,
          product_id: 7,
          line_kind: "PRODUCT",
          external_code: "I.V. 2",
          sku_snapshot: "CAT-GRAF",
          description_snapshot: "categoria GRAFICATE",
          quantity: "14600",
          unit: "PZ",
          unit_price: "50",
          line_total: "730000.0000",
          position: 1,
        },
        {
          id: 11,
          product_id: null,
          line_kind: "COMMITMENT",
          external_code: "I.V. 1",
          sku_snapshot: "I.V. 1",
          description_snapshot: "racchette NON GRAFICATE",
          quantity: "2000",
          unit: "PZ",
          unit_price: "50",
          line_total: "100000.0000",
          position: 2,
        },
      ],
      commercial_total: "830000.0000",
      priced_subtotal: "830000.0000",
      unpriced_item_count: 0,
      documents: [],
    });
    vi.mocked(billingApi.invoicedQuantities).mockResolvedValue([
      {
        order_item_id: 10,
        ordered_qty: "14600.0000",
        issued_qty: "0.0000",
        available_qty: "14600.0000",
        line_kind: "PRODUCT",
        description: "categoria GRAFICATE",
        billable: true,
      },
      {
        order_item_id: 11,
        ordered_qty: "2000.0000",
        issued_qty: "0.0000",
        available_qty: "0",
        line_kind: "COMMITMENT",
        description: "racchette NON GRAFICATE",
        billable: false,
      },
    ]);

    render(
      <MemoryRouter initialEntries={["/orders/31/commercial"]}>
        <OrderDetailPage user={writer} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("order-item-kind-10")).toBeInTheDocument());
    expect(screen.getByTestId("order-item-kind-10")).toHaveTextContent("Produto");
    expect(screen.getByTestId("order-item-kind-11")).toHaveTextContent("Compromisso");
    expect(screen.getByTestId("order-item-sku-10")).toHaveTextContent("CAT-GRAF");
    expect(screen.getByTestId("order-item-sku-11")).toHaveTextContent("I.V. 1");
    expect(screen.queryByTestId("bind-product-10")).not.toBeInTheDocument();
    expect(screen.getByTestId("bind-product-11")).toBeInTheDocument();
    expect(screen.getByTestId("order-item-available-10")).not.toHaveTextContent("—");
    expect(screen.getByTestId("order-item-available-11")).toHaveTextContent("—");
    expect(screen.getByText(/invoices-31/)).toBeInTheDocument();
  });

  it("shows empty payment schedule on commercial detail", async () => {
    vi.mocked(ordersApi.getOrder).mockResolvedValue({
      id: 9,
      code: "X",
      external_ref: null,
      source_system: "MANUAL",
      supplier_id: 1,
      status: "DRAFT",
      currency: "EUR",
      order_date: "2026-07-22",
      created_by_actor_id: "1",
      notes: null,
      version: 1,
      items: [
        {
          id: 1,
          product_id: 1,
          line_kind: "PRODUCT",
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
      <MemoryRouter initialEntries={["/orders/9/commercial"]}>
        <OrderDetailPage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("order-schedule-empty")).toBeInTheDocument());
    expect(screen.getByTestId("order-schedule-start")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("order-schedule-start"));
    expect(screen.getByTestId("order-schedule-mode")).toBeInTheDocument();
    expect(screen.getByTestId("order-schedule-save")).toBeInTheDocument();
  });
});

describe("BindProductModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(catalogApi.listProducts).mockResolvedValue([
      { id: 5, sku: "CAT-G5-TEST", description: "cat teste", is_active: true, created_at: null },
    ]);
  });

  it("rejects I.V.* SKU before calling onConfirm", async () => {
    const onConfirm = vi.fn();
    render(
      <BindProductModal
        open
        orderId={31}
        expectedVersion={2}
        line={{
          id: 42,
          external_code: "I.V. 2",
          description_snapshot: "GRAFICATE",
          quantity: "14600",
        }}
        onCancel={() => undefined}
        onConfirm={onConfirm}
      />,
    );
    await waitFor(() => expect(screen.getByTestId("bind-product-sku")).toBeInTheDocument());
    fireEvent.change(screen.getByTestId("bind-product-sku"), { target: { value: "I.V. 99" } });
    fireEvent.click(screen.getByTestId("confirm-modal-ok"));
    expect(await screen.findByTestId("bind-product-error")).toHaveTextContent(/I\.V\./i);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("maps G2 error codes to operator messages", () => {
    expect(
      bindProductErrorMessage(Object.assign(new Error("x"), { code: "line_already_invoiced", status: 422 })),
    ).toMatch(/fatura emitida/i);
    expect(
      bindProductErrorMessage(Object.assign(new Error("x"), { code: "invalid_product", status: 422 })),
    ).toMatch(/não encontrado ou inativo/i);
    expect(
      bindProductErrorMessage(Object.assign(new Error("x"), { code: "invalid_transition", status: 409 })),
    ).toMatch(/pedido confirmado/i);
    expect(bindProductErrorMessage(Object.assign(new Error("boom"), { status: 500 }))).toMatch(
      /Não foi possível vincular/i,
    );
  });
});
