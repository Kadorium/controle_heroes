import { NavLink, Outlet } from "react-router-dom";
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
function NavIcon({ d, extra }: { d: string; extra?: string }) {
  return (
    <svg
      className="shell-nav-icon"
      width="20"
      height="20"
      viewBox="0 0 20 20"
      aria-hidden="true"
      focusable="false"
    >
      <path fill="currentColor" fillRule="evenodd" d={d} />
      {extra ? <path fill="currentColor" d={extra} /> : null}
    </svg>
  );
}

function IconOrders() {
  return (
    <NavIcon d="M6.7 1.35h6.6c.7 0 1.25.55 1.25 1.25v2.15H5.45V2.6c0-.7.55-1.25 1.25-1.25zM8.35 2.2h3.3v1.05h-3.3V2.2zM3.6 4.75h12.8c.7 0 1.25.55 1.25 1.25v10.2c0 .7-.55 1.25-1.25 1.25H3.6c-.7 0-1.25-.55-1.25-1.25V6c0-.7.55-1.25 1.25-1.25zM6.35 8h7.3v1.35h-7.3V8zm0 2.85h7.3v1.35h-7.3v-1.35zm0 2.85h5v1.35h-5v-1.35z" />
  );
}

function IconInvoices() {
  return (
    <NavIcon d="M5.15 1.7h9.7a1.1 1.1 0 0 1 1.1 1.1v14.4a1.1 1.1 0 0 1-1.1 1.1H5.15a1.1 1.1 0 0 1-1.1-1.1V2.8a1.1 1.1 0 0 1 1.1-1.1zM13.2 8.6a1.7 1.7 0 1 1 0 3.4 1.7 1.7 0 0 1 0-3.4zM6.55 4.5h5.1v1.3h-5.1V4.5zm0 2.7h5.1v1.3h-5.1V7.2zm0 2.7h3.6v1.3H6.55v-1.3z" />
  );
}

function IconIngestion() {
  return (
    <NavIcon d="M9 1.55h2v5.5h2.7L10 12 6.3 7.05H9V1.55zM2.6 12.05h14.8v1.55H15.6L14.05 18H5.95L4.4 13.6H2.6v-1.55z" />
  );
}

function IconPayables() {
  return (
    <NavIcon d="M1.85 6.35h16.3A1.45 1.45 0 0 1 19.6 7.8v7.3a1.45 1.45 0 0 1-1.45 1.45H1.85A1.45 1.45 0 0 1 .4 15.1V7.8A1.45 1.45 0 0 1 1.85 6.35zM10 8.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z" />
  );
}

function IconPayments() {
  return (
    <NavIcon d="M10 1.75a8.25 8.25 0 1 1 0 16.5 8.25 8.25 0 0 1 0-16.5zm3.55 5.2-4.85 5.5-2.4-2.4-1.35 1.35 3.75 3.75 6.2-7.05-1.35-1.15z" />
  );
}

function IconShipments() {
  return (
    <NavIcon d="M4.7 6.6h3.3v5.5H4.7V6.6zm3.5 1.55h3.35v3.95H8.2V8.15zm3.55.7h3.55v3.25h-3.55V8.85zM1.7 12.15h16.6L16.2 16.7H3.8L1.7 12.15z" />
  );
}

function IconCustoms() {
  return (
    <NavIcon
      d="M8.85 1.7a6.55 6.55 0 1 1 0 13.1 6.55 6.55 0 0 1 0-13.1zm0 2.35a4.2 4.2 0 1 0 0 8.4 4.2 4.2 0 0 0 0-8.4z"
      extra="M13.35 12.2l4.7 4.7c.45.45.45 1.18 0 1.63-.45.45-1.18.45-1.63 0l-4.7-4.7 1.63-1.63z"
    />
  );
}

function IconInventory() {
  return (
    <NavIcon d="M5.7 2.15h8.6v5.5H5.7V2.15zM3.15 8.35h13.7v9.5H3.15V8.35z" />
  );
}

function IconProducts() {
  return (
    <NavIcon d="M4.2 3.1h11.6v3.4H4.2V3.1zm0 4.6h11.6v9.2H4.2V7.7zm2.2 2.1h7.2v1.4H6.4V9.8zm0 2.8h5.1v1.4H6.4v-1.4z" />
  );
}

function IconSuppliers() {
  return (
    <NavIcon d="M10 2.1a3.4 3.4 0 1 1 0 6.8 3.4 3.4 0 0 1 0-6.8zM3.4 16.4c.4-3.3 3.1-5.4 6.6-5.4s6.2 2.1 6.6 5.4H3.4z" />
  );
}

function IconUsers() {
  return (
    <NavIcon d="M7.2 2.4a2.7 2.7 0 1 1 0 5.4 2.7 2.7 0 0 1 0-5.4zm6.1 1.1a2.3 2.3 0 1 1 0 4.6 2.3 2.3 0 0 1 0-4.6zM2.6 16.3c.35-3 2.7-4.9 5.7-4.9 1.1 0 2.1.25 2.95.7-.15.35-.25.73-.25 1.15 0 1.7 1.15 3.15 2.7 3.65H2.6zm8.7-3.4c2.4 0 4.4 1.55 4.7 3.4h-6.9c.15-1.85 1.05-3.4 2.2-3.4z" />
  );
}

function IconProviders() {
  return (
    <NavIcon d="M2.4 12.2h4.1v5.1H2.4v-5.1zm5.5-3.6h4.2v8.7H7.9V8.6zm5.6-2.9h4.1v11.6h-4.1V5.7zM1.8 3.2h16.4v1.5H1.8V3.2z" />
  );
}

export function AppShell({ user, onLogout }: Props) {
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
  const canUsers = can(user, "users:read");
  const showProdutos = canCatalog;
  const showCompras = canOrders || canBilling || canIngestion;
  const showFinanceiro = canReporting || canBilling || canTreasury;
  const showLogistica = canLogistics;
  const showAduana = canCustoms || canInventory;
  const showAdministracao = canUsers;

  return (
    <div className="shell shell-sidebar-layout shell--auto-compact">
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
          {showProdutos ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-produtos">
                Produtos
              </div>
              <div role="group" aria-labelledby="nav-produtos">
                <NavLink to="/catalog/products" title="Produtos" aria-label="Produtos">
                  <IconProducts />
                  <span className="shell-nav-label">Produtos</span>
                </NavLink>
                <NavLink to="/catalog/suppliers" title="Fornecedores" aria-label="Fornecedores">
                  <IconSuppliers />
                  <span className="shell-nav-label">Fornecedores</span>
                </NavLink>
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
                  <NavLink to="/orders" title="Pedidos" aria-label="Pedidos">
                    <IconOrders />
                    <span className="shell-nav-label">Pedidos</span>
                  </NavLink>
                ) : null}
                {canBilling ? (
                  <NavLink to="/invoices" title="Faturas" aria-label="Faturas">
                    <IconInvoices />
                    <span className="shell-nav-label">Faturas</span>
                  </NavLink>
                ) : null}
                {canIngestion ? (
                  <NavLink to="/ingestion" title="Ingestão" aria-label="Ingestão" data-testid="nav-ingestion">
                    <IconIngestion />
                    <span className="shell-nav-label">Ingestão</span>
                  </NavLink>
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
                  <NavLink to="/payables" title="Contas a pagar" aria-label="Contas a pagar">
                    <IconPayables />
                    <span className="shell-nav-label">Contas a pagar</span>
                  </NavLink>
                ) : null}
                {canTreasury ? (
                  <NavLink
                    to="/payments"
                    title="Pagamentos realizados"
                    aria-label="Pagamentos realizados"
                  >
                    <IconPayments />
                    <span className="shell-nav-label">Pagamentos realizados</span>
                  </NavLink>
                ) : null}
              </div>
            </div>
          ) : null}
          {showLogistica ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-logistica">
                Logística
              </div>
              <div role="group" aria-labelledby="nav-logistica">
                <NavLink to="/shipments" title="Embarques" aria-label="Embarques">
                  <IconShipments />
                  <span className="shell-nav-label">Embarques</span>
                </NavLink>
                <NavLink to="/logistics-providers" title="Prestadores" aria-label="Prestadores">
                  <IconProviders />
                  <span className="shell-nav-label">Prestadores</span>
                </NavLink>
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
                  <NavLink to="/customs" title="Processos aduaneiros" aria-label="Processos aduaneiros">
                    <IconCustoms />
                    <span className="shell-nav-label">Processos</span>
                  </NavLink>
                ) : null}
                {canInventory ? (
                  <NavLink to="/inventory/movements" title="Estoque" aria-label="Estoque">
                    <IconInventory />
                    <span className="shell-nav-label">Estoque</span>
                  </NavLink>
                ) : null}
              </div>
            </div>
          ) : null}
          {showAdministracao ? (
            <div className="nav-group">
              <div className="nav-group-title" id="nav-admin">
                Administração
              </div>
              <div role="group" aria-labelledby="nav-admin">
                <NavLink to="/admin/users" title="Usuários" aria-label="Usuários">
                  <IconUsers />
                  <span className="shell-nav-label">Usuários</span>
                </NavLink>
              </div>
            </div>
          ) : null}
        </nav>
        <div className="shell-side-footer">
          <RuntimeBadge />
          <div className="shell-fx-slot">
            <FxQuoteStrip user={user} />
          </div>
          <Button
            type="button"
            variant="ghost"
            className="shell-logout"
            onClick={() => void logout()}
            title="Sair"
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
