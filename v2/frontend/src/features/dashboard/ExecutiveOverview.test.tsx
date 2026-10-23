import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ExecutiveOverview } from "./ExecutiveOverview";
import { OperationalPriorities } from "./OperationalPriorities";
import { DashboardPage } from "./DashboardPage";
import { isSystemExecutive } from "./executiveDisplay";
import { fetchDashboard, fetchMetricCatalog, fetchViews, type DashboardSnapshot, type DashboardWidget } from "./dashboardApi";
vi.mock("./dashboardApi", async importOriginal => ({ ...await importOriginal<typeof import("./dashboardApi")>(), fetchDashboard: vi.fn(), fetchMetricCatalog: vi.fn(), fetchViews: vi.fn() }));
const widget = (id: string, display: Record<string, unknown>): DashboardWidget => ({ widget_id: id, metric_id: id, label: id === "orders.to_invoice" ? "A faturar" : id, short_description: "Descrição", kind: "kpi_currency", status: "AVAILABLE", display, drill: "/payables", currencies: [], filters_applied: [], filters_ignored: [] });
const snap = (widgets: DashboardWidget[], id = "executiva"): DashboardSnapshot => ({ generated_at: "2026-10-22T15:00:00-03:00", view_id: id, view_name: id, base_preset: "executiva", filters: {}, lane: { lane: "test", includes_trial_mass: true }, widgets, home_ok: true, fallback_path: "/orders", default_preset: "executiva" });
const emptyControl = snap([widget("control.exceptions", { items: [], total_count: 0, state: "ok", errors: [] })], "controle");
const wrap = (children: React.ReactNode, entry = "/dashboard") => render(<MemoryRouter initialEntries={[entry]}>{children}</MemoryRouter>);
const overview = (widgets: DashboardWidget[]) => wrap(<ExecutiveOverview snapshot={snap(widgets)} refreshKey={0} onExplain={() => {}} onSeeAll={() => {}} />);
beforeEach(() => { vi.stubGlobal("scrollTo", vi.fn()); vi.mocked(fetchDashboard).mockResolvedValue(emptyControl); vi.mocked(fetchViews).mockResolvedValue([]); vi.mocked(fetchMetricCatalog).mockResolvedValue({ generated_at: "", presets: [], metrics: [], widgets: [] }); });
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.unstubAllGlobals(); });

describe("Executive composition: factual states and boundaries", () => {
  it("applies only to the system Executiva, including resolved defaults", () => {
    expect(isSystemExecutive(snap([]))).toBe(true);
    expect(isSystemExecutive(snap([], "41"))).toBe(false);
    expect(isSystemExecutive({ ...snap([]), view_id: null })).toBe(false);
  });
  it("confirms no overdue obligations only after explicit successful counts", async () => {
    overview([widget("ap.overdue", { state: "ok", total_count: 0, overdue_count: 0, by_currency: [] })]);
    expect(screen.getByText("Nenhuma obrigação vencida no recorte consultado.")).toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it.each([{}, { state: "ok", total_count: null }, { state: "error", total_count: 0, overdue_count: 0 }])("does not interpret incomplete/error as zero: %j", async display => {
    overview([widget("ap.overdue", display)]);
    expect(screen.queryByText("Nenhuma")).not.toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it("preserves zero, null, currencies and large amounts without adding them", async () => {
    overview([widget("orders.to_invoice", { by_currency: [{ currency: "EUR", amount: "0.00" }, { currency: "USD", amount: null }, { currency: "BRL", amount: "123456789.12" }] })]);
    expect(screen.getByText("EUR 0,00")).toBeInTheDocument();
    expect(screen.getByText("USD —")).toBeInTheDocument();
    expect(screen.getByTitle("BRL 123.456.789,12")).toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it("missing quote cannot create a zero BRL equivalent", async () => {
    overview([widget("treasury.fx_exposure", { hero_brl: null, quote: null, foreign: [{ currency: "EUR", open_balance: "25.00" }] })]);
    expect(screen.getByText("Cotação indisponível")).toBeInTheDocument();
    expect(screen.getByText("EUR 25,00")).toBeInTheDocument();
    expect(screen.queryByText("BRL 0,00")).not.toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it("uses returned months and marks stale rates, not the HTML example", async () => {
    overview([widget("ap.cash_due", { by_currency: [{ currency: "EUR", amount: "7.00" }] }), widget("ap.cash_committed", { labels: { m0: "Janeiro", m1: "Fevereiro", m2: "Março" }, by_currency: [] }), widget("treasury.fx_exposure", { hero_brl: "35.00", foreign: [{ currency: "EUR", open_balance: "7" }], quote: { rate: "5", stale: true } })]);
    expect(screen.getByText("Compromissos · Janeiro–Março")).toBeInTheDocument();
    expect(screen.getByText(/cotação desatualizada/)).toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it("one observation is a dated reference, not a chart", async () => {
    overview([widget("treasury.fx_trend", { days: 30, foreign: "EUR", base: "BRL", points: [{ date: "2026-08-01", rate: "6.12", source: "Fonte verificada" }] })]);
    expect(screen.queryByTestId("chart-trend")).not.toBeInTheDocument();
    expect(screen.getByText(/Um dia observado/)).toBeInTheDocument();
    expect(screen.getByText(/01\/08\/2026 · Fonte verificada/)).toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it("empty history does not fabricate axes or zero", async () => {
    overview([widget("treasury.fx_trend", { days: 30, points: [] })]);
    expect(screen.getByText("Sem cotações na série consultada.")).toBeInTheDocument();
    expect(screen.queryByTestId("chart-trend")).not.toBeInTheDocument();
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
  it("uses returned operation destinations and distinct units", async () => {
    overview([widget("goods.flow", { segments: [{ key: "customs", value: 2, href: "/customs?status=SUBMITTED" }] })]);
    expect(screen.getByRole("link", { name: "Consultar processos na aduana" })).toHaveAttribute("href", "/customs?status=SUBMITTED");
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
  });
});
describe("Control query: local lifecycle, ACL and order", () => {
  it("shows loading without an all-clear and aborts on unmount", () => {
    vi.mocked(fetchDashboard).mockReturnValue(new Promise(() => {}));
    const { unmount } = wrap(<OperationalPriorities refreshKey={0} />);
    expect(screen.getByText("Consultando prioridades…")).toBeInTheDocument();
    const signal = vi.mocked(fetchDashboard).mock.calls[0][1]; unmount(); expect(signal?.aborted).toBe(true);
  });
  it("shows failure and supports local retry", async () => {
    vi.mocked(fetchDashboard).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(emptyControl);
    wrap(<OperationalPriorities refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    await screen.findByText("Nenhuma exceção nas áreas consultadas.");
    expect(fetchDashboard).toHaveBeenCalledTimes(2);
  });
  it("does not replace ACL omission with no exceptions", async () => {
    vi.mocked(fetchDashboard).mockResolvedValue(snap([], "controle"));
    wrap(<OperationalPriorities refreshKey={0} />);
    await screen.findByText("Prioridades indisponíveis para este acesso.");
    expect(screen.queryByText("Nenhuma exceção nas áreas consultadas.")).not.toBeInTheDocument();
  });
  it("keeps server ordering, severity, long text and href under partial failure", async () => {
    vi.mocked(fetchDashboard).mockResolvedValue(snap([widget("control.exceptions", { state: "ok", errors: ["inventory"], total_count: 2, items: [{ title: "Referência operacional extensa ".repeat(5), reason: "Documento pendente", severity: "warning", module: "customs", href: "/customs/789" }, { title: "Segundo", severity: "blocker", href: "/orders/456" }] })]));
    wrap(<OperationalPriorities refreshKey={0} />);
    await screen.findByText(/Consulta parcial/);
    expect(screen.getByRole("link", { name: "Consultar origem →" })).toHaveAttribute("href", "/customs/789");
    expect(screen.getByText("Atenção · Aduana")).toBeInTheDocument();
    expect(fetchDashboard).toHaveBeenCalledTimes(1);
  });
  it("preserves personal layout order and excludes the new system composition", async () => {
    const personal = snap([widget("orders.to_invoice", { by_currency: [{ currency: "EUR", amount: "2" }] }), widget("ap.overdue", { by_currency: [{ currency: "EUR", amount: "1" }] })], "42");
    vi.mocked(fetchDashboard).mockResolvedValue(personal);
    wrap(<DashboardPage user={{ id: 1, role: "admin", permissions: [] } as never} />, "/dashboard?view=42");
    await screen.findByTestId("dash-widget-orders.to_invoice");
    expect(screen.queryByTestId("executive-summary")).not.toBeInTheDocument();
    expect(screen.getAllByTestId(/^dash-widget-/).map(el => el.dataset.testid)).toEqual(["dash-widget-orders.to_invoice", "dash-widget-ap.overdue"]);
    expect(fetchDashboard).toHaveBeenCalledTimes(1);
  });
  it("failed refresh retains the dated snapshot, not a success timestamp", async () => {
    vi.mocked(fetchDashboard).mockResolvedValueOnce(snap([widget("orders.to_invoice", { by_currency: [{ currency: "EUR", amount: "12" }] })], "financeiro")).mockRejectedValueOnce(new Error("offline"));
    wrap(<DashboardPage user={{ id: 1, role: "admin", permissions: [] } as never} />);
    await screen.findByText("€ 12,00"); fireEvent.click(screen.getByRole("button", { name: "Atualizar" }));
    await screen.findByText(/Os valores abaixo não foram atualizados/);
    expect(screen.getByText("€ 12,00")).toBeInTheDocument();
  });
});
