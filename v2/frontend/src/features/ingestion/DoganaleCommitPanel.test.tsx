import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { DoganaleCommitPanel } from "./DoganaleCommitPanel";
import * as api from "./ingestionApi";

vi.mock("./ingestionApi", async () => {
  const actual = await vi.importActual<typeof import("./ingestionApi")>("./ingestionApi");
  return {
    ...actual,
    fetchDoganalePreview: vi.fn(),
    commitDoganale: vi.fn(),
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

const basePreview = {
  document_id: 12,
  fingerprint: "abc",
  operations: [],
  open_error_count: 0,
  can_commit: false,
  process_targets: [] as api.DoganaleProcessTargetOut[],
  process_targets_reason: null as string | null,
  invoice_candidates: [] as api.DoganaleInvoiceCandidateOut[],
  invoice_candidates_reason: null as string | null,
  shipment_targets: [] as api.DoganaleShipmentTargetOut[],
  shipment_targets_reason: null as string | null,
  lines: [] as api.DoganaleLinePreviewOut[],
  blockers: [] as string[],
  resolved_process_id: null as number | null,
  resolved_invoice_id: null as number | null,
  resolved_shipment_id: null as number | null,
  will_create_process: true,
  reuse_reason: "created_empty" as string | null,
  already_committed: false,
  last_succeeded_attempt_id: null as number | null,
  last_succeeded_process_id: null as number | null,
  document_number: "328",
};

describe("DoganaleCommitPanel E7", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("explica que Doganale não contém imposto brasileiro e cria processo se não há candidato", async () => {
    vi.mocked(api.fetchDoganalePreview).mockResolvedValue({
      ...basePreview,
      can_commit: true,
      will_create_process: true,
      lines: [
        {
          position: 1,
          ncm: "95069900",
          description: "RACCHETTA",
          quantity: "50",
          unit: "SET",
          currency: "EUR",
          unit_price: "106.66",
          line_amount: "5333.00",
        },
      ],
    });

    render(
      <MemoryRouter>
        <DoganaleCommitPanel documentId={12} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("doganale-process-none")).toBeInTheDocument());
    expect(screen.getByText(/Não contém impostos brasileiros/)).toBeInTheDocument();
    expect(screen.getByTestId("doganale-commit-submit")).not.toBeDisabled();
    expect(screen.queryByLabelText(/process_ids/i)).not.toBeInTheDocument();
  });

  it("mostra 1 processo candidato e não commita sozinho", async () => {
    vi.mocked(api.fetchDoganalePreview).mockResolvedValue({
      ...basePreview,
      can_commit: false,
      will_create_process: false,
      process_targets_reason: "Há 1 processo candidato — confirme explicitamente.",
      process_targets: [
        {
          process_id: 7,
          code: "IP-7",
          status: "DRAFT",
          compatible: true,
          evidence: ["Fatura ISSUED já ligada"],
        },
      ],
    });

    render(
      <MemoryRouter>
        <DoganaleCommitPanel documentId={12} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("doganale-process-suggested")).toBeInTheDocument());
    expect(screen.getByTestId("doganale-commit-submit")).toBeDisabled();
    expect(screen.getByTestId("doganale-process-confirm")).toBeDisabled();
  });

  it("esconde o commit e mostra banner se já processado", async () => {
    vi.mocked(api.fetchDoganalePreview).mockResolvedValue({
      ...basePreview,
      can_commit: false,
      already_committed: true,
      last_succeeded_process_id: 9,
      will_create_process: false,
    });

    render(
      <MemoryRouter>
        <DoganaleCommitPanel documentId={12} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("doganale-processed-banner")).toBeInTheDocument());
    expect(screen.queryByTestId("doganale-commit-submit")).not.toBeInTheDocument();
    expect(screen.getByTestId("doganale-process-link")).toHaveAttribute("href", "/customs/9");
  });
});
