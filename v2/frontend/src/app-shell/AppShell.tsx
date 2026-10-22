import { NavLink, Outlet } from "react-router-dom";
import { useState, type ReactNode } from "react";
import type { User } from "../features/auth/types";
import { FxQuoteStrip } from "../features/treasury/FxPanels";
import { Button, roleLabel } from "../ui";
import { RuntimeBadge } from "./RuntimeBadge";

type Props = {
  user: User;
  onLogout: () => Promise<void> | void;
};

function can(user: User, perm: string) {
  return user.role === "admin" || (user.permissions ?? []).includes(perm);
}

/**
 * Ícones SVG inline mínimos — sem pacote externo (DECISÃO-RAIL Opção A).
 * Silhuetas distintas; detalhes internos via evenodd (recortes).
 */
function NavIcon({ d }: { d: string }) {
  return (
    <svg
      className="shell-nav-icon"
      width="20"
      height="20"
      viewBox="0 0 20 20"
      aria-hidden="true"
      focusable="false"
    >
      <path fill="currentColor" d={d} />
    </svg>
  );
}

function IconOrders() {
  return (
    <NavIcon d="M7.1 1.8h5.8v1.9H7.1V1.8zM4.2 3.1h2.3v2.3h7V3.1h2.3v14.9H4.2V3.1zm3.4 4.8h4.8v1.3H7.6V7.9zm0 2.8h4.8v1.3H7.6v-1.3zm0 2.8h3.2v1.3H7.6v-1.3z" />
  );
}

function IconInvoices() {
  return <NavIcon d="M5 1.9h7.4L16 6.5v11.6H5V1.9zm7.2.4v3.9h3.9M7.2 9.2h5.6v1.3H7.2V9.2zm0 2.8h4.2v1.3H7.2v-1.3z" />;
}

function IconIngestion() {
  return <NavIcon d="M9 1.6h2v6.1h2.8L10 12.5 6.2 7.7H9V1.6zM2.5 13.2h15v1.5h-1.7L14 18H6L4.2 14.7H2.5v-1.5z" />;
}

function IconPayables() {
  return (
    <NavIcon d="M2 6.3h16v8.8H2V6.3zm2.2 2h3.4v1.2H4.2V8.3zm9.4 0h2.4v1.2h-2.4V8.3zM10 8.6a2.3 2.3 0 1 0 0 4.6 2.3 2.3 0 0 0 0-4.6z" />
  );
}

function IconPayments() {
  return (
    <NavIcon d="M10 1.7a8.3 8.3 0 1 1 0 16.6 8.3 8.3 0 0 1 0-16.6zm3.5 5.3-4.8 5.4-2.4-2.4-1.3 1.3 3.7 3.7 6.1-7z" />
  );
}

function IconShipments() {
  return (
    <NavIcon d="M1.6 7.1h9.1V4.6h5.2l2.6 3.6v5.2h-1.5a2.2 2.2 0 0 1-4.3 0H8.1a2.2 2.2 0 0 1-4.3 0H1.6V7.1zm2.9 6.3a1.15 1.15 0 1 0 0 2.3 1.15 1.15 0 0 0 0-2.3zm9.5 0a1.15 1.15 0 1 0 0 2.3 1.15 1.15 0 0 0 0-2.3zM11.2 6.1v2.8h4.1L13.8 6.1h-2.6z" />
  );
}

function IconCustoms() {
  return (
    <NavIcon d="M10 1.6a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zm0 2.3 1.4 2.7 3 .4-2.2 2.1.5 2.9L10 10.5 7.3 12l.5-2.9-2.2-2.1 3-.4L10 3.9zM3.1 16.1h13.8v1.8H3.1z" />
  );
}

function IconInventory() {
  return (
    <NavIcon d="M10 1.7 16.5 5v.3L10 8.6 3.5 5.3V5L10 1.7zM3.5 6.7 9.3 9.6v6.6L3.5 13.4V6.7zm13 0v6.7L10.7 16.2V9.6l5.8-2.9z" />
  );
}

function IconProducts() {
  return <NavIcon d="M3.4 8.1 8.1 3.4h7.4v7.4L10.8 16.6 3.4 9.2V8.1zm9.4-3.2a1.35 1.35 0 1 0 0 2.7 1.35 1.35 0 0 0 0-2.7z" />;
}

function IconUsers() {
  return (
    <NavIcon d="M10 2.1a3.05 3.05 0 1 1 0 6.1 3.05 3.05 0 0 1 0-6.1zM4.1 16.7c.5-3.5 2.9-5.3 5.9-5.3s5.4 1.8 5.9 5.3H4.1z" />
  );
}

function IconCosting() {
  return (
    <NavIcon d="M3.2 16.4 10 2.4l6.8 14H3.2zm6.8-4.2h1.4v1.6H10v-1.6zm0-5.2h1.4v4H10v-4z" />
  );
}

function IconDashboard() {
  return (
    <NavIcon d="M2.2 2.2h7.1v7.1H2.2V2.2zm8.5 0h7.1v4.4h-7.1V2.2zM2.2 10.7h7.1v7.1H2.2v-7.1zm8.5 5.3h7.1v1.8h-7.1v-1.8zm0-5.3h7.1v4.1h-7.1V10.7z" />
  );
}

function SideLink({
  to,
  label,
  testId,
  children,
}: {
  to: string;
  label: string;
  testId?: string;
  children: ReactNode;
}) {
  return (
    <NavLink to={to} aria-label={label} data-label={label} data-testid={testId}>
      {children}
      <span className="shell-nav-label">{label}</span>
    </NavLink>
  );
}

export function AppShell({ user, onLogout }: Props) {
  const [railOpen, setRailOpen] = useState(false);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    await onLogout();
  }

  const canOrders = can(user, "orders:read");
  const canBilling = can(user, "billing:read");
  const canTreasury = can(user, "treasury:read");
  const canReporting = can(user, "reporting:read");
  const canLogistics = can(user, "logistics:read");
  const canCustoms = can(user, "customs:read");
  const canInventory = can(user, "inventory:read");
  const canIngestion = can(user, "ingestion:read");
  const canCatalog = can(user, "catalog:read");
  const canCosting = can(user, "costing:read");
  const canUsers = can(user, "users:read");
  const showCatalogo = canCatalog;
  const showCompras = canOrders || canBilling || canIngestion;
  const showFinanceiro = canReporting || canBilling || canTreasury;
  const showCustos = canCosting;
  const showLogistica = canLogistics;
  const showAduana = canCustoms || canInventory;
  const showAdministracao = canUsers;

  return (
    <div
      className={["shell", "shell-sidebar-layout", "shell--auto-compact", railOpen ? "shell--rail-open" : null]
        .filter(Boolean)
        .join(" ")}
    >
      <a className="skip-link" href="#main-content">
        Ir para o conteúdo
      </a>
      <aside className="shell-sidebar" aria-label="Navegação principal">
        <div className="shell-brand">
          <strong className="shell-brand-full">Epic Controle</strong>
          <strong className="shell-brand-rail" aria-hidden="true">
            EC
          </strong>
          <div className="shell-user">
            {user.name} · {roleLabel(user.role)}
          </div>
        </div>
        <nav className="shell-side-nav" aria-label="Módulos">
          {canReporting ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-visao">
                Visão
              </div>
              <div role="group" aria-labelledby="nav-visao">
                <SideLink to="/dashboard" label="Painel" testId="nav-dashboard">
                  <IconDashboard />
                </SideLink>
              </div>
            </div>
          ) : null}
          {showCompras ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-compras">
                Compras
              </div>
              <div role="group" aria-labelledby="nav-compras">
                {canOrders ? (
                  <SideLink to="/orders" label="Pedidos">
                    <IconOrders />
                  </SideLink>
                ) : null}
                {canBilling ? (
                  <SideLink to="/invoices" label="Faturas">
                    <IconInvoices />
                  </SideLink>
                ) : null}
                {canIngestion ? (
                  <SideLink to="/ingestion" label="Ingestão" testId="nav-ingestion">
                    <IconIngestion />
                  </SideLink>
                ) : null}
              </div>
            </div>
          ) : null}
          {showFinanceiro ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-financeiro">
                Financeiro
              </div>
              <div role="group" aria-labelledby="nav-financeiro">
                {canReporting || canBilling ? (
                  <SideLink to="/payables" label="Contas a pagar">
                    <IconPayables />
                  </SideLink>
                ) : null}
                {canTreasury ? (
                  <SideLink to="/payments" label="Pagamentos realizados">
                    <IconPayments />
                  </SideLink>
                ) : null}
              </div>
            </div>
          ) : null}
          {showCustos ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-custos">
                Custos
              </div>
              <div role="group" aria-labelledby="nav-custos">
                <SideLink to="/costing" label="Custos de importação" testId="nav-costing">
                  <IconCosting />
                </SideLink>
              </div>
            </div>
          ) : null}
          {showLogistica ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-logistica">
                Logística
              </div>
              <div role="group" aria-labelledby="nav-logistica">
                <SideLink to="/shipments" label="Embarques">
                  <IconShipments />
                </SideLink>
              </div>
            </div>
          ) : null}
          {showAduana ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-aduana">
                Aduana
              </div>
              <div role="group" aria-labelledby="nav-aduana">
                {canCustoms ? (
                  <SideLink to="/customs" label="Processos">
                    <IconCustoms />
                  </SideLink>
                ) : null}
                {canInventory ? (
                  <SideLink to="/inventory/movements" label="Estoque">
                    <IconInventory />
                  </SideLink>
                ) : null}
              </div>
            </div>
          ) : null}
          {showCatalogo ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-catalogo">
                Catálogo
              </div>
              <div role="group" aria-labelledby="nav-catalogo">
                <SideLink to="/catalog/products" label="Produtos">
                  <IconProducts />
                </SideLink>
              </div>
            </div>
          ) : null}
          {showAdministracao ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-admin">
                Administração
              </div>
              <div role="group" aria-labelledby="nav-admin">
                <SideLink to="/admin/users" label="Usuários">
                  <IconUsers />
                </SideLink>
              </div>
            </div>
          ) : null}
        </nav>
        <div className="shell-side-footer">
          <RuntimeBadge />
          <div className="shell-fx-slot">
            <FxQuoteStrip user={user} />
          </div>
          <button
            type="button"
            className="shell-rail-toggle"
            data-testid="shell-rail-toggle"
            aria-expanded={railOpen}
            aria-label={railOpen ? "Recolher navegação" : "Expandir navegação"}
            onClick={() => setRailOpen((v) => !v)}
          >
            {railOpen ? "‹" : "›"}
          </button>
          <Button
            type="button"
            variant="ghost"
            className="shell-logout"
            onClick={() => void logout()}
            aria-label="Sair"
          >
            <span className="shell-nav-label">Sair</span>
          </Button>
        </div>
      </aside>
      <div className="shell-content">
        <main id="main-content" className="shell-main" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
