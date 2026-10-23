import { act, fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { InvoiceDetailPage } from "./InvoiceDetailPage";
import { getInvoice, setTerms, issueInvoice, type Invoice } from "./billingApi";

vi.mock("./billingApi", () => ({
  getInvoice: vi.fn(), setTerms: vi.fn(), issueInvoice: vi.fn(),
  replaceItems: vi.fn(), uploadInvoiceDocument: vi.fn(),
}));
const admin = { id: 1, email: "demo@example.invalid", name: "Demo", role: "admin", permissions: [] };
const invoice = (mode: string, terms: object[] = [], status = "DRAFT") => ({
  id: 1, order_id: 1, invoice_number: "DEMO", invoice_type: "FINAL", currency: "EUR",
  version: 1, status, net_amount: "1000.00", terms_mode: mode, terms, items: [],
  payables: [], payables_preview: [], documents: [], blockers: [],
} as unknown as Invoice);
function mount() {
  return render(<MemoryRouter initialEntries={["/invoices/1"]}><Routes>
    <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage user={admin} />} />
  </Routes></MemoryRouter>);
}
afterEach(() => { cleanup(); vi.resetAllMocks(); });

describe("persisted invoice terms vs unsaved editing slots", () => {
  for (const mode of ["PERCENT", "AMOUNT"]) for (const count of [1, 2]) {
    it(`${mode}: ${count} saved terms after issue and reload, no phantom row`, async () => {
      const terms = Array.from({ length: count }, (_, i) => ({ due_date: `2026-11-${21+i}`,
        percent: mode === "PERCENT" ? String(100/count) : null,
        amount: mode === "AMOUNT" ? String(1000/count) : null }));
      const persisted = invoice(mode, terms);
      vi.mocked(getInvoice).mockResolvedValue(invoice(mode));
      vi.mocked(setTerms).mockResolvedValue(persisted);
      vi.mocked(issueInvoice).mockResolvedValue({ ...persisted, status: "ISSUED" });
      const view = mount();
      await screen.findByTestId("term-date-1");
      for (let i=0; i<count; i++) {
        fireEvent.change(screen.getByTestId(`term-date-${i}`), { target: { value: terms[i].due_date } });
        const input = screen.getByTestId(`term-${mode === "PERCENT" ? "pct" : "amt"}-${i}`);
        fireEvent.change(input, { target: { value: mode === "PERCENT" ? String(100/count) : String(1000/count) } });
        fireEvent.blur(input);
      }
      fireEvent.click(screen.getByTestId("save-terms"));
      await waitFor(() => expect(setTerms).toHaveBeenCalledTimes(1));
      expect(vi.mocked(setTerms).mock.calls[0][3]).toHaveLength(count);
      // Draft slots remain editable; issuing uses the server's saved terms only.
      fireEvent.click(screen.getByTestId("issue-invoice"));
      fireEvent.click(await screen.findByTestId("confirm-modal-ok"));
      await screen.findByTestId("invoice-readonly");
      expect(screen.getAllByTestId(/^term-date-/)).toHaveLength(count);
      expect(screen.getByTestId("term-preview-0")).toHaveTextContent(count === 1 ? "1.000,00" : "500,00");
      view.unmount();
      vi.mocked(getInvoice).mockResolvedValue({ ...persisted, status: "ISSUED" });
      mount();
      await screen.findByTestId("invoice-readonly");
      expect(screen.getAllByTestId(/^term-date-/)).toHaveLength(count);
    });
  }
  it("a save response does not erase an edit typed while saving", async () => {
    vi.mocked(getInvoice).mockResolvedValue(invoice("PERCENT"));
    let finish!: (value: Invoice) => void;
    vi.mocked(setTerms).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    mount();
    fireEvent.change(await screen.findByTestId("term-date-0"), { target: { value: "2026-11-21" } });
    fireEvent.change(screen.getByTestId("term-pct-0"), { target: { value: "100" } });
    fireEvent.click(screen.getByTestId("save-terms"));
    fireEvent.change(screen.getByTestId("term-pct-0"), { target: { value: "60" } });
    await act(async () => finish(invoice("PERCENT", [{ due_date: "2026-11-21", percent: "100" }])));
    expect(screen.getByTestId("term-pct-0")).toHaveValue("60");
  });
});
