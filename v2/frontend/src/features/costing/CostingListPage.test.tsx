import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CostingListPage } from "./CostingListPage";

const mocks = vi.hoisted(() => ({ queue: vi.fn() }));
vi.mock("./costingApi", () => ({
  readCostingQueuePage: mocks.queue,
  ensureCostingCase: vi.fn(),
}));

beforeEach(() => {
  mocks.queue.mockReset();
  mocks.queue.mockResolvedValue({ items: [
      {
        id: null,
        import_process_id: 9,
        process_code: "IMP-1",
        process_reference: "DUIMP-X",
        process_status: "DRAFT",
        current_kind: null,
        current_status: null,
        included_total_brl: null,
        partial_coverage: null,
        updated_at: null,
      },
    ], total: 51, limit: 50, offset: 0 });
});

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: [] as string[],
};

afterEach(() => cleanup());

describe("CostingListPage", () => {
  it("mostra fila e subtítulo bruto", async () => {
    render(
      <MemoryRouter>
        <CostingListPage user={admin} />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("costing-queue")).toBeInTheDocument();
    expect(
      screen.getByText(/Não representa tratamento contábil ou fiscal de recuperabilidade/i),
    ).toBeInTheDocument();
    expect(await screen.findByText("IMP-1")).toBeInTheDocument();
  });

  it("preserva busca e situação ao paginar e reinicia página ao buscar", async () => {
    render(<MemoryRouter initialEntries={["/costing?q=OP-01&sit=ready&offset=50"]}>
      <CostingListPage user={admin} />
    </MemoryRouter>);
    await screen.findByText("IMP-1");
    expect(mocks.queue.mock.calls[0][0].get("offset")).toBe("50");
    fireEvent.click(screen.getByRole("button", {name:"Anterior"}));
    await waitFor(() => expect(mocks.queue).toHaveBeenCalledTimes(2));
    const previous = mocks.queue.mock.calls[1][0];
    expect(Object.fromEntries(previous)).toEqual({q:"OP-01",situation:"ready",limit:"50",offset:"0"});
    fireEvent.change(screen.getByLabelText("Código ou referência da operação"), {target:{value:"OP-010"}});
    fireEvent.click(screen.getByRole("button", {name:"Buscar"}));
    await waitFor(() => expect(mocks.queue).toHaveBeenCalledTimes(3));
    expect(Object.fromEntries(mocks.queue.mock.calls[2][0])).toEqual({q:"OP-010",situation:"ready",limit:"50",offset:"0"});
  });

  it("não consulta dados sem permissão de leitura", () => {
    render(<MemoryRouter><CostingListPage user={{...admin,role:"estoque",permissions:[]}} /></MemoryRouter>);
    expect(screen.getByText("É preciso costing:read.")).toBeInTheDocument();
    expect(mocks.queue).not.toHaveBeenCalled();
  });
});
