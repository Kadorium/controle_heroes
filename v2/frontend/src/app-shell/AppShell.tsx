import { NavLink, Outlet } from "react-router-dom";
import type { User } from "../features/auth/types";
import { FxQuoteStrip } from "../features/treasury/FxPanels";

type Props = {
  user: User;
  onLogout: () => Promise<void> | void;
};

function can(user: User, perm: string) {
  return user.role === "admin" || (user.permissions ?? []).includes(perm);
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

  return (
    <div className="shell shell-sidebar-layout">
      <aside className="shell-sidebar" aria-label="Navegação">
        <div className="shell-brand">
          <strong>Epic Controle</strong>
          <div className="shell-user">
            {user.name} · {user.role}
          </div>
        </div>
        <nav className="shell-side-nav">
          {canOrders ? (
            <div className="nav-group">
              <div className="nav-group-title">Ordens</div>
              <NavLink to="/orders" end>
                Fila
              </NavLink>
              {can(user, "orders:write") ? <NavLink to="/orders/new">Nova</NavLink> : null}
            </div>
          ) : null}
          {canBilling || canTreasury || canReporting ? (
            <div className="nav-group">
              <div className="nav-group-title">Financeiro</div>
              {canReporting || canBilling ? (
                <NavLink to="/payables">{canReporting ? "Contas a pagar" : "Payables"}</NavLink>
              ) : null}
              {canBilling ? <NavLink to="/invoices">Faturas</NavLink> : null}
              {canTreasury ? <NavLink to="/payments">Pagamentos</NavLink> : null}
            </div>
          ) : null}
        </nav>
        <div className="shell-side-footer">
          <FxQuoteStrip user={user} />
          <button type="button" className="btn" onClick={() => void logout()}>
            Sair
          </button>
        </div>
      </aside>
      <div className="shell-content">
        <main className="shell-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
