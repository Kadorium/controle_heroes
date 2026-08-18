import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShipmentsListPage } from "./ShipmentsListPage";
import { ShipmentCreatePage } from "./ShipmentCreatePage";
import { ShipmentDetailPage } from "./ShipmentDetailPage";

vi.mock("./shipmentsApi", () => ({
  listShipments: vi.fn(),
  getShipment: vi.fn(),
  createShipment: vi.fn(),
  getDerivedTotals: vi.fn(),
  getDivergences: vi.fn(),
  listShipmentAudit: vi.fn(),
  listShipmentDocuments: vi.fn(),
  addPackage: vi.fn(),
  updatePackage: vi.fn(),
  addPackagesBatch: vi.fn(),
  updatePackagesBatch: vi.fn(),
  setPackageContents: vi.fn(),
  upsertDocumentSummary: vi.fn(),
  uploadShipmentDocument: vi.fn(),
  removePackage: vi.fn(),
}));

vi.mock("./providersApi", () => ({
  listLogisticsProviders: vi.fn(),
  createLogisticsProvider: vi.fn(),
}));

import * as shipmentsApi from "./shipmentsApi";
import * as providersApi from "./providersApi";

afterEach(() => {
  cleanup();
});

const writer = {
  id: 1,
  email: "a@b.c",
  name: "Admin",
  role: "admin",
  permissions: ["logistics:read", "logistics:write"],
};

const reader = {
  id: 2,
  email: "r@b.c",
  name: "Reader",
  role: "logistics",
  permissions: ["logistics:read"],
};

describe("ShipmentsListPage RTL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(providersApi.listLogisticsProviders).mockResolvedValue([]);
  });

  it("shows loading then empty state", async () => {
    vi.mocked(shipmentsApi.listShipments).mockResolvedValue([]);
    render(
      <MemoryRouter>
        <ShipmentsListPage user={writer} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/carregando embarques/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("empty-state")).toBeInTheDocument());
  });
});

describe("ShipmentCreatePage RTL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("blocks users without write permission", () => {
    render(
      <MemoryRouter>
        <ShipmentCreatePage user={reader} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/sem permissão/i)).toBeInTheDocument();
  });

  it("auto-selects single provider and shows microcopy", async () => {
    vi.mocked(providersApi.listLogisticsProviders).mockResolvedValue([
      {
        id: 9,
        legal_name: "Unica LTDA",
        trade_name: "Unica",
        provider_type: "TRANSPORTADOR",
        active: true,
        created_at: null,
        updated_at: null,
      },
    ]);
    render(
      <MemoryRouter>
        <ShipmentCreatePage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("shipment-create-page")).toBeInTheDocument());
    expect(
      screen.getByText(
        /Cadastre os dados básicos\. Itens, volumes e documentos serão adicionados após a criação\./i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("shipment-provider")).toHaveValue("9");
  });

  it("shows empty CTA when no providers", async () => {
    vi.mocked(providersApi.listLogisticsProviders).mockResolvedValue([]);
    render(
      <MemoryRouter>
        <ShipmentCreatePage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("shipment-create-providers-cta")).toBeInTheDocument(),
    );
  });

  it("leaves provider empty when multiple options", async () => {
    vi.mocked(providersApi.listLogisticsProviders).mockResolvedValue([
      {
        id: 1,
        legal_name: "A",
        trade_name: "A",
        provider_type: "TRANSPORTADOR",
        active: true,
        created_at: null,
        updated_at: null,
      },
      {
        id: 2,
        legal_name: "B",
        trade_name: "B",
        provider_type: "ARMADOR",
        active: true,
        created_at: null,
        updated_at: null,
      },
    ]);
    render(
      <MemoryRouter>
        <ShipmentCreatePage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("shipment-provider")).toHaveValue(""));
    expect(screen.getByTestId("shipment-modal")).toBeInTheDocument();
  });
});

describe("ShipmentDetailPage RTL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(providersApi.listLogisticsProviders).mockResolvedValue([
      {
        id: 3,
        legal_name: "MSC",
        trade_name: "MSC",
        provider_type: "ARMADOR",
        active: true,
        created_at: null,
        updated_at: null,
      },
    ]);
    vi.mocked(shipmentsApi.getDerivedTotals).mockResolvedValue({
      net_weight_kg: "0",
      gross_weight_kg: "0",
      volume_m3: "0",
      pallet_count: 0,
      carton_count: 0,
      box_count: 0,
      package_row_count: 0,
    });
    vi.mocked(shipmentsApi.getDivergences).mockResolvedValue([]);
    vi.mocked(shipmentsApi.listShipmentAudit).mockResolvedValue([]);
    vi.mocked(shipmentsApi.listShipmentDocuments).mockResolvedValue([]);
  });

  it("hides structure CTAs when BOOKED", async () => {
    vi.mocked(shipmentsApi.getShipment).mockResolvedValue({
      id: 7,
      code: "SHP-TEST",
      status: "BOOKED",
      version: 2,
      cancelled_at: null,
      modal: "SEA",
      origin: "IT",
      destination: "BR",
      logistics_provider_id: 3,
      carrier_name_snapshot: "MSC",
      logistics_provider: {
        id: 3,
        legal_name: "MSC",
        trade_name: "MSC",
        provider_type: "ARMADOR",
      },
      planned_departure: "2026-07-01",
      planned_arrival: "2026-08-01",
      actual_departure: null,
      actual_arrival: null,
      status_changed_at: "2026-07-01T12:00:00Z",
      notes: null,
      created_at: "2026-07-01T10:00:00Z",
      updated_at: "2026-07-01T12:00:00Z",
      items: [
        {
          id: 1,
          order_item_id: 10,
          quantity: "2",
          order_id: 5,
          order_code: "ORD-1",
          sku: "SKU-1",
          description: "Prod",
        },
      ],
      packages: [],
      references: [],
      document_summaries: [],
    });
    render(
      <MemoryRouter initialEntries={["/shipments/7"]}>
        <Routes>
          <Route path="/shipments/:shipmentId" element={<ShipmentDetailPage user={writer} />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("shipment-detail")).toBeInTheDocument());
    expect(screen.queryByTestId("shipment-add-item")).not.toBeInTheDocument();
  });

  it("shows package editor when PLANNED", async () => {
    vi.mocked(shipmentsApi.getShipment).mockResolvedValue({
      id: 8,
      code: "SHP-PLANNED",
      status: "PLANNED",
      version: 1,
      cancelled_at: null,
      modal: null,
      origin: null,
      destination: null,
      logistics_provider_id: null,
      carrier_name_snapshot: null,
      logistics_provider: null,
      planned_departure: null,
      planned_arrival: null,
      actual_departure: null,
      actual_arrival: null,
      status_changed_at: "2026-07-01T12:00:00Z",
      notes: null,
      created_at: "2026-07-01T10:00:00Z",
      updated_at: "2026-07-01T12:00:00Z",
      items: [],
      packages: [],
      references: [],
      document_summaries: [],
    });
    render(
      <MemoryRouter initialEntries={["/shipments/8"]}>
        <Routes>
          <Route path="/shipments/:shipmentId" element={<ShipmentDetailPage user={writer} />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("package-editor")).toBeInTheDocument());
    expect(screen.getByTestId("shipment-batch-range")).toBeInTheDocument();
    expect(screen.getByTestId("shipment-doc-upload")).toBeInTheDocument();
    expect(screen.getByTestId("document-summary-editor")).toBeInTheDocument();
  });

  it("explica palete declarado vs caixas CARTON sem tratar como erro de parse", async () => {
    vi.mocked(shipmentsApi.getShipment).mockResolvedValue({
      id: 8,
      code: "SHP-PLANNED",
      status: "PLANNED",
      version: 1,
      cancelled_at: null,
      modal: null,
      origin: null,
      destination: null,
      logistics_provider_id: null,
      carrier_name_snapshot: null,
      logistics_provider: null,
      planned_departure: null,
      planned_arrival: null,
      actual_departure: null,
      actual_arrival: null,
      status_changed_at: "2026-07-01T12:00:00Z",
      notes: null,
      created_at: "2026-07-01T10:00:00Z",
      updated_at: "2026-07-01T12:00:00Z",
      items: [],
      packages: [],
      references: [],
      document_summaries: [],
    });
    vi.mocked(shipmentsApi.getDerivedTotals).mockResolvedValue({
      net_weight_kg: "16",
      gross_weight_kg: "120",
      volume_m3: "0",
      pallet_count: 0,
      carton_count: 5,
      box_count: 0,
      package_row_count: 5,
    });
    vi.mocked(shipmentsApi.getDivergences).mockResolvedValue([
      {
        document_id: 3,
        summary_id: 1,
        is_significant: true,
        diffs: [
          {
            field: "pallet_count",
            declared: 1,
            derived: 0,
            is_significant: true,
          },
        ],
      },
    ]);
    render(
      <MemoryRouter initialEntries={["/shipments/8"]}>
        <Routes>
          <Route path="/shipments/:shipmentId" element={<ShipmentDetailPage user={writer} />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("divergence-pallet-notice")).toBeInTheDocument());
    expect(screen.getByTestId("divergence-pallet-notice")).toHaveTextContent(
      "O documento declara 1 palete",
    );
    expect(screen.getByTestId("divergence-pallet-notice")).toHaveTextContent("5 caixa");
    expect(screen.getByTestId("divergence-pallet-notice")).toHaveTextContent("nenhum volume do tipo PALLET");
    expect(screen.queryByTestId("divergence-notice")).not.toBeInTheDocument();
  });
});
