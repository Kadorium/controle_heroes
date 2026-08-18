import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { PackingCommitPanel } from "./PackingCommitPanel";
import * as api from "./ingestionApi";

vi.mock("./ingestionApi", async () => {
  const actual = await vi.importActual<typeof import("./ingestionApi")>("./ingestionApi");
  return {
    ...actual,
    fetchPackingPreview: vi.fn(),
    commitPlDetail: vi.fn(),
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
  permissions: ["ingestion:commit", "logistics:write", "ingestion:read"],
};

const basePreview = {
  document_id: 9,
  fingerprint: "abc",
  operations: [],
  open_error_count: 0,
  can_commit: false,
  order_candidates: [] as api.PackingOrderCandidateOut[],
  order_candidates_reason: null as string | null,
  shipment_targets: [] as api.PackingShipmentTargetOut[],
  shipment_targets_reason: null as string | null,
  line_matches: [] as api.PackingLineMatchOut[],
  cartons: [] as api.PackingCartonOut[],
  blockers: [] as string[],
  resolved_order_id: null as number | null,
  resolved_shipment_id: null as number | null,
  will_create_shipment: true,
};

describe("PackingCommitPanel C6", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mostra sugestão de um pedido e não commita sozinho", async () => {
    vi.mocked(api.fetchPackingPreview).mockResolvedValue({
      ...basePreview,
      blockers: ["order_id é obrigatório"],
      order_candidates: [
        {
          order_id: 1,
          order_code: "C46-328",
          status: "CONFIRMED",
          supplier_id: 4,
          currency: "EUR",
          evidence: ["Fornecedor do catálogo"],
          currency_match: true,
        },
      ],
      cartons: [
        {
          row_index: 0,
          carton_no: "1",
          items_per_ctn: "10",
          ncm: "95069900",
          description: "RACCHETTA",
          packaging: false,
        },
      ],
    });

    render(
      <MemoryRouter>
        <PackingCommitPanel documentId={9} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("packing-order-suggested")).toBeInTheDocument());
    expect(screen.getByTestId("packing-order-confirm-btn")).toBeDisabled();
    expect(screen.getByTestId("packing-commit-btn")).toBeDisabled();
    expect(screen.queryByTestId("packing-commit-result")).not.toBeInTheDocument();
    expect(screen.getByTestId("packing-carton-table")).toBeInTheDocument();
  });

  it("lista vários pedidos sem escolher em silêncio", async () => {
    vi.mocked(api.fetchPackingPreview).mockResolvedValue({
      ...basePreview,
      order_candidates: [
        {
          order_id: 1,
          order_code: "A",
          status: "CONFIRMED",
          supplier_id: 4,
          currency: "EUR",
          evidence: [],
          currency_match: true,
        },
        {
          order_id: 2,
          order_code: "B",
          status: "CONFIRMED",
          supplier_id: 4,
          currency: "EUR",
          evidence: [],
          currency_match: true,
        },
      ],
    });

    render(
      <MemoryRouter>
        <PackingCommitPanel documentId={9} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("packing-order-multiple")).toBeInTheDocument());
    expect(screen.getByTestId("packing-order-candidate-1")).toBeInTheDocument();
    expect(screen.getByTestId("packing-order-candidate-2")).toBeInTheDocument();
  });

  it("após commit SUCCEEDED, reload mostra packing processado e não reabre commit", async () => {
    vi.mocked(api.fetchPackingPreview).mockResolvedValue({
      ...basePreview,
      already_committed: true,
      can_commit: false,
      will_create_shipment: false,
      last_succeeded_attempt_id: 12,
      last_succeeded_shipment_id: 7,
      resolved_shipment_id: 7,
      blockers: [],
      operations: [
        {
          op_key: "create_shipment_planned",
          description: "Embarque já gerado a partir deste packing",
          entity_type: "shipment",
          params: { entity_id: "7" },
        },
      ],
    });

    render(
      <MemoryRouter>
        <PackingCommitPanel documentId={9} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("packing-processed-banner")).toBeInTheDocument());
    expect(screen.getByTestId("packing-shipment-link")).toHaveAttribute("href", "/shipments/7");
    expect(screen.getByTestId("packing-extraction-still-editable")).toBeInTheDocument();
    expect(screen.queryByTestId("packing-commit-btn")).not.toBeInTheDocument();
    expect(screen.queryByTestId("packing-order-candidates")).not.toBeInTheDocument();
  });
});
