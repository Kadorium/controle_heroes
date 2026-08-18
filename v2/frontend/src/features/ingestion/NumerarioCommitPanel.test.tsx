import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { NumerarioCommitPanel } from "./NumerarioCommitPanel";
import * as api from "./ingestionApi";

vi.mock("./ingestionApi", async () => {
  const actual = await vi.importActual<typeof import("./ingestionApi")>("./ingestionApi");
  return {
    ...actual,
    fetchNumerarioPreview: vi.fn(),
    commitNumerarioDocument: vi.fn(),
    listDocumentCommitAttempts: vi.fn(),
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
  permissions: ["ingestion:commit", "customs:write", "ingestion:read"],
};

describe("NumerarioCommitPanel E7-TAX", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listDocumentCommitAttempts).mockResolvedValue([]);
  });

  it("não pede para colar process_ids e avisa que não paga", async () => {
    vi.mocked(api.fetchNumerarioPreview).mockResolvedValue({
      document_id: 20,
      fingerprint: "x",
      invoice_refs: ["181", "202"],
      process_ids_input: [],
      planned_operations: [],
      open_error_count: 0,
      can_commit: false,
      process_candidates: [],
      process_candidates_reason: "Nenhum processo com fatura ISSUED",
      already_committed: false,
      last_succeeded_attempt_id: null,
      can_create_process: true,
    });

    render(
      <MemoryRouter>
        <NumerarioCommitPanel documentId={20} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("numerario-no-payment-notice")).toBeInTheDocument());
    expect(screen.getByTestId("numerario-create-process-submit")).toBeInTheDocument();
    expect(screen.queryByLabelText(/process_ids/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("numerario-invoice-refs")).toHaveTextContent("202");
  });
});
