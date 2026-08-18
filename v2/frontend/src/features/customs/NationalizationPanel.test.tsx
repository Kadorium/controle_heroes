import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { NationalizationPanel } from "./NationalizationPanel";
import * as api from "../inventory/inventoryApi";

vi.mock("../inventory/inventoryApi", async () => {
  const actual = await vi.importActual<typeof import("../inventory/inventoryApi")>(
    "../inventory/inventoryApi",
  );
  return {
    ...actual,
    listNationalizations: vi.fn(),
    listClearanceResiduals: vi.fn(),
    createNationalization: vi.fn(),
    addNationalizationItems: vi.fn(),
    confirmNationalization: vi.fn(),
    listReceiptResiduals: vi.fn(),
    reverseNationalization: vi.fn(),
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
  permissions: ["customs:write", "customs:clear", "customs:read"],
};

describe("NationalizationPanel E7-4", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mostra produto derivado e residual, sem campo de ID cru", async () => {
    vi.mocked(api.listNationalizations).mockResolvedValue([]);
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([]);
    vi.mocked(api.listClearanceResiduals).mockResolvedValue([
      {
        source_kind: "shipment_item",
        shipment_item_id: 4,
        invoice_item_id: null,
        allocated_qty: "50",
        nationalized_qty: "10",
        residual_qty: "40",
        product_id: 3,
        product_sku: "8057628953593",
        product_name: "RACCHETTA BT 2026 STARLIGHT",
        shipped_qty: "50",
      },
      {
        source_kind: "shipment_item",
        shipment_item_id: 5,
        invoice_item_id: null,
        allocated_qty: "10",
        nationalized_qty: "10",
        residual_qty: "0",
        product_id: 9,
        product_sku: "DONE-SKU",
        product_name: "Já nacionalizado",
        shipped_qty: "10",
      },
    ]);

    render(<NationalizationPanel user={admin} processId={1} />);

    await waitFor(() =>
      expect(screen.getByTestId("nationalization-residual-table")).toBeInTheDocument(),
    );
    expect(screen.getByText("RACCHETTA BT 2026 STARLIGHT")).toBeInTheDocument();
    expect(screen.getByText("8057628953593")).toBeInTheDocument();
    expect(screen.queryByText("Já nacionalizado")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/productId/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/shipmentItemId/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("nationalization-create")).toBeInTheDocument();
  });

  it("oculta Reverter quando já há estoque recebido da mesma liberação", async () => {
    vi.mocked(api.listClearanceResiduals).mockResolvedValue([]);
    vi.mocked(api.listNationalizations).mockResolvedValue([
      {
        id: 9,
        process_id: 1,
        reference: null,
        status: "CONFIRMED",
        version: 2,
        notes: null,
        confirmed_at: null,
        reversed_at: null,
        created_at: null,
        items: [
          {
            id: 3,
            doganale_line_id: null,
            invoice_item_id: null,
            shipment_item_id: 4,
            product_id: 3,
            quantity: "50",
            notes: null,
          },
        ],
      },
    ]);
    vi.mocked(api.listReceiptResiduals).mockResolvedValue([
      {
        nationalization_id: 9,
        nationalization_item_id: 3,
        product_id: 3,
        product_sku: "8057628953814",
        product_name: "WASH BAG STARLIGHT - RED",
        nationalized_qty: "50",
        received_qty: "20",
        residual_qty: "30",
      },
    ]);

    render(<NationalizationPanel user={admin} processId={1} />);

    await waitFor(() =>
      expect(screen.getByTestId("nationalization-reverse-hidden-9")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("nationalization-reverse-9")).not.toBeInTheDocument();
  });
});
