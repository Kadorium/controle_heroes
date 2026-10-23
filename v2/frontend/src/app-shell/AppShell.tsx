import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useState } from "react";
import type { User } from "../features/auth/types";
import { FxQuoteStrip } from "../features/treasury/FxPanels";
import { RuntimeBadge } from "./RuntimeBadge";
import { DemoTour } from "../features/demo/DemoTour";
import "./experience.css";

const paths: Record<string, string> = {
  home: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  stock: "m3 7 9-4 9 4v10l-9 4-9-4V7Zm0 0 9 4 9-4M12 11v10",
  product: "M3 3h9l9 9-9 9-9-9V3Zm5 5h.01",
  money: "M3 5h18v14H3zM3 9h18M7 14h4",
  operation: "M5 4h14v17H5zM9 2h6v5H9zM9 12h6M9 16h4",
};
function Icon({ name }: { name: string }) { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] ?? paths.operation} /></svg>; }
export function AppShell({ user, onLogout }: { user: User; onLogout: () => Promise<void> | void }) {
  const location = useLocation();
  const [expanded, setExpanded] = useState(() => localStorage.getItem("epic.navigation.expanded") !== "false");
  const can = (p: string) => user.role === "admin" || user.permissions.includes(p);
  const link = (to: string, label: string, permission: string, icon="operation", testId?: string) => can(permission) ? <NavLink key={to} to={to} aria-label={label} title={!expanded ? label : undefined} data-testid={testId}
    className={() => (to.includes("?") ? location.pathname + location.search === to : location.pathname.startsWith(to) && !(to === "/payables" && location.search.includes("purpose=fx"))) ? "active" : ""}>
    <Icon name={icon} /><span className="shell-nav-label">{label}</span></NavLink> : null;
  const activeGroup:Record<string,boolean> = {
    "Compras e documentos": /^\/(orders|invoices|ingestion)(\/|$)/.test(location.pathname),
    "Financeiro": /^\/(payments|costing)(\/|$)/.test(location.pathname) || location.pathname.includes("/fx") || location.search.includes("purpose=fx"),
    "Logística e histórico": /^\/(shipments|logistics-providers|inventory\/movements)(\/|$)/.test(location.pathname),
    "Cadastros": /^\/(catalog\/suppliers|admin)(\/|$)/.test(location.pathname),
  };
  const group = (label: string, children: React.ReactNode, visible: boolean) => visible ? <details className="experience-nav-group" open={!expanded || activeGroup[label] ? true : undefined}><summary title={label}>{expanded ? label : "···"}</summary>{children}</details> : null;
  return <div className={`shell shell-sidebar-layout experience-shell ${expanded ? "experience-expanded" : "experience-collapsed"}`}>
    <a className="skip-link" href="#main-content">Ir para o conteúdo</a>
    <aside className="shell-sidebar" aria-label="Navegação principal">
      <div className="experience-brand"><span className="experience-mark">E</span>{expanded && <div><strong>EPIC</strong><small>Controle</small></div>}
        <button className="shell-rail-toggle" data-testid="shell-rail-toggle" aria-expanded={expanded} aria-label={expanded ? "Recolher navegação" : "Expandir navegação"} onClick={() => setExpanded(v => { localStorage.setItem("epic.navigation.expanded", String(!v)); return !v; })}>{expanded ? "‹" : "›"}</button></div>
      <nav className="shell-side-nav" aria-label="Módulos">
        {link("/dashboard", "Visão geral", "reporting:read", "home", "nav-dashboard")}
        {link("/inventory/positions", "Estoque atual", "inventory:read", "stock", "nav-stock")}
        {link("/inventory/receiving", "Recebimentos", "inventory:read", "stock", "nav-receiving")}
        {link("/catalog/products", "Produtos", "catalog:read", "product")}
        {link("/payables", "Contas a pagar", "billing:read", "money")}
        {link("/customs", "Operações", "customs:read", "operation")}
        {group("Compras e documentos", <>{link("/orders", "Pedidos", "orders:read")}{link("/invoices", "Faturas", "billing:read")}{link("/ingestion", "Conferir documentos", "ingestion:read", "operation", "nav-ingestion")}</>, can("orders:read") || can("billing:read") || can("ingestion:read"))}
        {group("Financeiro", <>{link("/payments", "Pagamentos", "treasury:read", "money")}{link("/payables?purpose=fx", "Câmbio por obrigação", "treasury:fx_read", "money")}{link("/costing", "Custos de importação", "costing:read", "money", "nav-costing")}</>, can("treasury:read") || can("treasury:fx_read") || can("costing:read"))}
        {group("Logística e histórico", <>{link("/shipments", "Embarques", "logistics:read", "stock")}{link("/inventory/movements", "Movimentos de estoque", "inventory:read", "stock")}{link("/logistics-providers", "Prestadores logísticos", "logistics:read")}</>, can("logistics:read") || can("inventory:read"))}
        {group("Cadastros", <>{link("/catalog/suppliers", "Fornecedores", "catalog:read")}{link("/admin/users", "Usuários e acessos", "users:read")}</>, can("catalog:read") || can("users:read"))}
      </nav>
      <div className="shell-side-footer"><RuntimeBadge /><div className="shell-fx-slot"><FxQuoteStrip user={user} /></div>
        {expanded && <small className="experience-user">{user.name}</small>}<button className="shell-logout" aria-label="Sair" onClick={async () => { await fetch("/api/auth/logout", { method:"POST", credentials:"include" }); await onLogout(); }}>Sair</button></div>
    </aside>
    <div className="shell-content"><main id="main-content" className="shell-main" tabIndex={-1}>
      {import.meta.env.VITE_ENABLE_DEMO === "true" && user.role === "admin" ? <DemoTour /> : null}<Outlet />
    </main></div>
  </div>;
}
