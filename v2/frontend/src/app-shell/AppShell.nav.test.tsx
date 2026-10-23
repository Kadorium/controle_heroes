import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
vi.mock("./RuntimeBadge",()=>({RuntimeBadge:()=>null}));
vi.mock("../features/treasury/FxPanels",()=>({FxQuoteStrip:()=>null}));
const admin={id:1,email:"admin@example.com",name:"Admin",role:"admin",permissions:[] as string[]};
afterEach(()=>{cleanup();localStorage.clear();});
const destinations=[
  ["Visão geral","/dashboard"],["Estoque atual","/inventory/positions"],["Produtos","/catalog/products"],
  ["Contas a pagar","/payables"],["Operações","/customs"],["Pedidos","/orders"],["Faturas","/invoices"],
  ["Conferir documentos","/ingestion"],["Pagamentos","/payments"],["Câmbio por obrigação","/payables?purpose=fx"],
  ["Custos de importação","/costing"],["Embarques","/shipments"],["Movimentos de estoque","/inventory/movements"],
  ["Fornecedores","/catalog/suppliers"],["Prestadores logísticos","/logistics-providers"],["Usuários e acessos","/admin/users"],
];
describe("experience navigation",()=>{
  it("preserves all destinations with inventory second and coherent icons",()=>{
    render(<MemoryRouter><AppShell user={admin} onLogout={()=>{}}/></MemoryRouter>);
    const nav=within(screen.getByRole("navigation",{name:"Módulos"}));
    for(const [name,href] of destinations){const a=nav.getByRole("link",{name});expect(a).toHaveAttribute("href",href);expect(a.querySelector("svg")).toBeTruthy();}
    expect(nav.getAllByRole("link")[1]).toHaveAttribute("href","/inventory/positions");
  });
  it("does not give inventory readers access to financial, catalog or admin destinations",()=>{
    render(<MemoryRouter><AppShell user={{...admin,role:"operacao",permissions:["inventory:read"]}} onLogout={()=>{}}/></MemoryRouter>);
    const links=within(screen.getByRole("navigation",{name:"Módulos"})).getAllByRole("link");
    expect(links.map(l=>l.getAttribute("href"))).toEqual(["/inventory/positions","/inventory/receiving","/inventory/movements"]);
  });
  it("financial reader without reporting keeps payments and FX",()=>{
    render(<MemoryRouter><AppShell user={{...admin,role:"financeiro",permissions:["billing:read","treasury:read","treasury:fx_read"]}} onLogout={()=>{}}/></MemoryRouter>);
    expect(screen.getByRole("link",{name:"Câmbio por obrigação"})).toBeInTheDocument();
    expect(screen.getByRole("link",{name:"Contas a pagar"})).toBeInTheDocument();
    expect(screen.queryByRole("link",{name:"Visão geral"})).toBeNull();
  });
  it("stock role can receive without a misleading financial destination",()=>{
    render(<MemoryRouter><AppShell user={{...admin,role:"estoque",permissions:["inventory:read","inventory:write","reporting:read","documents:read","audit:read"]}} onLogout={()=>{}}/></MemoryRouter>);
    expect(screen.getByRole("link",{name:"Recebimentos"})).toHaveAttribute("href","/inventory/receiving");
    expect(screen.queryByRole("link",{name:"Contas a pagar"})).toBeNull();
    expect(screen.queryByRole("link",{name:"Operações"})).toBeNull();
  });
  it("collapse persists without removing destinations or their accessible names",()=>{
    render(<MemoryRouter><AppShell user={admin} onLogout={()=>{}}/></MemoryRouter>);
    fireEvent.click(screen.getByRole("button",{name:"Recolher navegação"}));
    expect(localStorage.getItem("epic.navigation.expanded")).toBe("false");
    expect(screen.getByRole("link",{name:"Estoque atual"})).toHaveAttribute("title","Estoque atual");
    fireEvent.click(screen.getByRole("button",{name:"Expandir navegação"}));
    expect(screen.getByTestId("shell-rail-toggle")).toHaveAttribute("aria-expanded","true");
  });
});
