import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../auth/types";
import { FatturaCommitPanel } from "./FatturaCommitPanel";
import * as api from "./ingestionApi";

vi.mock("./ingestionApi", async () => {
  const actual = await vi.importActual<typeof import("./ingestionApi")>("./ingestionApi");
  return {
    ...actual,
    fetchFatturaPreview: vi.fn(),
    commitFatturaDocument: vi.fn(),
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
  permissions: ["ingestion:commit", "orders:write", "billing:write", "ingestion:read"],
};

describe("FatturaCommitPanel A0", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mostra sugestão de um pedido e não commita sozinho", async () => {
    vi.mocked(api.fetchFatturaPreview).mockResolvedValue({
      document_id: 32,
      fingerprint: "abc",
      policy_match: {
        policy: "A",
        order_id: null,
        order_status: null,
        order_code: null,
        invoice_will_be_created: false,
        warning: "order_id é obrigatório",
      },
      operations: [],
      open_error_count: 0,
      can_commit: false,
      order_candidates: [
        {
          order_id: 38,
          order_code: "A0-ONE",
          status: "CONFIRMED",
          supplier_id: 26,
          currency: "EUR",
          evidence: ["Fornecedor do catálogo"],
          currency_match: true,
        },
      ],
      order_candidates_reason: null,
      line_matches: [],
    });

    render(
      <MemoryRouter>
        <FatturaCommitPanel documentId={32} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("fattura-order-suggested")).toBeInTheDocument());
    expect(screen.getByTestId("fattura-order-confirm-btn")).toBeDisabled();
    expect(screen.queryByTestId("fattura-commit-result")).not.toBeInTheDocument();
  });

  it("lista vários pedidos sem escolher em silêncio", async () => {
    vi.mocked(api.fetchFatturaPreview).mockResolvedValue({
      document_id: 32,
      fingerprint: "abc",
      policy_match: {
        policy: "A",
        order_id: null,
        order_status: null,
        order_code: null,
        invoice_will_be_created: false,
        warning: "order_id é obrigatório",
      },
      operations: [],
      open_error_count: 0,
      can_commit: false,
      order_candidates: [
        {
          order_id: 41,
          order_code: "A0-A",
          status: "CONFIRMED",
          supplier_id: 26,
          currency: "EUR",
          evidence: ["SKU"],
          currency_match: true,
        },
        {
          order_id: 42,
          order_code: "A0-B",
          status: "CONFIRMED",
          supplier_id: 26,
          currency: "EUR",
          evidence: ["SKU"],
          currency_match: true,
        },
      ],
      order_candidates_reason: null,
      line_matches: [],
    });

    render(
      <MemoryRouter>
        <FatturaCommitPanel documentId={32} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("fattura-order-multiple")).toBeInTheDocument());
    expect(screen.getByTestId("fattura-order-candidate-41")).toBeInTheDocument();
    expect(screen.getByTestId("fattura-order-candidate-42")).toBeInTheDocument();
    expect(screen.getByTestId("fattura-order-id-input")).toHaveDisplayValue("");
  });

  it("após commit SUCCEEDED, reload mostra fattura processada e não reabre commit", async () => {
    vi.mocked(api.fetchFatturaPreview).mockResolvedValue({
      document_id: 32,
      fingerprint: "abc",
      policy_match: {
        policy: "A",
        order_id: null,
        order_status: null,
        order_code: null,
        invoice_will_be_created: false,
        warning: null,
      },
      operations: [],
      open_error_count: 0,
      can_commit: false,
      already_committed: true,
      last_succeeded_attempt_id: 9,
      last_succeeded_invoice_id: 4,
      order_candidates: [],
      order_candidates_reason: null,
      line_matches: [],
    });

    render(
      <MemoryRouter>
        <FatturaCommitPanel documentId={32} user={admin} />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("fattura-processed-banner")).toBeInTheDocument());
    expect(screen.getByTestId("fattura-invoice-link")).toHaveAttribute("href", "/invoices/4");
    expect(screen.queryByTestId("fattura-commit-submit")).not.toBeInTheDocument();
  });
});
