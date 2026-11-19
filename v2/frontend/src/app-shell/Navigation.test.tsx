import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import { activeNavigation, visibleNavigation } from "./navigation";
vi.mock("./RuntimeBadge", () => ({ RuntimeBadge: () => null }));
vi.mock("../features/treasury/FxPanels", () => ({ FxQuoteStrip: () => null }));
const admin = { id:1, email:"admin@example.com", name:"Admin", role:"admin", permissions:[] as string[] };
const actor = (...permissions: string[]) => ({ ...admin, role:"restricted", permissions });
afterEach(() => { cleanup(); localStorage.clear(); sessionStorage.clear(); });
function mount(user = admin, path = "/dashboard") {
  render(<MemoryRouter initialEntries={[path]}><AppShell user={user} onLogout={()=>{}} /></MemoryRouter>);
  return within(screen.getByRole("navigation", { name:"Módulos" }));
}
describe("consolidated navigation", () => {
  it("has five stable primary areas and two secondary entries opening work screens", () => {
    const nav = mount();
    expect(nav.getAllByRole("link").map(link => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Visão geral","/dashboard"], ["Produtos","/inventory/positions"], ["Compras","/orders"],
      ["Importações","/customs"], ["Financeiro","/payables"], ["Conferir documentos","/ingestion"], ["Usuários e acessos","/admin/users"],
    ]);
    expect(nav.queryByRole("link", { name:"Estoque atual" })).toBeNull();
  });
  it.each([
    ["inventory:read", [["products","/inventory/positions"],["imports","/inventory/receiving"]]],
    ["catalog:read", [["products","/catalog/products"],["purchases","/catalog/suppliers"]]],
    ["costing:read", [["imports","/costing"]]],
    ["logistics:read", [["imports","/shipments"]]],
    ["billing:read", [["purchases","/invoices"],["finance","/payables"]]],
    ["treasury:read", [["finance","/payments"]]],
    ["treasury:fx_read", [["finance","/payables?purpose=fx"]]],
    ["users:read", [["access","/admin/users"]]],
    ["ingestion:read", [["documents","/ingestion"]]],
    ["customs:read", [["imports","/customs"]]],
  ])("uses an authorized fallback for %s", (permission, expected) => {
    expect(visibleNavigation(actor(permission as string)).map(a=>[a.id,a.sections[0].to])).toEqual(expected);
  });
  it.each(["/orders/5","/orders/5/commercial","/customs/5"])("does not stack area tabs above record headers at %s", path=>{
    mount(admin,path);expect(screen.queryByRole("navigation",{name:/Área de/})).toBeNull();
  });
  it("keeps the five import work queues in the agreed order",()=>{
    mount(admin,"/customs");expect(within(screen.getByRole("navigation",{name:"Área de importações"})).getAllByRole("link").map(x=>x.textContent)).toEqual(["Operações","Mercadorias a receber","Embarques","Custo desembarcado","Prestadores logísticos"]);
  });
  it("does not expose areas with no readable sections", () => {
    expect(visibleNavigation(actor("inventory:write", "catalog:write"))).toEqual([]);
  });
  it("stock users can receive without customs or financial access", () => {
    const nav=mount(actor("inventory:read","inventory:write","reporting:read"),"/inventory/receiving?item=4&state=all");
    expect(nav.getByRole("link",{name:"Importações"})).toHaveAttribute("aria-current","page");
    const local=within(screen.getByRole("navigation",{name:"Área de importações"}));
    expect(local.getAllByRole("link").map(a=>a.textContent)).toEqual(["Mercadorias a receber"]);
    expect(local.getByRole("link")).toHaveAttribute("href","/inventory/receiving?item=4&state=all");
    expect(nav.queryByRole("link",{name:"Financeiro"})).toBeNull();
  });
  it("removes duplicate FX tab when AP is allowed and keeps the old deep link active", () => {
    mount(admin,"/payables/42/fx?origin=invoice");
    expect(screen.queryByRole("link",{name:"Câmbio por obrigação"})).toBeNull();
    expect(screen.getByRole("link",{name:"Contas a pagar"})).toHaveAttribute("aria-current","page");
    expect(screen.getByRole("link",{name:"Financeiro"})).toHaveAttribute("aria-current","page");
  });
  it("preserves query parameters when reselecting the current list", () => {
    mount(admin,"/payables?purpose=fx&currency=EUR&due_before=2026-12-01&offset=50");
    expect(screen.getByRole("link",{name:"Contas a pagar"})).toHaveAttribute("href","/payables?purpose=fx&currency=EUR&due_before=2026-12-01&offset=50");
  });
  it.each([
    ["/catalog/products/3/edit","products","catalog"], ["/catalog/prices/import","products","catalog"],
    ["/inventory/sku/3","products","stock"], ["/inventory/movements","products","history"],
    ["/invoices/4","purchases","invoices"], ["/orders/5/commercial","purchases","orders"],
    ["/costing/2/compare","imports","costing"], ["/customs/funding/7","imports","operations"],
    ["/logistics-providers","imports","providers"], ["/ingestion/7","documents","documents"],
  ])("selects area and section for old detail URL %s", (path, area, section) => {
    const active=activeNavigation(visibleNavigation(admin),path);
    expect([active.area?.id,active.section?.id]).toEqual([area,section]);
  });
  it("matches path segments rather than prefixes of unrelated URLs", () => {
    expect(activeNavigation(visibleNavigation(admin),"/orders-archive").area).toBeUndefined();
  });
  it("keeps all destinations and visible captions when collapsed", () => {
    const nav=mount();fireEvent.click(screen.getByRole("button",{name:"Recolher navegação"}));
    expect(localStorage.getItem("epic.navigation.expanded")).toBe("false");
    expect(nav.getAllByRole("link")).toHaveLength(7);
    expect(nav.getByRole("link",{name:"Importações"})).toHaveAttribute("title","Importações");
    expect(nav.getByRole("link",{name:"Produtos"}).querySelector(".nav-rail-caption")).toHaveTextContent("Produtos");
  });
});
