import { NavLink, Outlet } from "react-router-dom";
import type { User } from "../features/auth/types";
import { FxQuoteStrip } from "../features/treasury/FxPanels";
import { Button, roleLabel } from "../ui";

type Props = {
  user: User;
  onLogout: () => Promise<void> | void;
};

function can(user: User, perm: string) {
  return user.role === "admin" || (user.permissions ?? []).includes(perm);
}

/** Ícones SVG inline mínimos — sem pacote externo (DECISÃO-RAIL Opção A). */
function IconOrders() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M4 3h12a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm1 2v10h10V5H5zm2 2h6v1.5H7V7zm0 3h6v1.5H7V10zm0 3h4v1.5H7V13z"
      />
    </svg>
  );
}

function IconInvoices() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M5 2h7l4 4v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zm7 1.5V7h3.5L12 3.5zM6 10h8v1.5H6V10zm0 3h8v1.5H6V13zm0 3h5v1.5H6V16z"
      />
    </svg>
  );
}

function IconPayables() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M3 5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2H3V5zm0 4h14v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9zm3 2.5h4V13H6v-1.5z"
      />
    </svg>
  );
}

function IconPayments() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M10 2a8 8 0 1 1 0 16A8 8 0 0 1 10 2zm0 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM9.25 6h1.5v4.25H14V12H9.25V6z"
      />
    </svg>
  );
}

function IconShipments() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M3 14h14v2H3v-2zm1.5-8h11L17 9v3H3V6l1.5-2zm2.2 2L5.6 8h8.8l-.9 2H6.7zM6 12.5h8v1H6v-1z"
      />
    </svg>
  );
}

function IconCustoms() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M4 3h12v2H4V3zm0 4h12v10H4V7zm2 2v6h8V9H6zm2 2h4v2H8v-2z"
      />
    </svg>
  );
}

function IconInventory() {
  return (
    <svg className="shell-nav-icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M3 4h14v3H3V4zm0 5h14v7H3V9zm2 2v3h10v-3H5z"
      />
    </svg>
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
  const showCompras = canOrders || canBilling;
  const showFinanceiro = canReporting || canBilling || canTreasury;
  const showLogistica = canLogistics;
  const showAduana = canCustoms || canInventory;

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
                  <NavLink to="/payments" title="Pagamentos" aria-label="Pagamentos">
                    <IconPayments />
                    <span className="shell-nav-label">Pagamentos</span>
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
        </nav>
        <div className="shell-side-footer">
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
