import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { IngestionQueuePage } from "./IngestionQueuePage";
import { IngestionWorkspacePage } from "./IngestionWorkspacePage";
import { IntakePanel } from "./IntakePanel";
import * as api from "./ingestionApi";

vi.mock("./ingestionApi", async () => {
  const actual = await vi.importActual<typeof import("./ingestionApi")>("./ingestionApi");
  return {
    ...actual,
    fetchStagingQueue: vi.fn(),
    fetchIngestionDocument: vi.fn(),
    correctIngestionField: vi.fn(),
    restoreIngestionField: vi.fn(),
    createBatch: vi.fn(),
    uploadBatchFiles: vi.fn(),
    fetchAdapters: vi.fn(),
    classifyOccurrence: vi.fn(),
    fetchCommitPreview: vi.fn(),
  };
});

const writer: User = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: ["ingestion:read", "ingestion:write"],
};

describe("IngestionQueuePage", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    sessionStorage.clear();
    vi.mocked(api.fetchAdapters).mockResolvedValue([]);
  });

  it("lista documentos da fila", async () => {
    vi.mocked(api.fetchStagingQueue).mockResolvedValue([
      {
        id: 10,
        occurrence_id: 5,
        batch_id: 1,
        doc_type: "ORDINE",
        review_status: "DRAFT",
        version: 1,
        adapter_id: "contract_stub_v1",
        open_issue_count: 2,
        updated_at: null,
      },
    ]);
    render(
      <MemoryRouter>
        <IngestionQueuePage user={writer} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("ingestion-queue-table")).toBeInTheDocument());
    expect(screen.getByText("ORDINE")).toBeInTheDocument();
  });

  it("mostra loading e empty", async () => {
    vi.mocked(api.fetchStagingQueue).mockResolvedValue([]);
    render(
      <MemoryRouter>
        <IngestionQueuePage user={writer} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/carregando fila/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("empty-state")).toBeInTheDocument());
  });
});

describe("IntakePanel", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    sessionStorage.clear();
    vi.mocked(api.fetchAdapters).mockResolvedValue([]);
  });

  it("renderiza dropzone para writer", () => {
    const { getByTestId } = render(<IntakePanel user={writer} />);
    expect(getByTestId("ingestion-intake-panel")).toBeInTheDocument();
    expect(getByTestId("intake-dropzone")).toBeInTheDocument();
  });

  it("oculta para leitor sem write", () => {
    const reader = { ...writer, role: "viewer", permissions: ["ingestion:read"] };
    const { container } = render(<IntakePanel user={reader} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("IngestionWorkspacePage", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
          arrayBuffer: async () => new ArrayBuffer(0),
        }),
      ),
    );
  });

  it("carrega IR, viewer e issues", async () => {
    vi.mocked(api.fetchIngestionDocument).mockResolvedValue({
      id: 10,
      occurrence_id: 5,
      batch_id: 1,
      document_set_id: null,
      doc_type: "ORDINE",
      adapter_id: "contract_stub_v1",
      adapter_version: "1",
      ir_schema_version: "1",
      review_status: "IN_REVIEW",
      version: 2,
      locked_by_actor_id: null,
      locked_at: null,
      created_by_actor_id: "1",
      created_at: null,
      updated_at: null,
      sections: [],
      fields: [
        {
          id: 1,
          document_id: 10,
          section_id: null,
          field_key: "supplier_name",
          value_type: "string",
          raw_value: "ACME",
          normalized_value: "ACME",
          corrected_value: null,
          effective_value: "ACME",
          locator_json: JSON.stringify({ page: 1, x: 0.1, y: 0.2, w: 0.3, h: 0.05 }),
          provenance_json: null,
          review_status: "PENDING",
          version: 1,
        },
        {
          id: 2,
          document_id: 10,
          section_id: null,
          field_key: "order_number",
          value_type: "string",
          raw_value: "589",
          normalized_value: "589",
          corrected_value: null,
          effective_value: "589",
          locator_json: null,
          provenance_json: null,
          review_status: "PENDING",
          version: 1,
        },
        {
          id: 3,
          document_id: 10,
          section_id: null,
          field_key: "order_date",
          value_type: "string",
          raw_value: "2026-06-04",
          normalized_value: "2026-06-04",
          corrected_value: null,
          effective_value: "2026-06-04",
          locator_json: null,
          provenance_json: null,
          review_status: "PENDING",
          version: 1,
        },
      ],
      rows: [
        {
          id: 1,
          document_id: 10,
          section_id: null,
          row_index: 0,
          row_key: "I.V. 1",
          cells_json: JSON.stringify({
            sku: { raw: "I.V. 1", normalized: "I.V. 1" },
            description: { raw: "racchette", normalized: "racchette" },
            quantity: { raw: "100", normalized: "100" },
            line_total: { raw: "500", normalized: "500" },
          }),
          review_status: "PENDING",
          version: 1,
        },
      ],
      issues: [
        {
          id: 99,
          document_id: 10,
          severity: "ERROR",
          code: "SUPPLIER_NOT_FOUND",
          message: "Fornecedor ACME não encontrado",
          target_type: "DOCUMENT",
          target_id: null,
          status: "OPEN",
          locator_json: null,
        },
        {
          id: 100,
          document_id: 10,
          severity: "WARNING",
          code: "AMBIGUOUS_SKU",
          message: "I.V. 1",
          target_type: "ROW",
          target_id: 0,
          status: "OPEN",
          locator_json: null,
        },
      ],
      open_issue_count: 2,
    });

    vi.mocked(api.fetchCommitPreview).mockResolvedValue({
      can_commit: false,
      can_create_order: false,
      readiness_derived: false,
      human_summary: "Cadastre o fornecedor antes de criar o pedido.",
      blocking_reasons: ["Fornecedor ausente"],
      operations: [],
      fingerprint: "stub",
    } as never);

    render(
      <MemoryRouter initialEntries={["/ingestion/10"]}>
        <Routes>
          <Route path="/ingestion/:documentId" element={<IngestionWorkspacePage user={writer} />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("ingestion-workspace-page")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ingestion-pdf-viewer")).toBeInTheDocument();
    expect(screen.getByTestId("ordine-summary-panel")).toBeInTheDocument();
    expect(screen.getByTestId("ordine-before-create-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("ordine-math-known-false")).not.toBeInTheDocument();
    expect(screen.getByText(/ainda não cadastrado/i)).toBeInTheDocument();
    expect(screen.queryByText(/SUPPLIER_NOT_FOUND/)).not.toBeInTheDocument();
    expect(screen.queryByText(/AMBIGUOUS_SKU/)).not.toBeInTheDocument();
    expect(screen.getByTestId("ordine-summary-lines")).toBeInTheDocument();
    expect(screen.getByText(/compromisso/i)).toBeInTheDocument();
    expect(screen.getByText("04/06/2026")).toBeInTheDocument();
  });
});
