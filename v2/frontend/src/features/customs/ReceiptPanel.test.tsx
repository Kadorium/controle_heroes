import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { ReceiptPanel } from "./ReceiptPanel";
import * as api from "../inventory/inventoryApi";
import type { GoodsReceipt, ReceiptResidual, StockLocation } from "../inventory/inventoryApi";

vi.mock("../inventory/inventoryApi", async () => {
  const actual = await vi.importActual<typeof import("../inventory/inventoryApi")>(
    "../inventory/inventoryApi",
  );
  return {
    ...actual,
    listReceipts: vi.fn(),
    listLocations: vi.fn(),
    listReceiptResiduals: vi.fn(),
    createReceipt: vi.fn(),
    addReceiptLines: vi.fn(),
    confirmReceipt: vi.fn(),
    reverseReceipt: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
});

const admin: User = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: ["inventory:read", "inventory:write"],
};

const domesticMain: StockLocation = {
  id: 2,
  code: "DOMESTIC-MAIN",
  name: "Doméstico principal",
  location_type: "DOMESTIC",
  active: true,
};

function residual(over: Partial<ReceiptResidual> = {}): ReceiptResidual {
  return {
    nationalization_id: 9,
    nationalization_item_id: 3,
    product_id: 4,
    product_sku: "8057628953814",
    product_name: "WASH BAG STARLIGHT - RED",
    nationalized_qty: "50",
    received_qty: "0",
    residual_qty: "50",
    ...over,
  };
}

function draftReceipt(over: Partial<GoodsReceipt> = {}): GoodsReceipt {
  return {
    id: 11,
    location_id: 2,
    location_code: "DOMESTIC-MAIN",
    location_type: "DOMESTIC",
    process_id: 1,
    nationalization_id: 9,
    receipt_type: "DOMESTIC_IN",
    status: "DRAFT",
    version: 1,
    notes: null,
    received_at: null,
    created_at: null,
    lines: [],
    ...over,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ReceiptPanel user={admin} processId={1} />
    </MemoryRouter>,
  );
}

describe("ReceiptPanel E8-2", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listReceipts).mockResolvedValue([]);
    vi.mocked(api.listLocations).mockResolvedValue([domesticMain]);
  });

  it("estado 0: sem residual nacionalizado", async () => {
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([]);
    renderPanel();
    await waitFor(() =>
      expect(screen.getByText("Sem quantidade nacionalizada")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("receipt-residual-table")).not.toBeInTheDocument();
  });

  it("estado 1: uma linha sem IDs crus e tipo só DOMESTIC_IN", async () => {
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([residual()]);
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("receipt-residual-table")).toBeInTheDocument(),
    );
    expect(screen.getByText("WASH BAG STARLIGHT - RED")).toBeInTheDocument();
    expect(screen.getByText("8057628953814")).toBeInTheDocument();
    expect(screen.queryByLabelText(/ID do produto/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("receipt-product-id")).not.toBeInTheDocument();
    expect(screen.queryByTestId("receipt-nat-id")).not.toBeInTheDocument();
    expect(screen.getByTestId("receipt-type")).toHaveValue("DOMESTIC_IN");
    expect(screen.getByTestId("receipt-type")).toBeDisabled();
    expect(screen.queryByRole("option", { name: /entreposto/i })).not.toBeInTheDocument();
  });

  it("estado N: só residual > 0 aparece", async () => {
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([
      residual(),
      residual({
        nationalization_item_id: 8,
        product_id: 5,
        product_sku: "8057628953593",
        product_name: "RACCHETTA BT 2026 STARLIGHT",
        residual_qty: "0",
        received_qty: "10",
        nationalized_qty: "10",
      }),
    ]);
    renderPanel();
    await waitFor(() =>
      expect(screen.getByText("WASH BAG STARLIGHT - RED")).toBeInTheDocument(),
    );
    expect(screen.queryByText("RACCHETTA BT 2026 STARLIGHT")).not.toBeInTheDocument();
  });

  it("avisa over-receipt e não inventa product_id", async () => {
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([residual()]);
    const created = draftReceipt();
    vi.mocked(api.createReceipt).mockResolvedValue(created);
    vi.mocked(api.addReceiptLines).mockResolvedValue({ ...created, version: 2, lines: [] });
    vi.mocked(api.confirmReceipt).mockResolvedValue({
      ...created,
      status: "CONFIRMED",
      version: 3,
    });
    renderPanel();
    const input = await screen.findByTestId("receipt-proposed-3");
    fireEvent.change(input, { target: { value: "80" } });
    expect(screen.getByTestId("receipt-over-3")).toHaveTextContent(/Acima do residual/i);

    fireEvent.click(screen.getByTestId("receipt-receive"));
    await waitFor(() =>
      expect(screen.getByTestId("receipt-error")).toHaveTextContent(/residual nacionalizado/i),
    );
    expect(api.createReceipt).not.toHaveBeenCalled();
  });

  it("double-click não cria dois rascunhos", async () => {
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([residual()]);
    let resolveCreate!: (value: GoodsReceipt) => void;
    const pending = new Promise<GoodsReceipt>((resolve) => {
      resolveCreate = resolve;
    });
    vi.mocked(api.createReceipt).mockReturnValue(pending);
    vi.mocked(api.addReceiptLines).mockResolvedValue(draftReceipt({ version: 2 }));
    vi.mocked(api.confirmReceipt).mockResolvedValue(
      draftReceipt({ status: "CONFIRMED", version: 3 }),
    );
    renderPanel();
    const btn = await screen.findByTestId("receipt-receive");
    fireEvent.click(btn);
    fireEvent.click(btn);
    expect(api.createReceipt).toHaveBeenCalledTimes(1);
    resolveCreate(draftReceipt());
    await waitFor(() => expect(api.confirmReceipt).toHaveBeenCalledTimes(1));
  });
});
