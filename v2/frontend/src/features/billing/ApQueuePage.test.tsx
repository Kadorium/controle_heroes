import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApQueuePage } from "./ApQueuePage";
import { fetchApQueue, type ApQueueResponse } from "../reporting/reportingApi";
vi.mock("../reporting/reportingApi", () => ({ fetchApQueue: vi.fn() }));
vi.mock("../catalog/useCatalogSearch", () => ({ useSupplierSearch: () => [] }));
vi.mock("../../navigation/useListReturn", () => ({ useListReturn: () => undefined }));
const admin = { id: 1, name: "Admin", email: "fixture@example.invalid", role: "admin", permissions: [] };
const data: ApQueueResponse = { items: [], total: 2, limit: 50, offset: 0, kpis: { total_count: 2, kpis_by_currency: ["BRL", "EUR"].map(currency => ({ currency, open_balance: "1200", overdue_balance: "0", due_today_balance: "0", next_7d_balance: "0", overdue_count: 0, total_count: 1 })) } };
function Location() { return <output data-testid="location">{useLocation().search}</output>; }
function mount(query = "?pending=OPEN_BALANCE") { return render(<MemoryRouter initialEntries={[`/payables${query}`]}><ApQueuePage user={admin} /><Location /></MemoryRouter>); }
beforeEach(() => { vi.mocked(fetchApQueue).mockResolvedValue(data); });
afterEach(() => { cleanup(); vi.resetAllMocks(); });
it("applies currency and due filter atomically while preserving invoice context", async () => {
  mount("?pending=OPEN_BALANCE&invoice_id=19");
  fireEvent.click(await screen.findByTestId("kpi-overdue-EUR"));
  await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("currency=EUR"));
  expect(screen.getByTestId("location")).toHaveTextContent("due_before=");
  expect(screen.getByTestId("location")).toHaveTextContent("invoice_id=19");
});
it("exposes custom URL dates and invoice filters, then clears both", async () => {
  mount("?pending=ALL&invoice_id=19&due_after=2026-12-01&due_before=2026-12-31");
  expect(screen.getByTestId("filter-bar-active")).toHaveTextContent("Fatura: 19");
  expect(screen.getByTestId("filter-bar-active")).toHaveTextContent("01/12/2026");
  fireEvent.click(screen.getByTestId("filter-bar-clear-all"));
  await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("?pending=OPEN_BALANCE"));
  expect(screen.getByTestId("location")).not.toHaveTextContent("invoice_id");
});
it("does not fabricate zero during loading, failure or absent KPI", async () => {
  vi.mocked(fetchApQueue).mockReturnValue(new Promise(() => undefined));
  const view = mount();
  expect(screen.getByText("Carregando contas a pagar…")).toBeVisible();
  expect(screen.queryByTestId("kpi-total-count")).toBeNull();
  view.unmount();
  vi.mocked(fetchApQueue).mockRejectedValue(new Error("Falha controlada")); mount();
  expect(await screen.findByText("Falha controlada")).toBeVisible();
  expect(screen.queryByText("Nenhuma obrigação neste filtro")).toBeNull();
  cleanup();
  vi.mocked(fetchApQueue).mockResolvedValue({ ...data, kpis: {}, total: 0 }); mount();
  expect(await screen.findByText("Nenhum saldo por moeda informado.")).toBeVisible();
  expect(screen.queryByTestId("kpi-open-balance-EUR")).toBeNull();
});
it("ignores an old response after the user changes filters", async () => {
  let finish!: (v: ApQueueResponse) => void;
  vi.mocked(fetchApQueue).mockReturnValueOnce(new Promise(resolve => { finish = resolve; })).mockResolvedValue({ ...data, kpis: { total_count: 0 } });
  mount(); fireEvent.change(screen.getByTestId("ap-filter-due"), { target: { value: "today" } });
  expect(await screen.findByText("Nenhum saldo por moeda informado.")).toBeVisible();
  finish(data);
  await waitFor(() => expect(screen.queryByTestId("kpi-open-balance-EUR")).toBeNull());
});
