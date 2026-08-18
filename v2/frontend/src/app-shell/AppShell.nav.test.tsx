import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";

vi.mock("./RuntimeBadge", () => ({
  RuntimeBadge: () => null,
}));

vi.mock("../features/treasury/FxPanels", () => ({
  FxQuoteStrip: () => null,
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: [] as string[],
};

const NAV_ITEMS: { name: string; href: string }[] = [
  { name: "Produtos", href: "/catalog/products" },
  { name: "Fornecedores", href: "/catalog/suppliers" },
  { name: "Pedidos", href: "/orders" },
  { name: "Faturas", href: "/invoices" },
  { name: "Ingestão", href: "/ingestion" },
  { name: "Contas a pagar", href: "/payables" },
  { name: "Pagamentos realizados", href: "/payments" },
  { name: "Embarques", href: "/shipments" },
  { name: "Prestadores", href: "/logistics-providers" },
  { name: "Processos aduaneiros", href: "/customs" },
  { name: "Estoque", href: "/inventory/movements" },
  { name: "Usuários", href: "/admin/users" },
];

afterEach(() => {
  cleanup();
});

describe("AppShell nav icons", () => {
  it("mantém grupos e destinos com SVG distintos", () => {
    render(
      <MemoryRouter>
        <AppShell user={admin} onLogout={() => undefined} />
      </MemoryRouter>,
    );

    const nav = within(screen.getByRole("navigation", { name: /módulos/i }));
    expect(nav.getAllByText(/^Produtos$/i).length).toBeGreaterThanOrEqual(1);
    expect(nav.getByText(/^Compras$/i)).toBeInTheDocument();
    expect(nav.getByText(/^Financeiro$/i)).toBeInTheDocument();
    expect(nav.getByText(/^Logística$/i)).toBeInTheDocument();
    expect(nav.getByText(/^Aduana$/i)).toBeInTheDocument();
    expect(nav.getByText(/^Administração$/i)).toBeInTheDocument();

    const pathDs: string[] = [];
    for (const item of NAV_ITEMS) {
      const link = nav.getByRole("link", { name: item.name });
      expect(link).toHaveAttribute("href", item.href);
      const svg = link.querySelector("svg.shell-nav-icon");
      expect(svg).toBeTruthy();
      expect(svg).toHaveAttribute("width", "20");
      expect(svg).toHaveAttribute("height", "20");
      const d = [...(svg?.querySelectorAll("path") ?? [])]
        .map((p) => p.getAttribute("d") ?? "")
        .join("|");
      expect(d.length).toBeGreaterThan(24);
      pathDs.push(d);
    }
    expect(new Set(pathDs).size).toBe(pathDs.length);
  });

  it("esconde Administração sem users:read", () => {
    render(
      <MemoryRouter>
        <AppShell
          user={{
            ...admin,
            role: "comprador",
            permissions: ["orders:read", "catalog:read", "logistics:read"],
          }}
          onLogout={() => undefined}
        />
      </MemoryRouter>,
    );
    const nav = within(screen.getByRole("navigation", { name: /módulos/i }));
    expect(nav.queryByText(/^Administração$/i)).toBeNull();
    expect(nav.queryByRole("link", { name: "Usuários" })).toBeNull();
    expect(nav.getByRole("link", { name: "Produtos" })).toBeInTheDocument();
  });
});
